"""Tests for TOMLSource adapter."""

from pathlib import Path

import pytest

from tripwire.config.models import ConfigFormat
from tripwire.config.sources.toml_source import TOMLSource


class TestTOMLSource:
    """Tests for TOMLSource adapter."""

    def test_format_name(self, tmp_path):
        """Test format_name property returns TOML."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        source = TOMLSource(toml_file)
        assert source.format_name == ConfigFormat.TOML

    def test_file_path(self, tmp_path):
        """Test file_path property returns path."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        source = TOMLSource(toml_file)
        assert source.file_path == toml_file

    def test_load_simple_toml(self, tmp_path):
        """Test loading simple TOML file."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('[tool.tripwire]\nport = 8000\nhost = "localhost"\n')

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        assert "port" in config
        assert config["port"].value == 8000
        assert isinstance(config["port"].value, int)
        assert config["port"].raw_value == "8000"

        assert "host" in config
        assert config["host"].value == "localhost"

    def test_load_nested_sections(self, tmp_path):
        """Test loading nested TOML sections."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire.database]\n" 'host = "localhost"\n' "port = 5432\n")

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        assert "database.host" in config
        assert config["database.host"].value == "localhost"
        assert "database.port" in config
        assert config["database.port"].value == 5432

    def test_load_preserves_types(self, tmp_path):
        """Test that TOML types are preserved."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            "[tool.tripwire]\n"
            "int_val = 42\n"
            "float_val = 3.14\n"
            "bool_val = true\n"
            'string_val = "hello"\n'
            "list_val = [1, 2, 3]\n"
        )

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        assert config["int_val"].value == 42
        assert isinstance(config["int_val"].value, int)

        assert config["float_val"].value == 3.14
        assert isinstance(config["float_val"].value, float)

        assert config["bool_val"].value is True
        assert isinstance(config["bool_val"].value, bool)

        assert config["string_val"].value == "hello"
        assert isinstance(config["string_val"].value, str)

        assert config["list_val"].value == [1, 2, 3]
        assert isinstance(config["list_val"].value, list)

    def test_load_boolean_raw_value(self, tmp_path):
        """Test boolean raw value is lowercase."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nenabled = true\ndisabled = false\n")

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        assert config["enabled"].raw_value == "true"
        assert config["disabled"].raw_value == "false"

    def test_load_tracks_metadata(self, tmp_path):
        """Test that metadata is properly tracked."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        metadata = config["port"].metadata
        assert metadata.source_type == ConfigFormat.TOML
        assert metadata.file_path == toml_file
        assert metadata.last_modified is not None
        assert metadata.line_number is None  # TOML parsers don't provide line numbers

    def test_load_detects_secrets(self, tmp_path):
        """Test secret detection based on key names."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            "[tool.tripwire]\n" 'api_key = "secret123"\n' 'database_password = "pass123"\n' 'regular_var = "value"\n'
        )

        source = TOMLSource(toml_file, section="tool.tripwire")
        config = source.load()

        assert config["api_key"].metadata.is_secret is True
        assert config["database_password"].metadata.is_secret is True
        assert config["regular_var"].metadata.is_secret is False

    def test_load_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        toml_file = tmp_path / "nonexistent.toml"

        source = TOMLSource(toml_file)

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            source.load()

    def test_load_section_not_found(self, tmp_path):
        """Test error when section doesn't exist."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[other.section]\nvalue = 1\n")

        source = TOMLSource(toml_file, section="tool.tripwire")

        with pytest.raises(ValueError, match="Section 'tool.tripwire' not found"):
            source.load()

    def test_save_new_file(self, tmp_path):
        """Test saving to new TOML file."""
        toml_file = tmp_path / "config.toml"

        source = TOMLSource(toml_file, section="tool.tripwire")

        # Load to get metadata structure
        from tripwire.config.models import ConfigValue, SourceMetadata

        metadata = SourceMetadata(source_type=ConfigFormat.TOML)
        data = {
            "port": ConfigValue("port", 8000, "8000", metadata),
            "host": ConfigValue("host", "localhost", "localhost", metadata),
        }

        source.save(data)

        assert toml_file.exists()

        # Reload and verify
        source2 = TOMLSource(toml_file, section="tool.tripwire")
        config = source2.load()

        assert config["port"].value == 8000
        assert config["host"].value == "localhost"

    def test_save_updates_existing_section(self, tmp_path):
        """Test saving updates existing section."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        source = TOMLSource(toml_file, section="tool.tripwire")

        from tripwire.config.models import ConfigValue, SourceMetadata

        metadata = SourceMetadata(source_type=ConfigFormat.TOML)
        data = {
            "port": ConfigValue("port", 3000, "3000", metadata),
            "host": ConfigValue("host", "0.0.0.0", "0.0.0.0", metadata),
        }

        source.save(data)

        # Reload and verify
        source2 = TOMLSource(toml_file, section="tool.tripwire")
        config = source2.load()

        assert config["port"].value == 3000
        assert config["host"].value == "0.0.0.0"

    def test_save_preserves_other_sections(self, tmp_path):
        """Test saving preserves other sections."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[project]\n" 'name = "myproject"\n' "[tool.tripwire]\n" "port = 8000\n")

        source = TOMLSource(toml_file, section="tool.tripwire")

        from tripwire.config.models import ConfigValue, SourceMetadata

        metadata = SourceMetadata(source_type=ConfigFormat.TOML)
        data = {
            "port": ConfigValue("port", 3000, "3000", metadata),
        }

        source.save(data)

        # Verify other section is preserved
        import tomllib

        with open(toml_file, "rb") as f:
            toml_data = tomllib.load(f)

        assert "project" in toml_data
        assert toml_data["project"]["name"] == "myproject"
        assert toml_data["tool"]["tripwire"]["port"] == 3000

    def test_save_nested_keys(self, tmp_path):
        """Test saving with nested (dotted) keys."""
        toml_file = tmp_path / "config.toml"

        source = TOMLSource(toml_file, section="tool.tripwire")

        from tripwire.config.models import ConfigValue, SourceMetadata

        metadata = SourceMetadata(source_type=ConfigFormat.TOML)
        data = {
            "database.host": ConfigValue("database.host", "localhost", "localhost", metadata),
            "database.port": ConfigValue("database.port", 5432, "5432", metadata),
        }

        source.save(data)

        # Reload and verify nesting
        source2 = TOMLSource(toml_file, section="tool.tripwire")
        config = source2.load()

        assert config["database.host"].value == "localhost"
        assert config["database.port"].value == 5432

    def test_roundtrip_load_save(self, tmp_path):
        """Test loading and saving preserves data and types."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            "[tool.tripwire]\n" "port = 8000\n" 'host = "localhost"\n' "debug = true\n" "timeout = 30.5\n"
        )

        source = TOMLSource(toml_file, section="tool.tripwire")

        # Load
        config = source.load()

        # Modify
        from tripwire.config.models import ConfigValue

        metadata = config["port"].metadata
        config["port"] = ConfigValue("port", 3000, "3000", metadata)

        # Save
        source.save(config)

        # Reload
        config2 = source.load()

        assert config2["port"].value == 3000
        assert isinstance(config2["port"].value, int)
        assert config2["host"].value == "localhost"
        assert config2["debug"].value is True
        assert isinstance(config2["debug"].value, bool)
        assert config2["timeout"].value == 30.5
        assert isinstance(config2["timeout"].value, float)

    def test_supports_feature(self, tmp_path):
        """Test feature support queries."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        source = TOMLSource(toml_file)

        assert source.supports_feature("comments") is False  # tomli doesn't preserve
        assert source.supports_feature("multiline") is True
        assert source.supports_feature("nested") is True
        assert source.supports_feature("typed_values") is True
        assert source.supports_feature("sections") is True
        assert source.supports_feature("unknown") is False
