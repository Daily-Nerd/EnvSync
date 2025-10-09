"""Unified configuration management for TripWire.

This package provides a format-agnostic abstraction layer for configuration
sources, supporting .env and TOML formats with a plugin system for future
extensions.

It also re-exports the original config.py module for backward compatibility.

Example:
    >>> from tripwire.config import ConfigRepository
    >>> repo = ConfigRepository.from_file(".env").load()
    >>> config = repo.get("DATABASE_URL")
    >>> print(config.value)
    postgresql://localhost/mydb

    >>> # Compare configurations
    >>> from tripwire.config import ConfigRepository
    >>> repo1 = ConfigRepository.from_file(".env").load()
    >>> repo2 = ConfigRepository.from_file("pyproject.toml").load()
    >>> diff = repo1.diff(repo2)
    >>> print(diff.summary())
    2 added, 1 removed, 3 modified
"""

# Re-export original config.py module for backward compatibility
# Note: This imports from the parent module (tripwire.config is a package,
# but there's also a tripwire/config.py module that needs to be accessible)
import sys
from pathlib import Path

# New unified config architecture (v0.4.0)
from .models import ConfigDiff, ConfigFormat, ConfigValue, SourceMetadata
from .repository import ConfigRepository, MergeStrategy
from .source import ConfigSource
from .sources.env_file import EnvFileSource
from .sources.toml_source import TOMLSource

# Import from the sibling config.py module
_parent_path = Path(__file__).parent.parent
_config_module_path = _parent_path / "config.py"

# Import the config.py module manually to avoid circular import
import importlib.util

spec = importlib.util.spec_from_file_location("_tripwire_config_legacy", _config_module_path)
if spec and spec.loader:
    _legacy_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_legacy_config)

    # Re-export from legacy config module
    TripWireConfig = _legacy_config.TripWireConfig
    VariableConfig = _legacy_config.VariableConfig
    apply_config_to_tripwire = _legacy_config.apply_config_to_tripwire
    find_config_file = _legacy_config.find_config_file
    generate_example_config = _legacy_config.generate_example_config
    load_config = _legacy_config.load_config
    parse_config = _legacy_config.parse_config
    parse_variable_config = _legacy_config.parse_variable_config
    validate_config = _legacy_config.validate_config

__all__ = [
    # New unified config architecture
    "ConfigDiff",
    "ConfigFormat",
    "ConfigValue",
    "ConfigRepository",
    "ConfigSource",
    "EnvFileSource",
    "MergeStrategy",
    "SourceMetadata",
    "TOMLSource",
    # Legacy config.py re-exports
    "TripWireConfig",
    "VariableConfig",
    "apply_config_to_tripwire",
    "find_config_file",
    "generate_example_config",
    "load_config",
    "parse_config",
    "parse_variable_config",
    "validate_config",
]
