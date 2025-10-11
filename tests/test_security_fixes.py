"""Tests for critical security fixes.

This module tests three critical security fixes:
1. Type inference cache race condition (Issue #1)
2. Git command injection via ReDoS (Issue #2)
3. Unbounded memory growth in git audit (Issue #3)
"""

import subprocess
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Generator

import pytest

from tripwire.git_audit import (
    _estimate_occurrence_size,
    analyze_secret_history,
    sanitize_git_pattern,
)


@pytest.fixture
def git_repo_large(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a git repo with many commits containing a secret.

    Args:
        tmp_path: Pytest temporary directory

    Yields:
        Path to the temporary git repository
    """
    repo_path = tmp_path / "large_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create 20 commits with secret to test memory limits
    for i in range(20):
        env_file = repo_path / f"config_{i}.env"
        env_file.write_text(f"SECRET_KEY=very_long_secret_value_number_{i}_" + "x" * 100 + "\n")
        subprocess.run(["git", "add", f"config_{i}.env"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add config {i}"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    yield repo_path


class TestCacheRaceCondition:
    """Tests for Issue #1: Type inference cache race condition fix."""

    def test_concurrent_cache_access(self) -> None:
        """Test that concurrent cache access doesn't cause race conditions."""
        from tripwire import env

        # Track results from threads
        results = []
        errors = []

        def require_var(thread_id: int) -> None:
            """Call require() from multiple threads."""
            try:
                # Each thread tries to infer type for same variable
                PORT: int = env.require("CONCURRENT_TEST_PORT", default=3000 + thread_id)
                results.append((thread_id, PORT))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run 50 threads concurrently
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(require_var, i) for i in range(50)]
            for future in futures:
                future.result()

        # Should have 50 successful results, no errors
        assert len(results) == 50
        assert len(errors) == 0

    def test_cache_lru_eviction(self) -> None:
        """Test that cache implements LRU eviction to prevent unbounded growth."""
        from tripwire.core import env
        from tripwire.core.inference import _CACHE_MAX_SIZE, _TYPE_INFERENCE_CACHE

        # Clear cache first
        _TYPE_INFERENCE_CACHE.clear()

        # Create more variables than cache size
        for i in range(_CACHE_MAX_SIZE + 100):
            # Each require() call will try to cache its result
            val: str = env.require(f"VAR_{i}", default=f"value_{i}")
            assert val == f"value_{i}"

        # Cache should never exceed max size
        assert len(_TYPE_INFERENCE_CACHE) <= _CACHE_MAX_SIZE

    def test_cache_thread_safety_stress(self) -> None:
        """Stress test cache thread safety with many concurrent operations."""
        from tripwire import env

        errors = []

        def stress_cache(thread_id: int) -> None:
            """Stress test the cache with many operations."""
            try:
                for i in range(100):
                    VAR: int = env.require(f"STRESS_{thread_id}_{i}", default=i)
                    assert VAR == i
            except Exception as e:
                errors.append(str(e))

        # Run 20 threads, each doing 100 operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_cache, i) for i in range(20)]
            for future in futures:
                future.result()

        # No errors should occur
        assert len(errors) == 0


class TestReDoSProtection:
    """Tests for Issue #2: Git command injection via ReDoS fix."""

    def test_sanitize_normal_pattern(self) -> None:
        """Test that normal patterns are not modified."""
        pattern = "normal_secret_123"
        sanitized = sanitize_git_pattern(pattern)
        assert sanitized == pattern

    def test_sanitize_nested_quantifiers(self) -> None:
        """Test that nested quantifiers are escaped."""
        # Malicious pattern: (a+)+
        pattern = "(a+)+"
        sanitized = sanitize_git_pattern(pattern)
        # Should be escaped (literal search)
        assert sanitized != pattern
        assert "\\" in sanitized

    def test_sanitize_nested_star_quantifiers(self) -> None:
        """Test that nested star quantifiers are escaped."""
        # Malicious pattern: (a*)*
        pattern = "(a*)*"
        sanitized = sanitize_git_pattern(pattern)
        assert sanitized != pattern
        assert "\\" in sanitized

    def test_sanitize_excessive_quantifiers(self) -> None:
        """Test that excessive consecutive quantifiers are escaped."""
        # Malicious pattern: b+++++++
        pattern = "b+++++++"
        sanitized = sanitize_git_pattern(pattern)
        assert sanitized != pattern
        assert "\\" in sanitized

    def test_sanitize_large_bounded_repetition(self) -> None:
        """Test that large bounded repetition is escaped."""
        # Malicious pattern: .{10000}
        pattern = ".{10000}"
        sanitized = sanitize_git_pattern(pattern)
        assert sanitized != pattern
        assert "\\" in sanitized

    def test_sanitize_max_length(self) -> None:
        """Test that patterns exceeding max length are truncated and escaped."""
        # Create a pattern longer than default max (1024)
        long_pattern = "a" * 2000
        sanitized = sanitize_git_pattern(long_pattern)
        # Should be truncated to max length
        assert len(sanitized) <= 1024 * 2  # Account for escaping
        # Should be escaped
        assert "\\" in sanitized or len(sanitized) == 1024

    def test_sanitize_custom_max_length(self) -> None:
        """Test sanitize with custom max length."""
        pattern = "a" * 500
        sanitized = sanitize_git_pattern(pattern, max_length=100)
        # Should be limited to 100 chars (plus escaping)
        assert len(sanitized) <= 200

    def test_sanitize_redos_attack_pattern(self) -> None:
        """Test actual ReDoS attack patterns from the wild."""
        # Real ReDoS patterns that have caused issues
        patterns = [
            "(a+)+b++++++++++++++++++++++c",  # Nested plus with excessive quantifiers
            "(a*)*x",  # Nested star
            "(.+)+$",  # Nested any-plus
            "(.*)*end",  # Nested any-star
            "a{1000,2000}",  # Large bounded repetition
        ]

        for pattern in patterns:
            sanitized = sanitize_git_pattern(pattern)
            # All should be escaped
            assert sanitized != pattern
            assert "\\" in sanitized

    def test_sanitize_preserves_safe_patterns(self) -> None:
        """Test that safe patterns are preserved."""
        safe_patterns = [
            "AWS_SECRET_KEY",
            "secret[0-9]+",  # Simple regex
            "key.*value",  # Safe wildcard
            "test+",  # Single quantifier
        ]

        for pattern in safe_patterns:
            sanitized = sanitize_git_pattern(pattern)
            # Should be unchanged
            assert sanitized == pattern

    def test_sanitize_bounded_repetition(self) -> None:
        """Test that bounded repetition is handled correctly."""
        # Small bounded repetitions are safe (note: current implementation escapes all {} patterns)
        pattern = "a{1,10}"
        sanitized = sanitize_git_pattern(pattern)
        # Current implementation escapes all bounded repetitions as a security precaution
        # This is conservative but safe
        assert "{" not in sanitized or "\\" in sanitized


class TestMemoryProtection:
    """Tests for Issue #3: Unbounded memory growth fix."""

    def test_analyze_secret_history_memory_limit(self, git_repo_large: Path) -> None:
        """Test that memory limit prevents OOM in large repos."""
        # Set a very small memory limit (0.001MB = 1KB) to trigger limit quickly
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            timeline = analyze_secret_history(
                secret_name="SECRET_KEY",
                repo_path=git_repo_large,
                max_memory_mb=0.001,  # 1KB limit - very small
            )

            # Should have triggered a memory warning (if any occurrences found)
            warning_messages = [str(warning.message) for warning in w]
            memory_warnings = [msg for msg in warning_messages if "Memory limit" in msg]

            # If we found occurrences and hit the memory limit, should have a warning
            if timeline.total_occurrences > 0:
                # With 1KB limit and ~512 bytes per occurrence, should hit limit
                assert len(memory_warnings) > 0

    def test_analyze_secret_history_partial_results(self, git_repo_large: Path) -> None:
        """Test that partial results are returned when memory limit is reached."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Very small limit to force partial results
            timeline = analyze_secret_history(
                secret_name="SECRET_KEY",
                repo_path=git_repo_large,
                max_memory_mb=1,
            )

            # Should still get some results even with limit
            # (Timeline should be valid, just incomplete)
            assert timeline is not None
            assert timeline.secret_name == "SECRET_KEY"

    def test_analyze_secret_history_default_memory_limit(self, git_repo_large: Path) -> None:
        """Test default memory limit (100MB) allows reasonable operations."""
        # Default limit should not trigger for our small test repo
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            timeline = analyze_secret_history(
                secret_name="SECRET_KEY",
                repo_path=git_repo_large,
                # Use default max_memory_mb (100MB)
            )

            # With default 100MB limit, should not hit limit on small repo
            warning_messages = [str(warning.message) for warning in w]
            memory_warnings = [msg for msg in warning_messages if "Memory limit" in msg]

            # Should have found results without hitting memory limit
            assert timeline.total_occurrences > 0
            # Should not have memory warnings for small repo
            assert len(memory_warnings) == 0

    def test_estimate_occurrence_size(self, git_repo_large: Path) -> None:
        """Test that occurrence size estimation works correctly."""
        from datetime import datetime

        from tripwire.git_audit import FileOccurrence

        # Create a sample occurrence
        occ = FileOccurrence(
            file_path="config/settings.py",
            line_number=42,
            commit_hash="abc123def456",
            commit_date=datetime.now(),
            author="Test User",
            author_email="test@example.com",
            commit_message="Add secret configuration",
            context="SECRET_KEY=***REDACTED***",
        )

        # Estimate size
        size = _estimate_occurrence_size(occ)

        # Should be a reasonable estimate (not 0, not crazy large)
        assert size > 0
        assert size < 10000  # Should be < 10KB per occurrence

    def test_memory_limit_warning_message(self, git_repo_large: Path) -> None:
        """Test that memory limit warning has helpful message."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            timeline = analyze_secret_history(
                secret_name="SECRET_KEY",
                repo_path=git_repo_large,
                max_memory_mb=1,  # Small limit to trigger warning
            )

            warning_messages = [str(warning.message) for warning in w]
            memory_warnings = [msg for msg in warning_messages if "Memory limit" in msg]

            if memory_warnings:
                msg = memory_warnings[0]
                # Should mention the limit
                assert "1MB" in msg
                # Should suggest alternative
                assert "audit_secret_stream" in msg
                # Should mention partial results
                assert "partial" in msg.lower()


class TestSecurityFixesIntegration:
    """Integration tests combining all three security fixes."""

    def test_concurrent_audit_operations(self, git_repo_large: Path) -> None:
        """Test concurrent audit operations work correctly with all fixes."""
        results = []
        errors = []

        def audit_secret(thread_id: int) -> None:
            """Run audit from multiple threads."""
            try:
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("always")

                    timeline = analyze_secret_history(
                        secret_name="SECRET_KEY",
                        repo_path=git_repo_large,
                        max_memory_mb=50,  # Reasonable limit
                    )
                    results.append((thread_id, timeline.total_occurrences))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run 10 concurrent audits
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(audit_secret, i) for i in range(10)]
            for future in futures:
                future.result()

        # All audits should succeed
        assert len(results) == 10
        assert len(errors) == 0

    def test_redos_pattern_with_sanitization(self) -> None:
        """Test that ReDoS patterns are safely handled."""
        # Malicious pattern that would cause ReDoS
        malicious_pattern = "(a+)+b++++++++++c"

        # Should be sanitized safely
        sanitized = sanitize_git_pattern(malicious_pattern)

        # Should be escaped (safe literal search)
        assert sanitized != malicious_pattern
        assert "\\" in sanitized

        # Verify it doesn't match the original dangerous pattern
        import re

        # The sanitized pattern should be a literal match (no regex interpretation)
        try:
            # This should not cause catastrophic backtracking
            re.compile(sanitized)
        except re.error:
            pytest.fail("Sanitized pattern should compile without errors")
