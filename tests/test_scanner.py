"""Tests for the code scanner module."""

import tempfile
from pathlib import Path

import pytest

from tripwire.scanner import (
    EnvVarInfo,
    deduplicate_variables,
    format_default_value,
    format_var_for_env_example,
    scan_directory,
    scan_file,
)


def test_scan_file_basic_require():
    """Test scanning a file with env.require() call."""
    code = """
from tripwire import env

API_KEY = env.require('API_KEY', description='API key for service')
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)

        assert len(variables) == 1
        assert variables[0].name == "API_KEY"
        assert variables[0].required is True
        assert variables[0].description == "API key for service"
        assert variables[0].var_type == "str"
    finally:
        temp_path.unlink()


def test_scan_file_optional_with_default():
    """Test scanning a file with env.optional() call."""
    code = """
from tripwire import env

DEBUG = env.optional('DEBUG', default=False, type=bool, description='Enable debug mode')
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)

        assert len(variables) == 1
        assert variables[0].name == "DEBUG"
        assert variables[0].required is False
        assert variables[0].default is False
        assert variables[0].var_type == "bool"
        assert variables[0].description == "Enable debug mode"
    finally:
        temp_path.unlink()


def test_scan_file_with_validation():
    """Test scanning a file with validation parameters."""
    code = """
from tripwire import env

EMAIL = env.require(
    'EMAIL',
    format='email',
    description='User email address'
)

PORT = env.require(
    'PORT',
    type=int,
    min_val=1000,
    max_val=9999
)

ENV = env.require(
    'ENV',
    choices=['dev', 'staging', 'prod']
)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)

        assert len(variables) == 3

        # Check EMAIL
        email_var = next(v for v in variables if v.name == "EMAIL")
        assert email_var.format == "email"

        # Check PORT
        port_var = next(v for v in variables if v.name == "PORT")
        assert port_var.var_type == "int"
        assert port_var.min_val == 1000
        assert port_var.max_val == 9999

        # Check ENV
        env_var = next(v for v in variables if v.name == "ENV")
        assert env_var.choices == ["dev", "staging", "prod"]
    finally:
        temp_path.unlink()


def test_scan_file_multiple_variables():
    """Test scanning a file with multiple env calls."""
    code = """
from tripwire import env

API_KEY = env.require('API_KEY')
DEBUG = env.optional('DEBUG', default=False, type=bool)
PORT = env.optional('PORT', default=8000, type=int)
DATABASE_URL = env.require('DATABASE_URL', format='postgresql')
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)

        assert len(variables) == 4

        var_names = {v.name for v in variables}
        assert var_names == {"API_KEY", "DEBUG", "PORT", "DATABASE_URL"}

        required = [v for v in variables if v.required]
        optional = [v for v in variables if not v.required]

        assert len(required) == 2
        assert len(optional) == 2
    finally:
        temp_path.unlink()


def test_scan_directory():
    """Test scanning a directory recursively."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create multiple Python files
        (tmppath / "app.py").write_text(
            """
from tripwire import env
API_KEY = env.require('API_KEY')
"""
        )

        (tmppath / "config.py").write_text(
            """
from tripwire import env
DEBUG = env.optional('DEBUG', default=False, type=bool)
DATABASE_URL = env.require('DATABASE_URL')
"""
        )

        # Create subdirectory
        subdir = tmppath / "utils"
        subdir.mkdir()
        (subdir / "helpers.py").write_text(
            """
from tripwire import env
SECRET_KEY = env.require('SECRET_KEY', secret=True)
"""
        )

        # Scan directory
        variables = scan_directory(tmppath)

        assert len(variables) == 4

        var_names = {v.name for v in variables}
        assert var_names == {"API_KEY", "DEBUG", "DATABASE_URL", "SECRET_KEY"}


def test_scan_directory_exclude_tests():
    """Test that test files in tests/ directory are excluded by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create normal file
        (tmppath / "app.py").write_text(
            """
from tripwire import env
API_KEY = env.require('API_KEY')
"""
        )

        # Create test directory with test file (should be excluded)
        tests_dir = tmppath / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text(
            """
from tripwire import env
TEST_VAR = env.require('TEST_VAR')
"""
        )

        # Create file starting with "test_" in root (should NOT be excluded)
        # Users might have legitimate files like test_app.py, test_server.py
        (tmppath / "test_config.py").write_text(
            """
from tripwire import env
CONFIG_VAR = env.require('CONFIG_VAR')
"""
        )

        # Scan directory
        variables = scan_directory(tmppath)

        # Should find API_KEY and CONFIG_VAR, but NOT TEST_VAR (from tests/ dir)
        assert len(variables) == 2
        var_names = {v.name for v in variables}
        assert var_names == {"API_KEY", "CONFIG_VAR"}
        assert "TEST_VAR" not in var_names


def test_deduplicate_variables():
    """Test variable deduplication."""
    vars_list = [
        EnvVarInfo(
            name="API_KEY",
            required=True,
            var_type="str",
            default=None,
            description="API key",
            format=None,
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
            secret=False,
            file_path=Path("file1.py"),
            line_number=1,
        ),
        EnvVarInfo(
            name="API_KEY",
            required=True,
            var_type="str",
            default=None,
            description="API key duplicate",
            format=None,
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
            secret=False,
            file_path=Path("file2.py"),
            line_number=5,
        ),
        EnvVarInfo(
            name="DEBUG",
            required=False,
            var_type="bool",
            default=False,
            description="Debug mode",
            format=None,
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
            secret=False,
            file_path=Path("file1.py"),
            line_number=2,
        ),
    ]

    unique = deduplicate_variables(vars_list)

    assert len(unique) == 2
    assert "API_KEY" in unique
    assert "DEBUG" in unique
    # Should keep first occurrence
    assert unique["API_KEY"].description == "API key"


def test_format_default_value():
    """Test formatting default values."""
    assert format_default_value(None) == ""
    assert format_default_value(True) == "true"
    assert format_default_value(False) == "false"
    assert format_default_value(42) == "42"
    assert format_default_value("hello") == "hello"
    assert format_default_value(["a", "b"]) == '["a", "b"]'
    assert format_default_value({"key": "value"}) == '{"key": "value"}'


def test_format_var_for_env_example_required():
    """Test formatting a required variable for .env.example."""
    var = EnvVarInfo(
        name="API_KEY",
        required=True,
        var_type="str",
        default=None,
        description="API key for service",
        format="uuid",
        pattern=None,
        choices=None,
        min_val=None,
        max_val=None,
        secret=False,
        file_path=Path("app.py"),
        line_number=1,
    )

    output = format_var_for_env_example(var)

    assert "# API key for service" in output
    assert "# Required | Type: str" in output
    assert "# Format: uuid" in output
    assert "API_KEY=" in output


def test_format_var_for_env_example_optional():
    """Test formatting an optional variable for .env.example."""
    var = EnvVarInfo(
        name="DEBUG",
        required=False,
        var_type="bool",
        default=False,
        description="Enable debug mode",
        format=None,
        pattern=None,
        choices=None,
        min_val=None,
        max_val=None,
        secret=False,
        file_path=Path("app.py"),
        line_number=2,
    )

    output = format_var_for_env_example(var)

    assert "# Enable debug mode" in output
    assert "# Optional | Type: bool" in output
    assert "DEBUG=false" in output


def test_format_var_with_choices():
    """Test formatting a variable with choices."""
    var = EnvVarInfo(
        name="ENV",
        required=True,
        var_type="str",
        default=None,
        description="Environment name",
        format=None,
        pattern=None,
        choices=["dev", "staging", "prod"],
        min_val=None,
        max_val=None,
        secret=False,
        file_path=Path("app.py"),
        line_number=1,
    )

    output = format_var_for_env_example(var)

    assert "# Choices: dev, staging, prod" in output


def test_format_var_with_range():
    """Test formatting a variable with min/max values."""
    var = EnvVarInfo(
        name="PORT",
        required=False,
        var_type="int",
        default=8000,
        description="Server port",
        format=None,
        pattern=None,
        choices=None,
        min_val=1000,
        max_val=9999,
        secret=False,
        file_path=Path("app.py"),
        line_number=1,
    )

    output = format_var_for_env_example(var)

    assert "# Range: min=1000, max=9999" in output
    assert "PORT=8000" in output


def test_scan_file_syntax_error():
    """Test that syntax errors are properly handled."""
    code = """
# Invalid Python syntax
def broken(
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        with pytest.raises(SyntaxError):
            scan_file(temp_path)
    finally:
        temp_path.unlink()


def test_scan_file_no_env_usage():
    """Test scanning a file with no env usage."""
    code = """
# Regular Python file
def hello():
    return "world"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)
        assert len(variables) == 0
    finally:
        temp_path.unlink()


def test_scan_file_all_python_types():
    """Test scanning file with all Python type annotations."""
    code = """
from tripwire import env

STR_VAR = env.require('STR_VAR', type=str)
INT_VAR = env.require('INT_VAR', type=int)
FLOAT_VAR = env.require('FLOAT_VAR', type=float)
BOOL_VAR = env.require('BOOL_VAR', type=bool)
LIST_VAR = env.require('LIST_VAR', type=list)
DICT_VAR = env.require('DICT_VAR', type=dict)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        variables = scan_file(temp_path)

        assert len(variables) == 6

        type_map = {v.name: v.var_type for v in variables}
        assert type_map["STR_VAR"] == "str"
        assert type_map["INT_VAR"] == "int"
        assert type_map["FLOAT_VAR"] == "float"
        assert type_map["BOOL_VAR"] == "bool"
        assert type_map["LIST_VAR"] == "list"
        assert type_map["DICT_VAR"] == "dict"
    finally:
        temp_path.unlink()
