"""Tests for the .env file parser module."""

import tempfile
from pathlib import Path

import pytest

from tripwire.parser import (
    EnvFileParser,
    compare_env_files,
    format_env_file,
    merge_env_files,
    needs_quoting,
    parse_env_file,
)


def test_parse_simple_key_value():
    """Test parsing simple key=value pairs."""
    content = """
API_KEY=my-secret-key
DEBUG=true
PORT=8000
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert len(entries) == 3
    assert entries["API_KEY"].value == "my-secret-key"
    assert entries["DEBUG"].value == "true"
    assert entries["PORT"].value == "8000"


def test_parse_with_quotes():
    """Test parsing values with quotes."""
    content = """
SINGLE_QUOTED='hello world'
DOUBLE_QUOTED="hello world"
WITH_SPACES="value with spaces"
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert entries["SINGLE_QUOTED"].value == "hello world"
    assert entries["DOUBLE_QUOTED"].value == "hello world"
    assert entries["WITH_SPACES"].value == "value with spaces"


def test_parse_with_comments():
    """Test parsing with comments."""
    content = """
# This is a comment
API_KEY=secret

# Another comment
DEBUG=true  # inline comment
"""
    parser = EnvFileParser(preserve_comments=True)
    entries = parser.parse_string(content)

    assert len(entries) == 2
    assert entries["API_KEY"].comment == "This is a comment"
    assert entries["API_KEY"].value == "secret"
    assert entries["DEBUG"].comment == "Another comment"


def test_parse_empty_values():
    """Test parsing empty values."""
    content = """
EMPTY_VAR=
QUOTED_EMPTY=""
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert entries["EMPTY_VAR"].value == ""
    assert entries["QUOTED_EMPTY"].value == ""


def test_parse_with_escapes():
    """Test parsing values with escape sequences."""
    content = r"""
NEWLINE="line1\nline2"
TAB="col1\tcol2"
QUOTE="He said \"hello\""
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert entries["NEWLINE"].value == "line1\nline2"
    assert entries["TAB"].value == "col1\tcol2"
    assert entries["QUOTE"].value == 'He said "hello"'


def test_parse_multiline_behavior():
    """Test that each line is parsed independently."""
    content = """
VAR1=value1
VAR2=value2
VAR3=value3
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert len(entries) == 3
    assert all(key in entries for key in ["VAR1", "VAR2", "VAR3"])


def test_parse_invalid_keys():
    """Test that invalid variable names are skipped."""
    content = """
VALID_KEY=value
123_INVALID=value
with-dash=value
VALID_KEY_2=value2
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    # Only valid keys should be parsed
    assert "VALID_KEY" in entries
    assert "VALID_KEY_2" in entries
    assert "123_INVALID" not in entries
    assert "with-dash" not in entries


def test_parse_file():
    """Test parsing from a file."""
    content = """
API_KEY=secret
DEBUG=true
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(content)
        f.flush()
        temp_path = Path(f.name)

    try:
        parser = EnvFileParser()
        entries = parser.parse_file(temp_path)

        assert len(entries) == 2
        assert entries["API_KEY"].value == "secret"
        assert entries["DEBUG"].value == "true"
    finally:
        temp_path.unlink()


def test_parse_file_not_found():
    """Test parsing a non-existent file raises error."""
    parser = EnvFileParser()

    with pytest.raises(FileNotFoundError):
        parser.parse_file(Path("/nonexistent/file.env"))


def test_parse_env_file_convenience():
    """Test the convenience function parse_env_file."""
    content = """
KEY1=value1
KEY2=value2
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(content)
        f.flush()
        temp_path = Path(f.name)

    try:
        result = parse_env_file(temp_path)

        assert isinstance(result, dict)
        assert result == {"KEY1": "value1", "KEY2": "value2"}
    finally:
        temp_path.unlink()


def test_compare_env_files():
    """Test comparing two env files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create .env file
        env_file = tmppath / ".env"
        env_file.write_text(
            """
VAR1=value1
VAR2=value2
EXTRA=extra_value
"""
        )

        # Create .env.example file
        example_file = tmppath / ".env.example"
        example_file.write_text(
            """
VAR1=
VAR2=
VAR3=
"""
        )

        missing, extra, common = compare_env_files(env_file, example_file)

        assert missing == ["VAR3"]  # In example but not in env
        assert extra == ["EXTRA"]  # In env but not in example
        assert common == ["VAR1", "VAR2"]  # In both


def test_compare_env_files_missing_env():
    """Test comparing when .env doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Only create .env.example
        example_file = tmppath / ".env.example"
        example_file.write_text("VAR1=\nVAR2=")

        env_file = tmppath / ".env"  # Doesn't exist

        missing, extra, common = compare_env_files(env_file, example_file)

        assert missing == ["VAR1", "VAR2"]
        assert extra == []
        assert common == []


def test_needs_quoting():
    """Test the needs_quoting function."""
    assert needs_quoting("simple") is False
    assert needs_quoting("123") is False
    assert needs_quoting("") is False

    assert needs_quoting("value with spaces") is True
    assert needs_quoting('value"quote') is True
    assert needs_quoting("value'quote") is True
    assert needs_quoting("value#hash") is True
    assert needs_quoting("value\nwith\nnewline") is True


def test_format_env_file():
    """Test formatting entries back to .env format."""
    from tripwire.parser import EnvEntry

    entries = {
        "API_KEY": EnvEntry(
            key="API_KEY",
            value="secret123",
            comment="API Key for service",
            line_number=1,
        ),
        "DEBUG": EnvEntry(
            key="DEBUG",
            value="true",
            comment=None,
            line_number=2,
        ),
    }

    output = format_env_file(entries, include_comments=True)

    assert "# API Key for service" in output
    assert "API_KEY=secret123" in output
    assert "DEBUG=true" in output


def test_format_env_file_with_special_chars():
    """Test formatting values that need quoting."""
    from tripwire.parser import EnvEntry

    entries = {
        "VALUE": EnvEntry(
            key="VALUE",
            value="value with spaces",
            comment=None,
            line_number=1,
        ),
    }

    output = format_env_file(entries, include_comments=False)

    assert 'VALUE="value with spaces"' in output


def test_merge_env_files():
    """Test merging new variables into existing .env file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create existing .env
        env_file = tmppath / ".env"
        env_file.write_text(
            """
EXISTING_VAR=existing_value
"""
        )

        # Merge new variables
        new_vars = {
            "NEW_VAR1": "new_value1",
            "NEW_VAR2": "new_value2",
        }

        merged = merge_env_files(env_file, new_vars, preserve_existing=True)

        assert "EXISTING_VAR=existing_value" in merged
        assert "NEW_VAR1=new_value1" in merged
        assert "NEW_VAR2=new_value2" in merged


def test_merge_env_files_preserve_existing():
    """Test that merging preserves existing values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        env_file = tmppath / ".env"
        env_file.write_text("VAR1=original_value\n")

        new_vars = {"VAR1": "new_value"}

        # With preserve_existing=True
        merged = merge_env_files(env_file, new_vars, preserve_existing=True)
        assert "VAR1=original_value" in merged
        assert "VAR1=new_value" not in merged


def test_merge_env_files_no_preserve():
    """Test that merging can override existing values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        env_file = tmppath / ".env"
        env_file.write_text("VAR1=original_value\n")

        new_vars = {"VAR1": "new_value"}

        # With preserve_existing=False
        merged = merge_env_files(env_file, new_vars, preserve_existing=False)
        assert "VAR1=new_value" in merged


def test_merge_env_files_nonexistent():
    """Test merging into a non-existent .env file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        env_file = tmppath / ".env"  # Doesn't exist

        new_vars = {"VAR1": "value1", "VAR2": "value2"}

        merged = merge_env_files(env_file, new_vars)

        assert "VAR1=value1" in merged
        assert "VAR2=value2" in merged


def test_parse_inline_comments():
    """Test handling inline comments."""
    content = """
VAR1=value1  # This is a comment
VAR2="value with # hash"  # But this is a comment
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    assert entries["VAR1"].value == "value1"
    assert entries["VAR2"].value == "value with # hash"


def test_parse_equals_in_value():
    """Test parsing values that contain equals signs."""
    content = """
CONNECTION_STRING=Server=localhost;User=admin
"""
    parser = EnvFileParser()
    entries = parser.parse_string(content)

    # Should split on FIRST equals only
    assert entries["CONNECTION_STRING"].value == "Server=localhost;User=admin"
