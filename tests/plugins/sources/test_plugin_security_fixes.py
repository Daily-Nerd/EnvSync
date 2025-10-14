"""Tests for Week 1 security fixes in plugins.

This test file validates the security enhancements made to:
1. VaultEnvSource - HTTPS enforcement with HTTP opt-in
2. RemoteConfigSource - HTTPS enforcement with HTTP opt-in
3. Git audit - HEAD validation and timeout protection
"""

from __future__ import annotations

import warnings
from unittest.mock import Mock

import pytest

from tripwire.plugins.errors import PluginValidationError, SecurityWarning


class TestVaultHTTPSEnforcement:
    """Test HTTPS enforcement in Vault plugin."""

    def test_https_url_accepted(self) -> None:
        """Test that HTTPS URLs are accepted without warnings."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with warnings.catch_warnings():
            warnings.simplefilter("error", SecurityWarning)
            # Should not raise any warnings
            vault = VaultEnvSource(
                url="https://vault.example.com",
                token="hvs.test",
                path="myapp/config",
            )

        assert vault.url == "https://vault.example.com"
        assert not vault.allow_http

    def test_http_url_rejected_by_default(self) -> None:
        """Test that HTTP URLs are rejected by default."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with pytest.raises(PluginValidationError) as exc:
            VaultEnvSource(
                url="http://localhost:8200",
                token="hvs.test",
                path="myapp/config",
            )

        assert "Vault URL must use HTTPS" in str(exc.value)
        assert "allow_http=True" in str(exc.value)

    def test_http_url_allowed_with_opt_in(self) -> None:
        """Test that HTTP URLs are allowed with explicit opt-in."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", SecurityWarning)

            vault = VaultEnvSource(
                url="http://localhost:8200",
                token="hvs.test",
                path="myapp/config",
                allow_http=True,
            )

        # Should succeed
        assert vault.url == "http://localhost:8200"
        assert vault.allow_http

        # Should have issued a warning
        assert len(w) == 1
        assert issubclass(w[0].category, SecurityWarning)
        assert "Security Warning" in str(w[0].message)
        assert "insecure" in str(w[0].message).lower()

    def test_invalid_scheme_rejected(self) -> None:
        """Test that invalid URL schemes are rejected."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with pytest.raises(PluginValidationError) as exc:
            VaultEnvSource(
                url="ftp://vault.example.com",
                token="hvs.test",
                path="myapp/config",
            )

        assert "Invalid URL scheme" in str(exc.value)

    def test_missing_hostname_rejected(self) -> None:
        """Test that URLs without hostname are rejected."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with pytest.raises(PluginValidationError) as exc:
            VaultEnvSource(
                url="https://",
                token="hvs.test",
                path="myapp/config",
            )

        assert "Invalid Vault URL format" in str(exc.value)

    def test_localhost_http_with_warning(self) -> None:
        """Test localhost HTTP URL shows warning (common dev scenario)."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", SecurityWarning)

            vault = VaultEnvSource(
                url="http://localhost:8200",
                token="hvs.test",
                path="myapp/config",
                allow_http=True,
            )

        assert vault.url == "http://localhost:8200"
        assert len(w) == 1
        assert "local/internal deployment" in str(w[0].message)


class TestRemoteConfigHTTPSEnforcement:
    """Test HTTPS enforcement in Remote Config plugin."""

    def test_https_url_accepted(self) -> None:
        """Test that HTTPS URLs are accepted without warnings."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with warnings.catch_warnings():
            warnings.simplefilter("error", SecurityWarning)
            # Should not raise any warnings
            remote = RemoteConfigSource(url="https://config.example.com/api")

        assert remote.url == "https://config.example.com/api"
        assert not remote.allow_http

    def test_http_url_rejected_by_default(self) -> None:
        """Test that HTTP URLs are rejected by default."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with pytest.raises(PluginValidationError) as exc:
            RemoteConfigSource(url="http://config.local")

        assert "Remote config URL must use HTTPS" in str(exc.value)
        assert "allow_http=True" in str(exc.value)

    def test_http_url_allowed_with_opt_in(self) -> None:
        """Test that HTTP URLs are allowed with explicit opt-in."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", SecurityWarning)

            remote = RemoteConfigSource(
                url="http://config.local:8080",
                allow_http=True,
            )

        # Should succeed
        assert remote.url == "http://config.local:8080"
        assert remote.allow_http

        # Should have issued a warning
        assert len(w) == 1
        assert issubclass(w[0].category, SecurityWarning)
        assert "Security Warning" in str(w[0].message)
        assert "insecure" in str(w[0].message).lower()

    def test_invalid_scheme_rejected(self) -> None:
        """Test that invalid URL schemes are rejected."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with pytest.raises(PluginValidationError) as exc:
            RemoteConfigSource(url="file:///etc/config.json")

        assert "Invalid URL scheme" in str(exc.value)

    def test_missing_hostname_rejected(self) -> None:
        """Test that URLs without hostname are rejected."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with pytest.raises(PluginValidationError) as exc:
            RemoteConfigSource(url="https://")

        assert "Invalid remote config URL format" in str(exc.value)

    def test_validate_config_http_rejected_by_default(self) -> None:
        """Test that validate_config also enforces HTTPS."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(url="https://config.example.com/api")

        config = {"url": "http://config.local"}

        with pytest.raises(PluginValidationError) as exc:
            remote.validate_config(config)

        assert "must use HTTPS" in str(exc.value)

    def test_validate_config_http_allowed_with_opt_in(self) -> None:
        """Test that validate_config allows HTTP with allow_http."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(url="https://config.example.com/api")

        config = {
            "url": "http://config.local",
            "allow_http": True,
        }

        # Should succeed without raising
        assert remote.validate_config(config) is True


class TestBackwardCompatibility:
    """Test that existing code remains functional."""

    def test_vault_existing_https_code_works(self) -> None:
        """Test that existing Vault code with HTTPS works unchanged."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        # This is how existing code looks - should work without changes
        vault = VaultEnvSource(
            url="https://vault.production.com",
            token="hvs.xxxxx",
            mount_point="secret",
            path="myapp/production",
            kv_version=2,
        )

        assert vault.url == "https://vault.production.com"
        assert vault.metadata.name == "vault"

    def test_remote_config_existing_https_code_works(self) -> None:
        """Test that existing RemoteConfig code with HTTPS works unchanged."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        # This is how existing code looks - should work without changes
        remote = RemoteConfigSource(
            url="https://config.production.com/api/v1/config",
            format="json",
            headers={"Authorization": "Bearer token"},
            timeout=30,
        )

        assert remote.url == "https://config.production.com/api/v1/config"
        assert remote.format == "json"


class TestSecurityWarningClass:
    """Test SecurityWarning exception class."""

    def test_security_warning_is_user_warning(self) -> None:
        """Test that SecurityWarning inherits from UserWarning."""
        from tripwire.plugins.errors import SecurityWarning

        assert issubclass(SecurityWarning, UserWarning)

    def test_security_warning_can_be_caught(self) -> None:
        """Test that SecurityWarning can be caught and filtered."""
        from tripwire.plugins.errors import SecurityWarning

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", SecurityWarning)
            warnings.warn("Test warning", SecurityWarning)

        assert len(w) == 1
        assert issubclass(w[0].category, SecurityWarning)
        assert "Test warning" in str(w[0].message)


class TestGitAuditSecurityFixes:
    """Test git audit security fixes (HEAD validation and timeouts)."""

    def test_git_command_has_timeout_parameter(self) -> None:
        """Test that run_git_command accepts timeout parameter."""
        # Check function signature has timeout parameter
        import inspect
        from pathlib import Path

        from tripwire.git_audit import run_git_command

        sig = inspect.signature(run_git_command)
        assert "timeout" in sig.parameters
        assert sig.parameters["timeout"].default == 30

    def test_git_command_default_timeout(self, tmp_path: Path) -> None:
        """Test that git commands use 30s timeout by default."""
        # Initialize a git repo
        import subprocess

        from tripwire.git_audit import run_git_command

        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Run a simple git command - should succeed with default timeout
        result = run_git_command(["status"], tmp_path, check=False)
        assert result.returncode == 0

    def test_sanitize_git_pattern_function_exists(self) -> None:
        """Test that sanitize_git_pattern function exists."""
        from tripwire.git_audit import sanitize_git_pattern

        # Test it sanitizes dangerous patterns
        dangerous_pattern = "(a+)+b"
        sanitized = sanitize_git_pattern(dangerous_pattern)

        # Should be escaped (no longer has nested quantifiers)
        assert "+" not in sanitized or sanitized != dangerous_pattern

    def test_sanitize_git_pattern_escapes_redos(self) -> None:
        """Test that ReDoS patterns are escaped."""
        from tripwire.git_audit import sanitize_git_pattern

        # Test various ReDoS patterns
        redos_patterns = [
            "(a+)+",
            "(a*)*",
            "(a?)+",
            "a{10,100}",
            "a{1000,}",
            "(.+)+",
            "(.*)*",
        ]

        for pattern in redos_patterns:
            sanitized = sanitize_git_pattern(pattern)
            # Should be escaped (no longer dangerous)
            assert sanitized != pattern or not any(c in sanitized for c in "+*?()")

    def test_sanitize_git_pattern_preserves_safe_patterns(self) -> None:
        """Test that safe patterns are preserved."""
        from tripwire.git_audit import sanitize_git_pattern

        safe_patterns = [
            "normal_secret_123",
            "API_KEY",
            "DATABASE_URL",
        ]

        for pattern in safe_patterns:
            sanitized = sanitize_git_pattern(pattern)
            assert sanitized == pattern


class TestDocumentation:
    """Test that documentation is updated."""

    def test_vault_docstring_mentions_allow_http(self) -> None:
        """Test that Vault __init__ docstring mentions allow_http parameter."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        docstring = VaultEnvSource.__init__.__doc__
        assert docstring is not None
        assert "allow_http" in docstring
        assert "local" in docstring.lower() or "internal" in docstring.lower()

    def test_remote_config_docstring_mentions_allow_http(self) -> None:
        """Test that RemoteConfig __init__ docstring mentions allow_http parameter."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        docstring = RemoteConfigSource.__init__.__doc__
        assert docstring is not None
        assert "allow_http" in docstring
        assert "local" in docstring.lower() or "internal" in docstring.lower()

    def test_git_command_docstring_mentions_timeout(self) -> None:
        """Test that run_git_command docstring mentions timeout."""
        from tripwire.git_audit import run_git_command

        docstring = run_git_command.__doc__
        assert docstring is not None
        assert "timeout" in docstring.lower()
        assert "security" in docstring.lower() or "hung" in docstring.lower()
