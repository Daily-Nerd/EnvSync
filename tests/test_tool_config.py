"""Tests for TripWire tool configuration from pyproject.toml."""

import tempfile
from pathlib import Path

from tripwire.tool_config import DEFAULT_TOOL_CONFIG, get_setting, load_tool_config


def test_load_tool_config_defaults_when_file_missing():
    """Test that defaults are returned when pyproject.toml doesn't exist."""
    config = load_tool_config("nonexistent.toml")

    assert config == DEFAULT_TOOL_CONFIG
    assert config["default_format"] == "table"
    assert config["strict_mode"] is False
    assert config["schema_file"] == ".tripwire.toml"
    assert config["scan_git_history"] is True
    assert config["max_commits"] == 1000
    assert config["default_environment"] == "development"


def test_load_tool_config_with_valid_config():
    """Test loading valid tool configuration from pyproject.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        # Create a pyproject.toml with tool.tripwire section
        pyproject_content = """
[tool.tripwire]
default_format = "json"
strict_mode = true
schema_file = "custom-schema.toml"
scan_git_history = false
max_commits = 500
default_environment = "production"
"""
        pyproject_path.write_text(pyproject_content)

        config = load_tool_config(pyproject_path)

        assert config["default_format"] == "json"
        assert config["strict_mode"] is True
        assert config["schema_file"] == "custom-schema.toml"
        assert config["scan_git_history"] is False
        assert config["max_commits"] == 500
        assert config["default_environment"] == "production"


def test_load_tool_config_partial_config():
    """Test that partial configuration merges with defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        # Only override some settings
        pyproject_content = """
[tool.tripwire]
default_format = "summary"
strict_mode = true
"""
        pyproject_path.write_text(pyproject_content)

        config = load_tool_config(pyproject_path)

        # Overridden values
        assert config["default_format"] == "summary"
        assert config["strict_mode"] is True

        # Default values
        assert config["schema_file"] == ".tripwire.toml"
        assert config["scan_git_history"] is True
        assert config["max_commits"] == 1000
        assert config["default_environment"] == "development"


def test_load_tool_config_without_tool_section():
    """Test loading pyproject.toml without [tool.tripwire] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        # pyproject.toml without tool.tripwire
        pyproject_content = """
[project]
name = "my-project"
version = "1.0.0"
"""
        pyproject_path.write_text(pyproject_content)

        config = load_tool_config(pyproject_path)

        # Should return all defaults
        assert config == DEFAULT_TOOL_CONFIG


def test_load_tool_config_invalid_toml():
    """Test that invalid TOML returns defaults without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        # Invalid TOML syntax
        pyproject_content = """
[tool.tripwire
invalid syntax here
"""
        pyproject_path.write_text(pyproject_content)

        # Should not raise, just return defaults
        config = load_tool_config(pyproject_path)
        assert config == DEFAULT_TOOL_CONFIG


def test_load_tool_config_with_extra_keys():
    """Test that extra unknown keys are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
default_format = "table"
unknown_setting = "some_value"
another_unknown = 123
"""
        pyproject_path.write_text(pyproject_content)

        config = load_tool_config(pyproject_path)

        # Known setting should be loaded
        assert config["default_format"] == "table"

        # Unknown settings should not be in config
        assert "unknown_setting" not in config
        assert "another_unknown" not in config


def test_get_setting_existing_key():
    """Test get_setting for existing key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
default_format = "json"
"""
        pyproject_path.write_text(pyproject_content)

        value = get_setting("default_format", pyproject_path=pyproject_path)
        assert value == "json"


def test_get_setting_missing_key_with_default():
    """Test get_setting for missing key with default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
default_format = "json"
"""
        pyproject_path.write_text(pyproject_content)

        value = get_setting("nonexistent_key", default="fallback", pyproject_path=pyproject_path)
        assert value == "fallback"


def test_get_setting_missing_key_from_defaults():
    """Test get_setting falls back to DEFAULT_TOOL_CONFIG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        # Empty config
        pyproject_content = """
[project]
name = "test"
"""
        pyproject_path.write_text(pyproject_content)

        # Should get value from DEFAULT_TOOL_CONFIG
        value = get_setting("max_commits", pyproject_path=pyproject_path)
        assert value == 1000


def test_load_tool_config_with_path_object():
    """Test that load_tool_config accepts Path objects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
strict_mode = true
"""
        pyproject_path.write_text(pyproject_content)

        # Pass as Path object
        config = load_tool_config(pyproject_path)
        assert config["strict_mode"] is True


def test_load_tool_config_with_string_path():
    """Test that load_tool_config accepts string paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
strict_mode = true
"""
        pyproject_path.write_text(pyproject_content)

        # Pass as string
        config = load_tool_config(str(pyproject_path))
        assert config["strict_mode"] is True


def test_load_tool_config_all_supported_types():
    """Test that all value types are correctly parsed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"

        pyproject_content = """
[tool.tripwire]
default_format = "table"        # string
strict_mode = true              # boolean
max_commits = 1500              # integer
schema_file = ".custom.toml"    # string
scan_git_history = false        # boolean
default_environment = "staging" # string
"""
        pyproject_path.write_text(pyproject_content)

        config = load_tool_config(pyproject_path)

        assert isinstance(config["default_format"], str)
        assert isinstance(config["strict_mode"], bool)
        assert isinstance(config["max_commits"], int)
        assert isinstance(config["schema_file"], str)
        assert isinstance(config["scan_git_history"], bool)
        assert isinstance(config["default_environment"], str)
