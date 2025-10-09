"""Tests for configuration data models."""

from pathlib import Path

import pytest

from tripwire.config.models import ConfigDiff, ConfigFormat, ConfigValue, SourceMetadata


class TestConfigFormat:
    """Tests for ConfigFormat enum."""

    def test_format_values(self):
        """Test enum values are correct."""
        assert ConfigFormat.ENV.value == "env"
        assert ConfigFormat.TOML.value == "toml"

    def test_format_membership(self):
        """Test format membership."""
        assert ConfigFormat.ENV in ConfigFormat
        assert ConfigFormat.TOML in ConfigFormat


class TestSourceMetadata:
    """Tests for SourceMetadata dataclass."""

    def test_minimal_metadata(self):
        """Test creating metadata with minimal fields."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)

        assert metadata.source_type == ConfigFormat.ENV
        assert metadata.file_path is None
        assert metadata.line_number is None
        assert metadata.last_modified is None
        assert metadata.is_secret is False
        assert metadata.comment is None

    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = SourceMetadata(
            source_type=ConfigFormat.ENV,
            file_path=Path(".env"),
            line_number=42,
            last_modified=1234567890.0,
            is_secret=True,
            comment="Database configuration",
        )

        assert metadata.source_type == ConfigFormat.ENV
        assert metadata.file_path == Path(".env")
        assert metadata.line_number == 42
        assert metadata.last_modified == 1234567890.0
        assert metadata.is_secret is True
        assert metadata.comment == "Database configuration"

    def test_metadata_is_frozen(self):
        """Test that metadata is immutable."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)

        with pytest.raises(AttributeError):
            metadata.source_type = ConfigFormat.TOML


class TestConfigValue:
    """Tests for ConfigValue dataclass."""

    def test_minimal_config_value(self):
        """Test creating config value with minimal fields."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        value = ConfigValue(key="PORT", value="8000", raw_value="8000", metadata=metadata)

        assert value.key == "PORT"
        assert value.value == "8000"
        assert value.raw_value == "8000"
        assert value.metadata == metadata

    def test_typed_config_value(self):
        """Test config value with typed value."""
        metadata = SourceMetadata(source_type=ConfigFormat.TOML)
        value = ConfigValue(key="PORT", value=8000, raw_value="8000", metadata=metadata)

        assert value.key == "PORT"
        assert value.value == 8000
        assert isinstance(value.value, int)
        assert value.raw_value == "8000"

    def test_str_returns_raw_value(self):
        """Test __str__ returns raw value."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        value = ConfigValue(key="PORT", value=8000, raw_value="8000", metadata=metadata)

        assert str(value) == "8000"

    def test_repr_is_informative(self):
        """Test __repr__ includes key info."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        value = ConfigValue(key="PORT", value=8000, raw_value="8000", metadata=metadata)

        repr_str = repr(value)
        assert "PORT" in repr_str
        assert "8000" in repr_str
        assert "env" in repr_str


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_empty_diff(self):
        """Test diff with no changes."""
        diff = ConfigDiff(added={}, removed={}, modified={}, unchanged={})

        assert not diff.has_changes
        assert diff.summary() == "No differences"

    def test_diff_with_additions(self):
        """Test diff with added variables."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        added = {"NEW_VAR": ConfigValue("NEW_VAR", "value", "value", metadata)}

        diff = ConfigDiff(added=added, removed={}, modified={}, unchanged={})

        assert diff.has_changes
        assert "1 added" in diff.summary()
        assert len(diff.added) == 1

    def test_diff_with_removals(self):
        """Test diff with removed variables."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        removed = {"OLD_VAR": ConfigValue("OLD_VAR", "value", "value", metadata)}

        diff = ConfigDiff(added={}, removed=removed, modified={}, unchanged={})

        assert diff.has_changes
        assert "1 removed" in diff.summary()
        assert len(diff.removed) == 1

    def test_diff_with_modifications(self):
        """Test diff with modified variables."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        old_val = ConfigValue("PORT", "8000", "8000", metadata)
        new_val = ConfigValue("PORT", "3000", "3000", metadata)
        modified = {"PORT": (old_val, new_val)}

        diff = ConfigDiff(added={}, removed={}, modified=modified, unchanged={})

        assert diff.has_changes
        assert "1 modified" in diff.summary()
        assert len(diff.modified) == 1

    def test_diff_with_all_changes(self):
        """Test diff with all types of changes."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)

        added = {"NEW_VAR": ConfigValue("NEW_VAR", "value", "value", metadata)}
        removed = {"OLD_VAR": ConfigValue("OLD_VAR", "value", "value", metadata)}
        old_val = ConfigValue("PORT", "8000", "8000", metadata)
        new_val = ConfigValue("PORT", "3000", "3000", metadata)
        modified = {"PORT": (old_val, new_val)}
        unchanged = {"HOST": ConfigValue("HOST", "localhost", "localhost", metadata)}

        diff = ConfigDiff(added=added, removed=removed, modified=modified, unchanged=unchanged)

        assert diff.has_changes
        summary = diff.summary()
        assert "1 added" in summary
        assert "1 removed" in summary
        assert "1 modified" in summary

    def test_diff_summary_order(self):
        """Test summary lists changes in consistent order."""
        metadata = SourceMetadata(source_type=ConfigFormat.ENV)

        added = {f"VAR_{i}": ConfigValue(f"VAR_{i}", "v", "v", metadata) for i in range(2)}
        removed = {f"OLD_{i}": ConfigValue(f"OLD_{i}", "v", "v", metadata) for i in range(3)}
        old_val = ConfigValue("PORT", "8000", "8000", metadata)
        new_val = ConfigValue("PORT", "3000", "3000", metadata)
        modified = {"PORT": (old_val, new_val)}

        diff = ConfigDiff(added=added, removed=removed, modified=modified, unchanged={})

        summary = diff.summary()
        assert "2 added" in summary
        assert "3 removed" in summary
        assert "1 modified" in summary
