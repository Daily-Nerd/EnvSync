"""
Plugin Registry System for TripWire.

This module provides infrastructure for discovering, installing, and managing
plugins from remote registries (GitHub-based).

Architecture:
- PluginVersionInfo: Metadata for a specific plugin version
- PluginRegistryEntry: Complete plugin information with all versions
- PluginRegistryIndex: Complete registry with all plugins
- PluginRegistryClient: Fetches and caches registry index from GitHub
- PluginInstaller: Downloads, validates, and installs plugins

The registry is hosted on GitHub as a JSON file, similar to npm/PyPI indexes.
"""

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _validate_url_scheme(url: str) -> None:
    """
    Validate that URL uses HTTPS scheme only.

    Prevents SSRF attacks via file://, ftp://, or other dangerous schemes.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL scheme is not HTTPS
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Security: Only HTTPS URLs are allowed, got scheme '{parsed.scheme}'. " f"URL: {url}")


def _is_safe_path(base_path: Path, target_path: Path) -> bool:
    """
    Check if target path is safely contained within base path.

    Prevents path traversal attacks (Zip Slip) by ensuring extracted
    files cannot escape the intended directory using paths like ../../etc/passwd

    Args:
        base_path: Base directory that should contain target
        target_path: Target path to validate

    Returns:
        True if target_path is safely within base_path
    """
    # Resolve both paths to absolute canonical forms
    base_resolved = base_path.resolve()
    target_resolved = target_path.resolve()

    # Check if target is a child of base
    try:
        target_resolved.relative_to(base_resolved)
        return True
    except ValueError:
        return False


def _safe_extract_tarfile(tar: tarfile.TarFile, target_dir: Path) -> None:
    """
    Safely extract tarfile with path traversal protection.

    Validates each member path before extraction to prevent Zip Slip attacks.

    Args:
        tar: Open tarfile object
        target_dir: Directory to extract to

    Raises:
        RuntimeError: If any member path attempts to escape target_dir
    """
    for member in tar.getmembers():
        # Construct full target path
        member_path = target_dir / member.name

        # Validate path is safe
        if not _is_safe_path(target_dir, member_path):
            raise RuntimeError(
                f"Security: Archive member '{member.name}' attempts to escape "
                f"extraction directory. Possible path traversal attack."
            )

    # All paths validated, safe to extract
    tar.extractall(target_dir)  # nosec B202  # Path traversal validated above via _is_safe_path()


def _safe_extract_zipfile(zip_file: zipfile.ZipFile, target_dir: Path) -> None:
    """
    Safely extract zipfile with path traversal protection.

    Validates each member path before extraction to prevent Zip Slip attacks.

    Args:
        zip_file: Open zipfile object
        target_dir: Directory to extract to

    Raises:
        RuntimeError: If any member path attempts to escape target_dir
    """
    for member_name in zip_file.namelist():
        # Construct full target path
        member_path = target_dir / member_name

        # Validate path is safe
        if not _is_safe_path(target_dir, member_path):
            raise RuntimeError(
                f"Security: Archive member '{member_name}' attempts to escape "
                f"extraction directory. Possible path traversal attack."
            )

    # All paths validated, safe to extract
    zip_file.extractall(target_dir)  # nosec B202  # Path traversal validated above via _is_safe_path()


@dataclass(frozen=True)
class PluginVersionInfo:
    """
    Metadata for a specific version of a plugin.

    Attributes:
        version: Semantic version string (e.g., "0.1.0")
        release_date: ISO date string when version was released
        min_tripwire_version: Minimum TripWire version required
        max_tripwire_version: Maximum TripWire version (None = no limit)
        download_url: URL to download plugin archive (.tar.gz or .zip)
        checksum: SHA256 checksum for download verification
        downloads: Number of downloads for this version
    """

    version: str
    release_date: str
    min_tripwire_version: str
    max_tripwire_version: Optional[str] = None
    download_url: str = ""
    checksum: str = ""
    downloads: int = 0

    def __post_init__(self) -> None:
        """Validate version info after initialization."""
        if not self.version:
            raise ValueError("version cannot be empty")
        if not self.min_tripwire_version:
            raise ValueError("min_tripwire_version cannot be empty")


@dataclass(frozen=True)
class PluginRegistryEntry:
    """
    Complete information about a plugin in the registry.

    Attributes:
        name: Plugin package name (e.g., "tripwire-vault")
        display_name: Human-readable name (e.g., "HashiCorp Vault")
        description: Short description of plugin functionality
        author: Plugin author name
        author_email: Contact email for author
        homepage: Plugin website/documentation URL
        repository: Source code repository URL
        license: License identifier (e.g., "MIT", "Apache-2.0")
        tags: Search tags for discovery
        versions: Dict mapping version strings to PluginVersionInfo
        latest_version: Current stable version string
        total_downloads: Total downloads across all versions
        created_at: ISO timestamp when plugin was added to registry
        updated_at: ISO timestamp when plugin was last updated
    """

    name: str
    display_name: str
    description: str
    author: str
    author_email: str
    homepage: str
    repository: str
    license: str
    tags: List[str] = field(default_factory=list)
    versions: Dict[str, PluginVersionInfo] = field(default_factory=dict)
    latest_version: str = "0.1.0"
    total_downloads: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        """Validate registry entry after initialization."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.latest_version:
            raise ValueError("latest_version cannot be empty")

    def get_version(self, version: Optional[str] = None) -> Optional[PluginVersionInfo]:
        """
        Get specific version info, or latest if not specified.

        Args:
            version: Version string, or None for latest

        Returns:
            PluginVersionInfo if found, None otherwise
        """
        target_version = version or self.latest_version
        return self.versions.get(target_version)

    def matches_search(self, query: str) -> bool:
        """
        Check if plugin matches search query.

        Args:
            query: Search query string (case-insensitive)

        Returns:
            True if plugin matches query
        """
        query_lower = query.lower()
        return (
            query_lower in self.name.lower()
            or query_lower in self.display_name.lower()
            or query_lower in self.description.lower()
            or any(query_lower in tag.lower() for tag in self.tags)
        )


@dataclass(frozen=True)
class PluginRegistryIndex:
    """
    Complete registry index containing all available plugins.

    Attributes:
        version: Registry schema version
        updated_at: ISO timestamp when registry was last updated
        plugins: Dict mapping plugin IDs to PluginRegistryEntry
    """

    version: str
    updated_at: str
    plugins: Dict[str, PluginRegistryEntry] = field(default_factory=dict)

    def search(self, query: str) -> List[PluginRegistryEntry]:
        """
        Search plugins by query string.

        Args:
            query: Search query (matches name, description, tags)

        Returns:
            List of matching plugins, sorted by relevance
        """
        if not query:
            return list(self.plugins.values())

        matches = [plugin for plugin in self.plugins.values() if plugin.matches_search(query)]

        # Sort by relevance (name match > display_name match > description match)
        def relevance_score(plugin: PluginRegistryEntry) -> int:
            query_lower = query.lower()
            score = 0
            if query_lower in plugin.name.lower():
                score += 100
            if query_lower in plugin.display_name.lower():
                score += 50
            if query_lower in plugin.description.lower():
                score += 10
            score += sum(10 for tag in plugin.tags if query_lower in tag.lower())
            return score

        matches.sort(key=relevance_score, reverse=True)
        return matches

    def get_plugin(self, plugin_id: str) -> Optional[PluginRegistryEntry]:
        """
        Get plugin by ID.

        Args:
            plugin_id: Plugin identifier (e.g., "vault")

        Returns:
            PluginRegistryEntry if found, None otherwise
        """
        return self.plugins.get(plugin_id)


class PluginRegistryClient:
    """
    Client for fetching and caching plugin registry from GitHub.

    The registry is a JSON file hosted on GitHub that contains metadata
    about all available plugins. The client caches the registry locally
    to reduce network requests.
    """

    DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/tripwire-plugins/registry/main/registry.json"
    CACHE_DIR = Path.home() / ".tripwire" / "cache"
    CACHE_FILE = CACHE_DIR / "registry.json"

    def __init__(self, registry_url: Optional[str] = None) -> None:
        """
        Initialize registry client.

        Args:
            registry_url: Custom registry URL (defaults to official registry)
        """
        self.registry_url = registry_url or self.DEFAULT_REGISTRY_URL
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_registry(self, use_cache: bool = True) -> PluginRegistryIndex:
        """
        Fetch plugin registry from remote or cache.

        Args:
            use_cache: Whether to use cached registry if available

        Returns:
            PluginRegistryIndex

        Raises:
            RuntimeError: If registry cannot be fetched
        """
        # Try cache first if enabled
        if use_cache and self.CACHE_FILE.exists():
            try:
                return self._load_from_cache()
            except Exception:
                # Cache corrupted, fall through to remote fetch
                pass

        # Fetch from remote
        try:
            return self._fetch_from_remote()
        except Exception as e:
            # If remote fails and cache exists, try cache as fallback
            if self.CACHE_FILE.exists():
                try:
                    return self._load_from_cache()
                except Exception:
                    pass
            raise RuntimeError(f"Failed to fetch plugin registry: {e}") from e

    def _fetch_from_remote(self) -> PluginRegistryIndex:
        """Fetch registry from remote URL and cache it."""
        try:
            # Validate URL scheme for security (prevent SSRF)
            _validate_url_scheme(self.registry_url)

            with urllib.request.urlopen(
                self.registry_url, timeout=10
            ) as response:  # nosec B310  # URL scheme validated above
                data = response.read()

            # Parse JSON
            registry_data = json.loads(data)
            registry = self._parse_registry(registry_data)

            # Cache for future use
            self._save_to_cache(data)

            return registry
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error fetching registry: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid registry JSON: {e}") from e

    def _load_from_cache(self) -> PluginRegistryIndex:
        """Load registry from local cache."""
        with open(self.CACHE_FILE, "r") as f:
            registry_data = json.load(f)
        return self._parse_registry(registry_data)

    def _save_to_cache(self, data: bytes) -> None:
        """Save registry data to cache."""
        with open(self.CACHE_FILE, "wb") as f:
            f.write(data)

    def _parse_registry(self, data: Dict[str, Any]) -> PluginRegistryIndex:
        """Parse registry JSON into PluginRegistryIndex."""
        plugins = {}

        for plugin_id, plugin_data in data.get("plugins", {}).items():
            # Parse versions
            versions = {}
            for version_str, version_data in plugin_data.get("versions", {}).items():
                versions[version_str] = PluginVersionInfo(
                    version=version_data.get("version", version_str),
                    release_date=version_data.get("release_date", ""),
                    min_tripwire_version=version_data.get("min_tripwire_version", "0.10.0"),
                    max_tripwire_version=version_data.get("max_tripwire_version"),
                    download_url=version_data.get("download_url", ""),
                    checksum=version_data.get("checksum", ""),
                    downloads=version_data.get("downloads", 0),
                )

            # Parse plugin entry
            plugins[plugin_id] = PluginRegistryEntry(
                name=plugin_data.get("name", plugin_id),
                display_name=plugin_data.get("display_name", plugin_id),
                description=plugin_data.get("description", ""),
                author=plugin_data.get("author", ""),
                author_email=plugin_data.get("author_email", ""),
                homepage=plugin_data.get("homepage", ""),
                repository=plugin_data.get("repository", ""),
                license=plugin_data.get("license", ""),
                tags=plugin_data.get("tags", []),
                versions=versions,
                latest_version=plugin_data.get("latest_version", "0.1.0"),
                total_downloads=plugin_data.get("total_downloads", 0),
                created_at=plugin_data.get("created_at", ""),
                updated_at=plugin_data.get("updated_at", ""),
            )

        return PluginRegistryIndex(
            version=data.get("version", "1.0.0"),
            updated_at=data.get("updated_at", ""),
            plugins=plugins,
        )

    def clear_cache(self) -> None:
        """Clear local registry cache."""
        if self.CACHE_FILE.exists():
            self.CACHE_FILE.unlink()


class PluginInstaller:
    """
    Plugin installer for downloading, validating, and installing plugins.

    This class handles the complete installation workflow:
    1. Download plugin archive from registry
    2. Verify checksum
    3. Extract archive
    4. Validate plugin structure
    5. Install to plugins directory
    """

    PLUGINS_DIR = Path.home() / ".tripwire" / "plugins"

    def __init__(self, registry_client: Optional[PluginRegistryClient] = None) -> None:
        """
        Initialize plugin installer.

        Args:
            registry_client: Custom registry client (defaults to default client)
        """
        self.registry_client = registry_client or PluginRegistryClient()
        self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    def install(
        self,
        plugin_id: str,
        version: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        """
        Install plugin from registry.

        Args:
            plugin_id: Plugin identifier (e.g., "vault")
            version: Specific version to install (None = latest)
            force: Force reinstall if already installed

        Returns:
            Path to installed plugin directory

        Raises:
            RuntimeError: If installation fails
        """
        # Fetch registry
        registry = self.registry_client.fetch_registry()

        # Get plugin entry
        plugin_entry = registry.get_plugin(plugin_id)
        if not plugin_entry:
            raise RuntimeError(f"Plugin '{plugin_id}' not found in registry")

        # Get version info
        version_info = plugin_entry.get_version(version)
        if not version_info:
            raise RuntimeError(f"Version '{version}' not found for plugin '{plugin_id}'")

        # Check if already installed
        plugin_dir = self.PLUGINS_DIR / plugin_id
        if plugin_dir.exists() and not force:
            raise RuntimeError(f"Plugin '{plugin_id}' is already installed. " f"Use --force to reinstall.")

        # Download plugin
        archive_path = self._download_plugin(version_info)

        try:
            # Verify checksum
            self._verify_checksum(archive_path, version_info.checksum)

            # Extract archive
            extract_dir = self._extract_archive(archive_path)

            # Install plugin
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)

            # Move extracted files to plugin directory
            shutil.move(str(extract_dir), str(plugin_dir))

            return plugin_dir
        finally:
            # Cleanup temporary files
            if archive_path.exists():
                archive_path.unlink()

    def uninstall(self, plugin_id: str) -> None:
        """
        Uninstall plugin.

        Args:
            plugin_id: Plugin identifier

        Raises:
            RuntimeError: If plugin is not installed
        """
        plugin_dir = self.PLUGINS_DIR / plugin_id
        if not plugin_dir.exists():
            raise RuntimeError(f"Plugin '{plugin_id}' is not installed")

        shutil.rmtree(plugin_dir)

    def list_installed(self) -> List[str]:
        """
        List installed plugins.

        Returns:
            List of installed plugin IDs
        """
        if not self.PLUGINS_DIR.exists():
            return []

        return [d.name for d in self.PLUGINS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]

    def is_installed(self, plugin_id: str) -> bool:
        """
        Check if plugin is installed.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if installed
        """
        return (self.PLUGINS_DIR / plugin_id).exists()

    def _download_plugin(self, version_info: PluginVersionInfo) -> Path:
        """Download plugin archive to temporary directory."""
        if not version_info.download_url:
            raise RuntimeError("No download URL available for plugin")

        # Validate URL scheme for security (prevent SSRF)
        _validate_url_scheme(version_info.download_url)

        # Download to temporary file
        temp_dir = Path(tempfile.gettempdir())
        archive_path = temp_dir / f"tripwire-plugin-{version_info.version}.tar.gz"

        try:
            with urllib.request.urlopen(
                version_info.download_url, timeout=30
            ) as response:  # nosec B310  # URL scheme validated above
                with open(archive_path, "wb") as f:
                    f.write(response.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to download plugin: {e}") from e

        return archive_path

    def _verify_checksum(self, archive_path: Path, expected_checksum: str) -> None:
        """Verify SHA256 checksum of downloaded archive."""
        if not expected_checksum:
            # No checksum provided, skip verification (not recommended)
            return

        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        actual_checksum = f"sha256:{sha256_hash.hexdigest()}"

        if actual_checksum != expected_checksum:
            raise RuntimeError(f"Checksum mismatch! Expected {expected_checksum}, " f"got {actual_checksum}")

    def _extract_archive(self, archive_path: Path) -> Path:
        """Extract plugin archive to temporary directory with path traversal protection."""
        temp_dir = Path(tempfile.mkdtemp(prefix="tripwire-plugin-"))

        try:
            if archive_path.suffix == ".gz" or archive_path.suffixes[-2:] == [".tar", ".gz"]:
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Use safe extraction to prevent Zip Slip attacks
                    _safe_extract_tarfile(tar, temp_dir)  # noqa: S202
            elif archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_file:
                    # Use safe extraction to prevent Zip Slip attacks
                    _safe_extract_zipfile(zip_file, temp_dir)  # noqa: S202
            else:
                raise RuntimeError(f"Unsupported archive format: {archive_path.suffix}")
        except Exception as e:
            shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to extract archive: {e}") from e

        # Find the actual plugin directory (handle archives with root directory)
        extracted_items = list(temp_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            # Archive has single root directory, use it
            return extracted_items[0]
        else:
            # Archive has multiple items at root, use temp_dir
            return temp_dir
