"""TripWire tool configuration from pyproject.toml.

This module handles loading TripWire TOOL settings from [tool.tripwire] section
in pyproject.toml. These are settings for the TripWire CLI tool itself, NOT
application environment variable configuration.

Example pyproject.toml:
    [tool.tripwire]
    default_format = "table"           # Default output format for CLI
    strict_mode = true                 # Exit 1 on warnings
    schema_file = ".tripwire.toml"    # Schema location
    scan_git_history = true            # Enable git scanning
    max_commits = 1000                 # Git scan depth
    default_environment = "development" # Default env
"""

import tomllib
from pathlib import Path
from typing import Any

# Default settings for TripWire tool
DEFAULT_TOOL_CONFIG: dict[str, Any] = {
    "default_format": "table",
    "strict_mode": False,
    "schema_file": ".tripwire.toml",
    "scan_git_history": True,
    "max_commits": 1000,
    "default_environment": "development",
}


def load_tool_config(pyproject_path: str | Path = "pyproject.toml") -> dict[str, Any]:
    """Load TripWire tool settings from pyproject.toml [tool.tripwire].

    This loads configuration for the TripWire CLI tool itself, NOT your
    application's environment variable configuration. Application config
    should be defined in .tripwire.toml schema files.

    Supported settings:
        - default_format: Default output format (table/json/summary)
        - strict_mode: Exit 1 on warnings
        - schema_file: Path to .tripwire.toml
        - scan_git_history: Enable git scanning
        - max_commits: Git scan depth
        - default_environment: Default environment name

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Dict of TripWire tool settings with defaults applied

    Examples:
        >>> config = load_tool_config()
        >>> config['default_format']
        'table'

        >>> config = load_tool_config('/path/to/pyproject.toml')
        >>> config['strict_mode']
        False
    """
    pyproject_path = Path(pyproject_path)

    # Start with defaults
    config = DEFAULT_TOOL_CONFIG.copy()

    # If no pyproject.toml, return defaults
    if not pyproject_path.exists():
        return config

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Extract [tool.tripwire] section if it exists
        if "tool" in data and "tripwire" in data["tool"]:
            tool_config = data["tool"]["tripwire"]

            # Update config with user-defined values
            for key in DEFAULT_TOOL_CONFIG:
                if key in tool_config:
                    config[key] = tool_config[key]

    except (tomllib.TOMLDecodeError, OSError, KeyError):
        # If file is invalid or can't be read, return defaults
        # This is intentionally silent - tool should work with defaults
        pass

    return config


def get_setting(key: str, default: Any = None, pyproject_path: str | Path = "pyproject.toml") -> Any:
    """Get a specific TripWire tool setting.

    Args:
        key: Setting name (e.g., 'default_format')
        default: Default value if setting not found
        pyproject_path: Path to pyproject.toml file

    Returns:
        Setting value or default

    Examples:
        >>> get_setting('default_format')
        'table'

        >>> get_setting('custom_setting', default='fallback')
        'fallback'
    """
    config = load_tool_config(pyproject_path)
    return config.get(key, default)
