"""Tests for EnvFileSource adapter."""

from pathlib import Path

import pytest

from tripwire.config.models import ConfigFormat, ConfigValue, SourceMetadata
from tripwire.config.sources.env_file import EnvFileSource


class TestEnvFileSource:
    """Tests for EnvFileSource adapter."""

    def test_format_name(self, tmp_path):
        """Test format_name property returns ENV."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        source = EnvFileSource(env_file)
        assert source.format_name == ConfigFormat.ENV

    def test_file_path(self, tmp_path):
        """Test file_path property returns path."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        source = EnvFileSource(env_file)
        assert source.file_path == env_file

    def test_load_simple_env(self, tmp_path):
        """Test loading simple .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        source = EnvFileSource(env_file)
        config = source.load()

        assert "PORT" in config
        assert config["PORT"].value == "8000"
        assert config["PORT"].raw_value == "8000"
        assert config["PORT"].key == "PORT"

        assert "HOST" in config
        assert config["HOST"].value == "localhost"

    def test_load_with_comments(self, tmp_path):
        """Test loading .env file with comments."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# Database configuration\n" "DATABASE_URL=postgresql://localhost/db  # Main database\n" "PORT=8000\n"
        )

        source = EnvFileSource(env_file)
        config = source.load()

        assert "DATABASE_URL" in config
        assert config["DATABASE_URL"].metadata.comment == "Main database"

    def test_load_empty_values(self, tmp_path):
        """Test loading .env file with empty values."""
        env_file = tmp_path / ".env"
        env_file.write_text("EMPTY_VAR=\nNONEMPTY=value\n")

        source = EnvFileSource(env_file)
        config = source.load()

        assert "EMPTY_VAR" in config
        assert config["EMPTY_VAR"].value == ""

    def test_load_tracks_line_numbers(self, tmp_path):
        """Test that line numbers are tracked."""
        env_file = tmp_path / ".env"
        env_file.write_text("# Comment\nPORT=8000\n# Another comment\nHOST=localhost\n")

        source = EnvFileSource(env_file)
        config = source.load()

        assert config["PORT"].metadata.line_number == 2
        assert config["HOST"].metadata.line_number == 4

    def test_load_tracks_metadata(self, tmp_path):
        """Test that metadata is properly tracked."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        source = EnvFileSource(env_file)
        config = source.load()

        metadata = config["PORT"].metadata
        assert metadata.source_type == ConfigFormat.ENV
        assert metadata.file_path == env_file
        assert metadata.last_modified is not None

    def test_load_detects_secrets(self, tmp_path):
        """Test secret detection based on key names."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "API_KEY=secret123\n" "DATABASE_PASSWORD=pass123\n" "OAUTH_TOKEN=token123\n" "REGULAR_VAR=value\n"
        )

        source = EnvFileSource(env_file)
        config = source.load()

        assert config["API_KEY"].metadata.is_secret is True
        assert config["DATABASE_PASSWORD"].metadata.is_secret is True
        assert config["OAUTH_TOKEN"].metadata.is_secret is True
        assert config["REGULAR_VAR"].metadata.is_secret is False

    def test_load_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        env_file = tmp_path / "nonexistent.env"

        source = EnvFileSource(env_file)

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            source.load()

    def test_save_new_file(self, tmp_path):
        """Test saving to new .env file."""
        env_file = tmp_path / ".env"

        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        data = {
            "PORT": ConfigValue("PORT", "8000", "8000", metadata),
            "HOST": ConfigValue("HOST", "localhost", "localhost", metadata),
        }

        source = EnvFileSource(env_file)
        source.save(data)

        assert env_file.exists()
        content = env_file.read_text()
        assert "PORT=8000" in content
        assert "HOST=localhost" in content

    def test_save_updates_existing_file(self, tmp_path):
        """Test saving updates existing variables."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        data = {
            "PORT": ConfigValue("PORT", "3000", "3000", metadata),
            "HOST": ConfigValue("HOST", "localhost", "localhost", metadata),
        }

        source = EnvFileSource(env_file)
        source.save(data)

        content = env_file.read_text()
        assert "PORT=3000" in content
        assert "HOST=localhost" in content

    def test_save_preserves_comments(self, tmp_path):
        """Test saving preserves existing comments."""
        env_file = tmp_path / ".env"
        env_file.write_text("# Database configuration\n" "PORT=8000  # Server port\n" "HOST=localhost\n")

        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        data = {
            "PORT": ConfigValue("PORT", "3000", "3000", metadata),
            "HOST": ConfigValue("HOST", "0.0.0.0", "0.0.0.0", metadata),
        }

        source = EnvFileSource(env_file)
        source.save(data)

        content = env_file.read_text()
        assert "# Database configuration" in content
        assert "# Server port" in content

    def test_save_appends_new_variables(self, tmp_path):
        """Test saving appends new variables."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        data = {
            "PORT": ConfigValue("PORT", "8000", "8000", metadata),
            "NEW_VAR": ConfigValue("NEW_VAR", "value", "value", metadata),
        }

        source = EnvFileSource(env_file)
        source.save(data)

        content = env_file.read_text()
        assert "PORT=8000" in content
        assert "NEW_VAR=value" in content

    def test_save_with_metadata_comments(self, tmp_path):
        """Test saving with comments from metadata."""
        env_file = tmp_path / ".env"

        metadata = SourceMetadata(source_type=ConfigFormat.ENV, comment="Database configuration")
        data = {
            "DATABASE_URL": ConfigValue(
                "DATABASE_URL", "postgresql://localhost/db", "postgresql://localhost/db", metadata
            ),
        }

        source = EnvFileSource(env_file)
        source.save(data)

        content = env_file.read_text()
        assert "DATABASE_URL=postgresql://localhost/db" in content
        assert "# Database configuration" in content

    def test_roundtrip_load_save(self, tmp_path):
        """Test loading and saving preserves data."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        source = EnvFileSource(env_file)

        # Load
        config = source.load()

        # Modify
        metadata = config["PORT"].metadata
        config["PORT"] = ConfigValue("PORT", "3000", "3000", metadata)

        # Save
        source.save(config)

        # Reload
        config2 = source.load()

        assert config2["PORT"].value == "3000"
        assert config2["HOST"].value == "localhost"

    def test_supports_feature(self, tmp_path):
        """Test feature support queries."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        source = EnvFileSource(env_file)

        assert source.supports_feature("comments") is True
        assert source.supports_feature("multiline") is True
        assert source.supports_feature("nested") is False
        assert source.supports_feature("typed_values") is False
        assert source.supports_feature("unknown") is False
