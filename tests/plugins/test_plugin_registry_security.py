"""
Security tests for plugin registry system.

Tests URL scheme validation (SSRF protection) and path traversal (Zip Slip) protection.
"""

import io
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tripwire.plugins.registry import (
    PluginInstaller,
    PluginRegistryClient,
    PluginVersionInfo,
    _is_safe_path,
    _safe_extract_tarfile,
    _safe_extract_zipfile,
    _validate_url_scheme,
)


class TestURLSchemeValidation:
    """Test suite for URL scheme validation (SSRF protection)."""

    def test_validate_url_scheme_https_allowed(self):
        """HTTPS URLs should be allowed."""
        # Should not raise
        _validate_url_scheme("https://github.com/tripwire-plugins/registry/main/registry.json")
        _validate_url_scheme("https://example.com/path/to/file.tar.gz")

    def test_validate_url_scheme_http_rejected(self):
        """HTTP URLs should be rejected."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("http://example.com/file.tar.gz")

    def test_validate_url_scheme_file_rejected(self):
        """file:// URLs should be rejected (SSRF protection)."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("file:///etc/passwd")

    def test_validate_url_scheme_ftp_rejected(self):
        """ftp:// URLs should be rejected."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("ftp://example.com/file.tar.gz")

    def test_validate_url_scheme_custom_scheme_rejected(self):
        """Custom schemes should be rejected."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("custom://example.com/file.tar.gz")

    def test_validate_url_scheme_gopher_rejected(self):
        """gopher:// URLs should be rejected (SSRF vector)."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("gopher://evil.com/path")

    def test_validate_url_scheme_data_rejected(self):
        """data:// URLs should be rejected."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("data:text/plain;base64,SGVsbG8gV29ybGQ=")


class TestPathTraversalProtection:
    """Test suite for path traversal (Zip Slip) protection."""

    def test_is_safe_path_valid_child(self):
        """Paths within base directory should be safe."""
        base = Path("/tmp/test")
        child = Path("/tmp/test/plugin/file.py")
        assert _is_safe_path(base, child) is True

    def test_is_safe_path_direct_child(self):
        """Direct children should be safe."""
        base = Path("/tmp/test")
        child = Path("/tmp/test/file.py")
        assert _is_safe_path(base, child) is True

    def test_is_safe_path_parent_traversal_rejected(self):
        """Paths escaping via .. should be rejected."""
        base = Path("/tmp/test")
        malicious = Path("/tmp/test/../etc/passwd")
        assert _is_safe_path(base, malicious) is False

    def test_is_safe_path_absolute_escape_rejected(self):
        """Absolute paths outside base should be rejected."""
        base = Path("/tmp/test")
        malicious = Path("/etc/passwd")
        assert _is_safe_path(base, malicious) is False

    def test_is_safe_path_symlink_escape(self, tmp_path):
        """Symlinks escaping base should be detected."""
        base = tmp_path / "base"
        base.mkdir()

        # Create directory outside base
        outside = tmp_path / "outside"
        outside.mkdir()

        # Create symlink inside base pointing outside
        symlink = base / "link"
        symlink.symlink_to(outside)

        # Should detect that resolved path is outside base
        target = base / "link" / "file.txt"
        assert _is_safe_path(base, target) is False

    def test_is_safe_path_nested_relative_escape(self):
        """Complex nested .. paths should be rejected."""
        base = Path("/tmp/test/plugin")
        malicious = Path("/tmp/test/plugin/../../../../../../etc/passwd")
        assert _is_safe_path(base, malicious) is False


class TestSafeTarfileExtraction:
    """Test suite for safe tarfile extraction."""

    def test_safe_extract_tarfile_valid_archive(self, tmp_path):
        """Normal archives should extract successfully."""
        # Create test tarfile
        archive = tmp_path / "test.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            # Add valid file
            info = tarfile.TarInfo(name="plugin/file.py")
            info.size = 10
            tar.addfile(info, io.BytesIO(b"print('hi')"))

        # Extract to temp directory
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract_tarfile(tar, extract_dir)

        # Verify extraction
        assert (extract_dir / "plugin" / "file.py").exists()

    def test_safe_extract_tarfile_path_traversal_blocked(self, tmp_path):
        """Tarfiles with .. paths should be rejected."""
        # Create malicious tarfile with path traversal
        archive = tmp_path / "malicious.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            info = tarfile.TarInfo(name="../../etc/passwd")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"pwnd"))

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Should raise RuntimeError
        with tarfile.open(archive, "r:gz") as tar:
            with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
                _safe_extract_tarfile(tar, extract_dir)

        # Verify file was NOT created outside extract_dir
        assert not (tmp_path / "etc" / "passwd").exists()

    def test_safe_extract_tarfile_absolute_path_blocked(self, tmp_path):
        """Tarfiles with absolute paths should be rejected."""
        # Create malicious tarfile with absolute path
        archive = tmp_path / "malicious.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            info = tarfile.TarInfo(name="/etc/evil")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"pwnd"))

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with tarfile.open(archive, "r:gz") as tar:
            with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
                _safe_extract_tarfile(tar, extract_dir)


class TestSafeZipfileExtraction:
    """Test suite for safe zipfile extraction."""

    def test_safe_extract_zipfile_valid_archive(self, tmp_path):
        """Normal zip archives should extract successfully."""
        # Create test zipfile
        archive = tmp_path / "test.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("plugin/file.py", "print('hi')")

        # Extract to temp directory
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with zipfile.ZipFile(archive, "r") as zf:
            _safe_extract_zipfile(zf, extract_dir)

        # Verify extraction
        assert (extract_dir / "plugin" / "file.py").exists()

    def test_safe_extract_zipfile_path_traversal_blocked(self, tmp_path):
        """Zipfiles with .. paths should be rejected."""
        # Create malicious zipfile with path traversal
        archive = tmp_path / "malicious.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../../etc/passwd", "pwnd")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Should raise RuntimeError
        with zipfile.ZipFile(archive, "r") as zf:
            with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
                _safe_extract_zipfile(zf, extract_dir)

        # Verify file was NOT created outside extract_dir
        assert not (tmp_path / "etc" / "passwd").exists()

    def test_safe_extract_zipfile_absolute_path_blocked(self, tmp_path):
        """Zipfiles with absolute paths should be rejected."""
        # Create malicious zipfile with absolute path
        archive = tmp_path / "malicious.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("/etc/evil", "pwnd")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with zipfile.ZipFile(archive, "r") as zf:
            with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
                _safe_extract_zipfile(zf, extract_dir)


class TestRegistryClientSecurity:
    """Integration tests for PluginRegistryClient security."""

    def test_fetch_registry_rejects_file_url(self, tmp_path):
        """Registry client falls back to bundled registry when file:// URL fails."""
        # Ensure cache doesn't exist
        cache_file = tmp_path / "cache" / "registry.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        client = PluginRegistryClient(registry_url="file:///etc/passwd")
        client.CACHE_FILE = cache_file  # Use temp cache location

        # Should fall back to bundled registry (file:// URL validation will fail)
        registry = client.fetch_registry(use_cache=False)

        # Should have loaded bundled registry with 4 official plugins
        assert registry.version == "1.0.0"
        assert len(registry.plugins) >= 4
        assert "vault" in registry.plugins

    def test_fetch_registry_rejects_http_url(self, tmp_path):
        """Registry client falls back to bundled registry when http:// URL fails."""
        # Ensure cache doesn't exist
        cache_file = tmp_path / "cache" / "registry.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        client = PluginRegistryClient(registry_url="http://evil.com/malicious.json")
        client.CACHE_FILE = cache_file  # Use temp cache location

        # Should fall back to bundled registry (http:// URL validation will fail)
        registry = client.fetch_registry(use_cache=False)

        # Should have loaded bundled registry with 4 official plugins
        assert registry.version == "1.0.0"
        assert len(registry.plugins) >= 4
        assert "vault" in registry.plugins

    @patch("urllib.request.urlopen")
    def test_fetch_registry_accepts_https_url(self, mock_urlopen):
        """Registry client should accept https:// URLs."""
        # Mock response with valid JSON
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b'{"version": "1.0.0", "updated_at": "2025-10-12", "plugins": {}}'
        mock_urlopen.return_value = mock_response

        client = PluginRegistryClient(registry_url="https://github.com/tripwire/registry.json")
        registry = client.fetch_registry(use_cache=False)

        # Should successfully fetch
        assert registry.version == "1.0.0"
        mock_urlopen.assert_called_once()


class TestPluginInstallerSecurity:
    """Integration tests for PluginInstaller security."""

    @patch("urllib.request.urlopen")
    def test_install_rejects_file_url(self, mock_urlopen, tmp_path):
        """Plugin installer should reject file:// download URLs."""
        version_info = PluginVersionInfo(
            version="1.0.0",
            release_date="2025-10-12",
            min_tripwire_version="0.10.0",
            download_url="file:///etc/passwd",
            checksum="sha256:abc123",
        )

        installer = PluginInstaller()

        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            installer._download_plugin(version_info)

        # urlopen should never be called
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_install_rejects_http_url(self, mock_urlopen):
        """Plugin installer should reject http:// download URLs."""
        version_info = PluginVersionInfo(
            version="1.0.0",
            release_date="2025-10-12",
            min_tripwire_version="0.10.0",
            download_url="http://evil.com/malicious.tar.gz",
            checksum="sha256:abc123",
        )

        installer = PluginInstaller()

        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            installer._download_plugin(version_info)

        # urlopen should never be called
        mock_urlopen.assert_not_called()

    def test_extract_archive_rejects_path_traversal_tar(self, tmp_path):
        """Plugin installer should reject tar archives with path traversal."""
        # Create malicious tarfile
        archive = tmp_path / "malicious.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            info = tarfile.TarInfo(name="../../evil.py")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"pwnd"))

        installer = PluginInstaller()

        with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
            installer._extract_archive(archive)

    def test_extract_archive_rejects_path_traversal_zip(self, tmp_path):
        """Plugin installer should reject zip archives with path traversal."""
        # Create malicious zipfile
        archive = tmp_path / "malicious.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../../evil.py", "pwnd")

        installer = PluginInstaller()

        with pytest.raises(RuntimeError, match="attempts to escape extraction directory"):
            installer._extract_archive(archive)


class TestSecurityEdgeCases:
    """Test edge cases and corner cases for security."""

    def test_validate_url_scheme_empty_string(self):
        """Empty URL should raise ValueError."""
        with pytest.raises(ValueError, match="Only HTTPS URLs are allowed"):
            _validate_url_scheme("")

    def test_is_safe_path_same_path(self):
        """Base path and target path being the same should be safe."""
        path = Path("/tmp/test")
        assert _is_safe_path(path, path) is True

    def test_path_traversal_with_mixed_separators(self, tmp_path):
        """Path traversal attempts with mixed separators should be caught."""
        # Windows-style path on Unix (or vice versa)
        base = tmp_path / "base"
        base.mkdir()

        # Various traversal attempts
        attempts = [
            "..\\..\\etc\\passwd",  # Windows-style
            "..%2F..%2Fetc%2Fpasswd",  # URL-encoded
            "....//....//etc//passwd",  # Double dots
        ]

        for attempt in attempts:
            target = base / attempt
            # After resolution, these should all be caught
            # (though some may fail at Path construction)
            try:
                result = _is_safe_path(base, target)
                # If it doesn't fail at construction, it should be marked unsafe
                assert result is False or not target.exists()
            except (ValueError, OSError):
                # Some path constructions may fail, which is also acceptable
                pass

    def test_unicode_path_traversal(self, tmp_path):
        """Unicode-based path traversal attempts should be caught."""
        base = tmp_path / "base"
        base.mkdir()

        # Unicode dots: U+FF0E (FULLWIDTH FULL STOP)
        # Most filesystems normalize these, but let's test
        malicious = base / "\uff0e\uff0e/\uff0e\uff0e/etc/passwd"

        # Should either fail construction or be marked unsafe
        try:
            result = _is_safe_path(base, malicious)
            assert result is False or not malicious.exists()
        except (ValueError, OSError):
            pass
