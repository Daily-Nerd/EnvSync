"""Tests for EnvFileLoader and environment variable sources."""

import os
from pathlib import Path
from typing import Dict

import pytest

from tripwire.core.loader import DotenvFileSource, EnvFileLoader, EnvSource
from tripwire.exceptions import EnvFileNotFoundError


class MockEnvSource(EnvSource):
    """Mock source for testing."""

    def __init__(self, variables: Dict[str, str]):
        self.variables = variables

    def load(self) -> Dict[str, str]:
        # Load into os.environ
        for key, value in self.variables.items():
            os.environ[key] = value
        return self.variables


class TestEnvSource:
    """Test suite for EnvSource abstract base class."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        # Store original state
        original_env = os.environ.copy()
        yield
        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)

    def test_env_source_is_abstract(self):
        """Test that EnvSource cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EnvSource()  # type: ignore

    def test_mock_source_implements_interface(self):
        """Test that concrete implementations work."""
        source = MockEnvSource({"TEST_VAR": "test_value"})
        loaded = source.load()
        assert loaded == {"TEST_VAR": "test_value"}
        assert os.getenv("TEST_VAR") == "test_value"


class TestDotenvFileSource:
    """Test suite for DotenvFileSource."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        # Store original state
        original_env = os.environ.copy()
        yield
        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)

    def test_load_existing_file(self, tmp_path):
        """Test loading an existing .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\nANOTHER_VAR=another_value\n")

        source = DotenvFileSource(env_file, override=False)
        loaded = source.load()

        assert "TEST_VAR" in loaded
        assert loaded["TEST_VAR"] == "test_value"
        assert "ANOTHER_VAR" in loaded
        assert loaded["ANOTHER_VAR"] == "another_value"

        # Verify loaded into os.environ
        assert os.getenv("TEST_VAR") == "test_value"
        assert os.getenv("ANOTHER_VAR") == "another_value"

    def test_load_nonexistent_file_returns_empty(self, tmp_path):
        """Test loading nonexistent file returns empty dict."""
        env_file = tmp_path / "nonexistent.env"
        source = DotenvFileSource(env_file, override=False)

        loaded = source.load()
        assert loaded == {}

    def test_load_with_override_true(self, tmp_path):
        """Test loading with override=True."""
        # Set existing value
        os.environ["OVERRIDE_TEST"] = "old_value"

        env_file = tmp_path / ".env"
        env_file.write_text("OVERRIDE_TEST=new_value\n")

        source = DotenvFileSource(env_file, override=True)
        source.load()

        # Should be overridden
        assert os.getenv("OVERRIDE_TEST") == "new_value"

    def test_load_with_override_false(self, tmp_path):
        """Test loading with override=False (default)."""
        # Set existing value
        os.environ["NO_OVERRIDE_TEST"] = "old_value"

        env_file = tmp_path / ".env"
        env_file.write_text("NO_OVERRIDE_TEST=new_value\n")

        source = DotenvFileSource(env_file, override=False)
        source.load()

        # Should NOT be overridden
        assert os.getenv("NO_OVERRIDE_TEST") == "old_value"

    def test_load_empty_file(self, tmp_path):
        """Test loading empty .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        source = DotenvFileSource(env_file, override=False)
        loaded = source.load()

        assert loaded == {}

    def test_load_file_with_comments(self, tmp_path):
        """Test loading file with comments and blank lines."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
# This is a comment
TEST_VAR=value1

# Another comment
ANOTHER_VAR=value2

"""
        )

        source = DotenvFileSource(env_file, override=False)
        loaded = source.load()

        assert len(loaded) == 2
        assert loaded["TEST_VAR"] == "value1"
        assert loaded["ANOTHER_VAR"] == "value2"

    def test_load_file_with_quoted_values(self, tmp_path):
        """Test loading file with quoted values."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SINGLE_QUOTED='value with spaces'\n"
            'DOUBLE_QUOTED="value with spaces"\n'
            "UNQUOTED=value_without_spaces\n"
        )

        source = DotenvFileSource(env_file, override=False)
        loaded = source.load()

        assert loaded["SINGLE_QUOTED"] == "value with spaces"
        assert loaded["DOUBLE_QUOTED"] == "value with spaces"
        assert loaded["UNQUOTED"] == "value_without_spaces"

    def test_load_file_with_equals_in_value(self, tmp_path):
        """Test loading file with equals sign in value."""
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://user:pass@host:5432/db?param=value\n")

        source = DotenvFileSource(env_file, override=False)
        loaded = source.load()

        # Should handle multiple = signs correctly
        assert "DATABASE_URL" in loaded


class TestEnvFileLoader:
    """Test suite for EnvFileLoader."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        # Store original state
        original_env = os.environ.copy()
        yield
        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)

    def test_load_single_source(self, tmp_path):
        """Test loading single source."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\n")

        source = DotenvFileSource(env_file, override=False)
        loader = EnvFileLoader([source], strict=False)

        loader.load_all()

        assert os.getenv("VAR1") == "value1"
        assert len(loader.get_loaded_files()) == 1
        assert loader.get_loaded_files()[0] == env_file

    def test_load_multiple_sources_no_override(self, tmp_path):
        """Test loading multiple sources without override."""
        env_file1 = tmp_path / ".env.base"
        env_file1.write_text("VAR1=base_value\nVAR2=base_value2\n")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("VAR1=local_value\n")

        sources = [
            DotenvFileSource(env_file1, override=False),
            DotenvFileSource(env_file2, override=False),
        ]
        loader = EnvFileLoader(sources, strict=False)

        loader.load_all()

        # First source loads VAR1=base_value
        # Second source tries to load VAR1=local_value but override=False
        # So VAR1 should still be base_value
        assert os.getenv("VAR1") == "base_value"
        assert os.getenv("VAR2") == "base_value2"
        assert len(loader.get_loaded_files()) == 2

    def test_load_multiple_sources_with_override(self, tmp_path):
        """Test loading multiple sources with override."""
        env_file1 = tmp_path / ".env.base"
        env_file1.write_text("VAR1=base_value\nVAR2=base_value2\n")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("VAR1=local_value\n")

        sources = [
            DotenvFileSource(env_file1, override=False),
            DotenvFileSource(env_file2, override=True),  # Override enabled
        ]
        loader = EnvFileLoader(sources, strict=False)

        loader.load_all()

        # Second source should override VAR1
        assert os.getenv("VAR1") == "local_value"
        assert os.getenv("VAR2") == "base_value2"

    def test_strict_mode_missing_file_raises(self, tmp_path):
        """Test strict mode raises error for missing file."""
        nonexistent = tmp_path / "nonexistent.env"
        source = DotenvFileSource(nonexistent, override=False)
        loader = EnvFileLoader([source], strict=True)

        with pytest.raises(EnvFileNotFoundError) as exc_info:
            loader.load_all()

        assert str(nonexistent) in str(exc_info.value)

    def test_non_strict_mode_missing_file_continues(self, tmp_path):
        """Test non-strict mode continues when file missing."""
        nonexistent = tmp_path / "nonexistent.env"
        existing = tmp_path / ".env"
        existing.write_text("VAR1=value1\n")

        sources = [
            DotenvFileSource(nonexistent, override=False),
            DotenvFileSource(existing, override=False),
        ]
        loader = EnvFileLoader(sources, strict=False)

        # Should not raise
        loader.load_all()

        # Should load from existing file
        assert os.getenv("VAR1") == "value1"
        # Only existing file should be in loaded list
        assert len(loader.get_loaded_files()) == 1
        assert loader.get_loaded_files()[0] == existing

    def test_get_loaded_files_returns_copy(self, tmp_path):
        """Test get_loaded_files returns immutable copy."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\n")

        source = DotenvFileSource(env_file, override=False)
        loader = EnvFileLoader([source], strict=False)
        loader.load_all()

        # Get list
        files1 = loader.get_loaded_files()
        assert len(files1) == 1

        # Modify list (should not affect loader)
        files1.append(Path("/fake/path"))

        # Get fresh list
        files2 = loader.get_loaded_files()
        assert len(files2) == 1  # Should still be 1

    def test_empty_sources_list(self):
        """Test loader with empty sources list."""
        loader = EnvFileLoader([], strict=False)
        loader.load_all()  # Should not raise

        assert len(loader.get_loaded_files()) == 0

    def test_mixed_source_types(self, tmp_path):
        """Test loader with mixed source types."""
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_VAR=from_file\n")

        sources = [
            MockEnvSource({"MOCK_VAR": "from_mock"}),
            DotenvFileSource(env_file, override=False),
        ]
        loader = EnvFileLoader(sources, strict=False)

        loader.load_all()

        assert os.getenv("MOCK_VAR") == "from_mock"
        assert os.getenv("FILE_VAR") == "from_file"

        # Only file source should be in loaded files
        assert len(loader.get_loaded_files()) == 1

    def test_load_order_matters(self, tmp_path):
        """Test that source loading order matters."""
        # Clear any existing value
        os.environ.pop("ORDER_TEST", None)

        file1 = tmp_path / ".env1"
        file1.write_text("ORDER_TEST=first\n")

        file2 = tmp_path / ".env2"
        file2.write_text("ORDER_TEST=second\n")

        # Load in different orders
        sources1 = [
            DotenvFileSource(file1, override=False),
            DotenvFileSource(file2, override=True),
        ]
        loader1 = EnvFileLoader(sources1, strict=False)
        loader1.load_all()
        assert os.getenv("ORDER_TEST") == "second"

        # Reverse order
        os.environ.pop("ORDER_TEST", None)
        sources2 = [
            DotenvFileSource(file2, override=False),
            DotenvFileSource(file1, override=True),
        ]
        loader2 = EnvFileLoader(sources2, strict=False)
        loader2.load_all()
        assert os.getenv("ORDER_TEST") == "first"
