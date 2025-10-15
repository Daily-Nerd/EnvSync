"""Tests for multi-source merge behavior - critical for v0.11.0 release.

This test suite verifies TripWire's MERGE-WITH-OVERRIDE strategy when loading
multiple environment sources. This behavior is critical for the bootstrap pattern
where .env provides credentials and plugins (Vault, AWS) provide application secrets.

DESIGN BEHAVIOR (VERIFIED):
- Sources load left-to-right (first → last)
- Later sources override ONLY overlapping keys
- Non-overlapping keys from ALL sources are PRESERVED
- Final result is a UNION of all sources with priority resolution

This enables patterns like:
    .env (base config) + Vault (secrets) + .env.local (developer overrides)
"""

import os
from pathlib import Path
from typing import Dict

import pytest

from tripwire import TripWire
from tripwire.core.loader import DotenvFileSource, EnvFileLoader, EnvSource


class MockVaultSource(EnvSource):
    """Mock Vault source for testing multi-source merge behavior."""

    def __init__(self, variables: Dict[str, str]):
        self.variables = variables

    def load(self) -> Dict[str, str]:
        """Load variables into os.environ (merge behavior)."""
        # Plugin sources inject into os.environ
        for key, value in self.variables.items():
            os.environ[key] = value
        return self.variables


class MockAWSSource(EnvSource):
    """Mock AWS Secrets Manager source for testing."""

    def __init__(self, variables: Dict[str, str]):
        self.variables = variables

    def load(self) -> Dict[str, str]:
        """Load variables into os.environ (merge behavior)."""
        for key, value in self.variables.items():
            os.environ[key] = value
        return self.variables


class TestMultiSourceMergeBehavior:
    """Test suite verifying TripWire's multi-source merge strategy.

    CRITICAL FOR v0.11.0: These tests document expected behavior for
    the bootstrap pattern where .env provides credentials to access
    cloud secret managers (Vault, AWS Secrets Manager, etc.).
    """

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        # Store original state
        original_env = os.environ.copy()
        yield
        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)

    def test_two_source_merge_preserves_non_overlapping_variables(self, tmp_path):
        """Regression test: Later sources must NOT clear earlier sources' variables.

        This is the CRITICAL behavior for the bootstrap pattern:
        - .env provides: DEBUG, VAULT_TOKEN, VAULT_URL, THRESHOLD, PORT
        - Vault provides: GH_TOKEN, AWS_SECRET, DATABASE_URL, PORT (overlaps)
        - Expected: ALL variables present, Vault's PORT overrides .env's PORT
        """
        # Setup .env file with bootstrap credentials and config
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
DEBUG=true
PORT=3354
VAULT_TOKEN=hvs.local_token
VAULT_URL=https://vault.example.com
THRESHOLD=100
""".strip()
        )

        # Setup mock Vault source with secrets and overlapping PORT
        vault_vars = {
            "GH_TOKEN": "ghp_vault_token",
            "AWS_SECRET": "aws_vault_secret",
            "DATABASE_URL": "postgresql://vault_db",
            "PORT": "8080",  # Overlaps with .env
        }

        # Create sources (use override=True to ensure test values override any existing env vars)
        dotenv = DotenvFileSource(env_file, override=True)
        vault = MockVaultSource(vault_vars)

        # Load both sources (order matters - later overrides earlier)
        loader = EnvFileLoader([dotenv, vault], strict=False)
        loader.load_all()

        # VERIFY: Non-overlapping variables from .env are PRESERVED
        assert os.getenv("DEBUG") == "true", "DEBUG from .env should be preserved"
        assert os.getenv("VAULT_TOKEN") == "hvs.local_token", "VAULT_TOKEN from .env should be preserved"
        assert os.getenv("VAULT_URL") == "https://vault.example.com", "VAULT_URL from .env should be preserved"
        assert os.getenv("THRESHOLD") == "100", "THRESHOLD from .env should be preserved"

        # VERIFY: Non-overlapping variables from Vault are ADDED
        assert os.getenv("GH_TOKEN") == "ghp_vault_token", "GH_TOKEN from Vault should be added"
        assert os.getenv("AWS_SECRET") == "aws_vault_secret", "AWS_SECRET from Vault should be added"
        assert os.getenv("DATABASE_URL") == "postgresql://vault_db", "DATABASE_URL from Vault should be added"

        # VERIFY: Overlapping variable (PORT) uses LATER source (Vault)
        assert os.getenv("PORT") == "8080", "PORT from Vault should override .env's PORT"

    def test_three_source_merge_with_cascading_overrides(self, tmp_path):
        """Test three-source merge with cascading priority resolution.

        Pattern: Base config → Vault secrets → Local overrides

        IMPORTANT: DotenvFileSource with override=False (default) does NOT override
        existing variables. Plugin sources (Vault, AWS) ALWAYS override.

        To achieve "later source wins", use override=True on DotenvFileSource.
        """
        # Source 1: Base .env (lowest priority)
        base_env = tmp_path / ".env"
        base_env.write_text(
            """
APP_NAME=myapp
DEBUG=false
PORT=8000
LOG_LEVEL=info
VAULT_TOKEN=hvs.xxx
""".strip()
        )

        # Source 2: Vault (medium priority - always overrides)
        vault_vars = {
            "DATABASE_URL": "postgresql://prod_db",
            "API_KEY": "vault_api_key",
            "PORT": "9000",  # Overrides .env
            "LOG_LEVEL": "warning",  # Overrides .env
        }

        # Source 3: Local overrides (highest priority - needs override=True)
        local_env = tmp_path / ".env.local"
        local_env.write_text(
            """
DEBUG=true
PORT=3000
""".strip()
        )

        # Create sources in priority order (note: override=True on all for test isolation)
        dotenv_base = DotenvFileSource(base_env, override=True)  # Override for test isolation
        vault = MockVaultSource(vault_vars)
        dotenv_local = DotenvFileSource(local_env, override=True)  # Must override!

        # Load all sources
        loader = EnvFileLoader([dotenv_base, vault, dotenv_local], strict=False)
        loader.load_all()

        # VERIFY: Variables unique to each source are preserved
        assert os.getenv("APP_NAME") == "myapp", "Unique to .env - preserved"
        assert os.getenv("VAULT_TOKEN") == "hvs.xxx", "Unique to .env - preserved"
        assert os.getenv("DATABASE_URL") == "postgresql://prod_db", "Unique to Vault - preserved"
        assert os.getenv("API_KEY") == "vault_api_key", "Unique to Vault - preserved"

        # VERIFY: Cascading overrides (highest priority wins)
        assert os.getenv("PORT") == "3000", "Port: .env.local (override=True) > Vault > .env"
        assert os.getenv("DEBUG") == "true", "Debug: .env.local > .env"
        assert os.getenv("LOG_LEVEL") == "warning", "Log level: Vault > .env (no .env.local override)"

    def test_tripwire_v2_with_multiple_plugin_sources(self, tmp_path):
        """Test TripWire with multiple plugin sources (realistic usage).

        This tests the ACTUAL TripWire API that users will use in production.
        """
        # Setup .env with bootstrap credentials
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
DEBUG=true
VAULT_TOKEN=hvs.local_token
AWS_REGION=us-east-1
LOCAL_CONFIG=present
""".strip()
        )

        # Setup plugin sources
        vault_source = MockVaultSource(
            {
                "DATABASE_URL": "postgresql://vault_db",
                "API_KEY": "vault_api_key",
            }
        )

        aws_source = MockAWSSource(
            {
                "AWS_SECRET_KEY": "aws_secret",
                "S3_BUCKET": "my-bucket",
                "API_KEY": "aws_api_key",  # Conflicts with Vault
            }
        )

        # Create TripWire with multiple sources (RECOMMENDED PATTERN)
        dotenv = DotenvFileSource(env_file, override=True)  # Override for test isolation
        env = TripWire(sources=[dotenv, vault_source, aws_source], auto_load=True)

        # VERIFY: All non-overlapping variables are available
        assert os.getenv("DEBUG") == "true", "From .env"
        assert os.getenv("VAULT_TOKEN") == "hvs.local_token", "From .env"
        assert os.getenv("AWS_REGION") == "us-east-1", "From .env"
        assert os.getenv("LOCAL_CONFIG") == "present", "From .env"
        assert os.getenv("DATABASE_URL") == "postgresql://vault_db", "From Vault"
        assert os.getenv("AWS_SECRET_KEY") == "aws_secret", "From AWS"
        assert os.getenv("S3_BUCKET") == "my-bucket", "From AWS"

        # VERIFY: Overlapping variable (API_KEY) uses LAST source (AWS)
        assert os.getenv("API_KEY") == "aws_api_key", "AWS (last) overrides Vault"

    def test_bootstrap_pattern_realistic_scenario(self, tmp_path):
        """Test the EXACT bootstrap pattern from user's question.

        User's scenario:
        - .env contains: DEBUG, PORT, VAULT_TOKEN, VAULT_URL, THRESHOLD
        - Vault contains: GH_TOKEN, AWS_SECRET, DATABASE_URL, PORT (overlaps)

        User's expectation: Merge both, Vault's PORT wins, all other vars preserved.
        """
        # User's .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
DEBUG=true
PORT=3354
VAULT_TOKEN=hvs.xxx
VAULT_URL=https://vault.example.com
THRESHOLD=100
""".strip()
        )

        # User's Vault source
        vault = MockVaultSource(
            {
                "GH_TOKEN": "ghp_xxx",
                "AWS_SECRET": "xxx",
                "DATABASE_URL": "postgresql://...",
                "PORT": "8080",
            }
        )

        # User's code pattern
        dotenv = DotenvFileSource(env_file, override=True)  # Override for test isolation
        env = TripWire(sources=[dotenv, vault], auto_load=True)

        # User's expectation 1: Get bootstrap credentials from .env
        assert os.getenv("DEBUG") == "true"
        assert os.getenv("VAULT_TOKEN") == "hvs.xxx"
        assert os.getenv("VAULT_URL") == "https://vault.example.com"
        assert os.getenv("THRESHOLD") == "100"

        # User's expectation 2: Get application secrets from Vault
        assert os.getenv("GH_TOKEN") == "ghp_xxx"
        assert os.getenv("AWS_SECRET") == "xxx"
        assert os.getenv("DATABASE_URL") == "postgresql://..."

        # User's expectation 3: Vault's PORT overrides .env's PORT
        assert os.getenv("PORT") == "8080"

        # User's understanding: "All variables from both sources should be available"
        # This test CONFIRMS that understanding is CORRECT.

    def test_single_source_does_not_affect_merge_behavior(self, tmp_path):
        """Test that single source behaves identically (no special casing)."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\nVAR2=value2\n")

        dotenv = DotenvFileSource(env_file)
        env = TripWire(sources=[dotenv], auto_load=True)

        assert os.getenv("VAR1") == "value1"
        assert os.getenv("VAR2") == "value2"

    def test_empty_source_list_does_not_error(self):
        """Test that empty source list is handled gracefully."""
        # Should not raise
        env = TripWire(sources=[], auto_load=True)
        assert env is not None

    def test_source_with_override_parameter_behavior(self, tmp_path):
        """Test how DotenvFileSource override parameter affects merging.

        override=False: Only sets variables if NOT already in os.environ
        override=True: Always sets variables (overrides existing)
        """
        # Set existing value
        os.environ["OVERRIDE_TEST"] = "original_value"

        # Source 1: override=False (won't override existing)
        file1 = tmp_path / ".env1"
        file1.write_text("OVERRIDE_TEST=file1_value\n")

        # Source 2: override=True (will override existing)
        file2 = tmp_path / ".env2"
        file2.write_text("OVERRIDE_TEST=file2_value\n")

        # Test 1: override=False doesn't override existing
        dotenv1 = DotenvFileSource(file1, override=False)
        loader1 = EnvFileLoader([dotenv1])
        loader1.load_all()
        assert os.getenv("OVERRIDE_TEST") == "original_value", "override=False preserves existing"

        # Test 2: override=True does override existing
        dotenv2 = DotenvFileSource(file2, override=True)
        loader2 = EnvFileLoader([dotenv2])
        loader2.load_all()
        assert os.getenv("OVERRIDE_TEST") == "file2_value", "override=True replaces existing"

    def test_documented_merge_behavior_for_v0_11_0(self, tmp_path):
        """Comprehensive test documenting merge behavior for v0.11.0 documentation.

        This test serves as the canonical reference for multi-source behavior.
        """
        # Setup: Three sources with various overlaps
        base_env = tmp_path / ".env"
        base_env.write_text("A=base_A\nB=base_B\nC=base_C\nSHARED=base_SHARED\n")

        source2_vars = {"B": "source2_B", "D": "source2_D", "SHARED": "source2_SHARED"}
        source3_vars = {"C": "source3_C", "E": "source3_E", "SHARED": "source3_SHARED"}

        # Load sources in order
        dotenv = DotenvFileSource(base_env)
        source2 = MockVaultSource(source2_vars)
        source3 = MockAWSSource(source3_vars)

        env = TripWire(sources=[dotenv, source2, source3], auto_load=True)

        # EXPECTED MERGE RESULT:
        # Variable | Source 1 | Source 2 | Source 3 | Final Value
        # ---------|----------|----------|----------|------------
        # A        | base_A   | -        | -        | base_A (only in source1)
        # B        | base_B   | source2_B| -        | source2_B (source2 wins)
        # C        | base_C   | -        | source3_C| source3_C (source3 wins)
        # D        | -        | source2_D| -        | source2_D (only in source2)
        # E        | -        | -        | source3_E| source3_E (only in source3)
        # SHARED   | base     | source2  | source3  | source3_SHARED (last wins)

        assert os.getenv("A") == "base_A"
        assert os.getenv("B") == "source2_B"
        assert os.getenv("C") == "source3_C"
        assert os.getenv("D") == "source2_D"
        assert os.getenv("E") == "source3_E"
        assert os.getenv("SHARED") == "source3_SHARED"

        # SUMMARY: Result is UNION of all sources with rightmost priority
        all_vars = {"A", "B", "C", "D", "E", "SHARED"}
        loaded_vars = {k for k in all_vars if os.getenv(k) is not None}
        assert loaded_vars == all_vars, "All variables from all sources are present"
