"""Tests for environment variable interpolation."""

import os
from pathlib import Path

import pytest

from tripwire.parser import EnvFileParser, expand_variables


class TestExpandVariables:
    """Test the expand_variables function."""

    def test_expand_braced_variable(self):
        """Test ${VAR} syntax expansion."""
        env_dict = {"HOST": "localhost", "PORT": "5432"}
        result = expand_variables("${HOST}:${PORT}", env_dict, allow_os_environ=False)
        assert result == "localhost:5432"

    def test_expand_unbraced_variable(self):
        """Test $VAR syntax expansion."""
        env_dict = {"USER": "admin", "DOMAIN": "example.com"}
        result = expand_variables("$USER@$DOMAIN", env_dict, allow_os_environ=False)
        assert result == "admin@example.com"

    def test_expand_mixed_syntax(self):
        """Test mixed ${VAR} and $VAR syntax."""
        env_dict = {"BASE": "/app", "ENV": "prod"}
        result = expand_variables("${BASE}/data-$ENV", env_dict, allow_os_environ=False)
        assert result == "/app/data-prod"

    def test_expand_with_text(self):
        """Test expansion with surrounding text."""
        env_dict = {"DB_HOST": "postgres"}
        result = expand_variables("postgresql://${DB_HOST}:5432/mydb", env_dict, allow_os_environ=False)
        assert result == "postgresql://postgres:5432/mydb"

    def test_expand_undefined_variable_keeps_reference(self):
        """Test that undefined variables are kept as-is."""
        env_dict = {"HOST": "localhost"}
        result = expand_variables("${HOST}:${UNDEFINED}", env_dict, allow_os_environ=False)
        assert result == "localhost:${UNDEFINED}"

    def test_expand_from_os_environ(self):
        """Test fallback to os.environ."""
        os.environ["TEST_VAR_123"] = "from_os"
        env_dict = {"HOST": "localhost"}
        result = expand_variables("${HOST}:${TEST_VAR_123}", env_dict, allow_os_environ=True)
        assert result == "localhost:from_os"
        del os.environ["TEST_VAR_123"]

    def test_expand_prefers_env_dict_over_os_environ(self):
        """Test that env_dict takes precedence over os.environ."""
        os.environ["TEST_VAR_456"] = "from_os"
        env_dict = {"TEST_VAR_456": "from_dict"}
        result = expand_variables("${TEST_VAR_456}", env_dict, allow_os_environ=True)
        assert result == "from_dict"
        del os.environ["TEST_VAR_456"]

    def test_expand_with_os_environ_disabled(self):
        """Test that os.environ is not used when disabled."""
        os.environ["TEST_VAR_789"] = "from_os"
        env_dict = {}
        result = expand_variables("${TEST_VAR_789}", env_dict, allow_os_environ=False)
        assert result == "${TEST_VAR_789}"
        del os.environ["TEST_VAR_789"]

    def test_expand_empty_string(self):
        """Test expansion with empty string."""
        result = expand_variables("", {}, allow_os_environ=False)
        assert result == ""

    def test_expand_no_variables(self):
        """Test string with no variables."""
        result = expand_variables("plain text", {}, allow_os_environ=False)
        assert result == "plain text"

    def test_expand_multiple_occurrences(self):
        """Test same variable referenced multiple times."""
        env_dict = {"VAR": "value"}
        result = expand_variables("$VAR and ${VAR} and $VAR", env_dict, allow_os_environ=False)
        assert result == "value and value and value"

    def test_expand_nested_like_syntax(self):
        """Test nested-like syntax (recursive expansion)."""
        env_dict = {"INNER": "value", "OUTER": "prefix_${INNER}"}
        result = expand_variables("${OUTER}", env_dict, allow_os_environ=False)
        # Should recursively expand OUTER which contains ${INNER}
        assert result == "prefix_value"

    def test_expand_invalid_variable_names(self):
        """Test that invalid variable names are not expanded."""
        env_dict = {}
        # Variables must start with letter or underscore
        assert expand_variables("${123VAR}", env_dict, False) == "${123VAR}"
        # Must be alphanumeric + underscore
        assert expand_variables("${VAR-NAME}", env_dict, False) == "${VAR-NAME}"

    def test_expand_with_underscores(self):
        """Test variable names with underscores."""
        env_dict = {"MY_VAR_NAME": "value", "_PRIVATE": "secret"}
        result = expand_variables("${MY_VAR_NAME}:${_PRIVATE}", env_dict, False)
        assert result == "value:secret"

    def test_expand_with_numbers(self):
        """Test variable names with numbers (but not starting with)."""
        env_dict = {"VAR1": "one", "VAR2": "two"}
        result = expand_variables("${VAR1}-${VAR2}", env_dict, False)
        assert result == "one-two"

    def test_expand_case_sensitive(self):
        """Test that variable names are case-sensitive."""
        env_dict = {"var": "lower", "VAR": "upper"}
        assert expand_variables("$var", env_dict, False) == "lower"
        assert expand_variables("$VAR", env_dict, False) == "upper"


class TestEnvFileParserInterpolation:
    """Test EnvFileParser with variable interpolation."""

    def test_parse_with_interpolation_enabled(self, tmp_path):
        """Test parsing with interpolation enabled."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
HOST=localhost
PORT=5432
DATABASE_URL=postgresql://${HOST}:${PORT}/mydb
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["HOST"].value == "localhost"
        assert entries["PORT"].value == "5432"
        assert entries["DATABASE_URL"].value == "postgresql://localhost:5432/mydb"

    def test_parse_with_interpolation_disabled(self, tmp_path):
        """Test parsing with interpolation disabled."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
HOST=localhost
DATABASE_URL=postgresql://${HOST}:5432/mydb
"""
        )

        parser = EnvFileParser(expand_vars=False)
        entries = parser.parse_file(env_file)

        assert entries["DATABASE_URL"].value == "postgresql://${HOST}:5432/mydb"

    def test_parse_chained_interpolation(self, tmp_path):
        """Test chained variable references."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
BASE_DIR=/app
DATA_DIR=${BASE_DIR}/data
LOG_DIR=${BASE_DIR}/logs
CACHE_DIR=${DATA_DIR}/cache
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["BASE_DIR"].value == "/app"
        assert entries["DATA_DIR"].value == "/app/data"
        assert entries["LOG_DIR"].value == "/app/logs"
        # CACHE_DIR references DATA_DIR which is already expanded
        assert entries["CACHE_DIR"].value == "/app/data/cache"

    def test_parse_interpolation_with_quotes(self, tmp_path):
        """Test interpolation within quoted values."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
USER=admin
MESSAGE="Hello ${USER}!"
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["MESSAGE"].value == "Hello admin!"

    def test_parse_interpolation_order_independent(self, tmp_path):
        """Test that order of variable definitions doesn't matter."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
# Reference before definition
FULL_URL=${PROTOCOL}://${HOST}:${PORT}
PROTOCOL=https
HOST=api.example.com
PORT=443
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["FULL_URL"].value == "https://api.example.com:443"

    def test_parse_interpolation_with_os_environ(self, tmp_path):
        """Test interpolation with os.environ fallback."""
        os.environ["TEST_HOME"] = "/home/test"

        env_file = tmp_path / ".env"
        env_file.write_text("CONFIG_PATH=${TEST_HOME}/.config")

        parser = EnvFileParser(expand_vars=True, allow_os_environ=True)
        entries = parser.parse_file(env_file)

        assert entries["CONFIG_PATH"].value == "/home/test/.config"

        del os.environ["TEST_HOME"]

    def test_parse_undefined_variable_preserved(self, tmp_path):
        """Test that undefined variables are preserved in output."""
        env_file = tmp_path / ".env"
        env_file.write_text("PATH=${UNDEFINED_VAR}/bin")

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["PATH"].value == "${UNDEFINED_VAR}/bin"

    def test_parse_complex_interpolation_scenario(self, tmp_path):
        """Test complex real-world interpolation scenario."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
# Database configuration
DB_USER=postgres
DB_PASS=secret123
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp

# Derived values
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DATABASE_URL_READ_ONLY=postgresql://${DB_USER}_readonly:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis configuration
REDIS_HOST=redis-server
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}

# Application paths
APP_ROOT=/opt/myapp
APP_DATA=${APP_ROOT}/data
APP_LOGS=${APP_ROOT}/logs
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["DATABASE_URL"].value == "postgresql://postgres:secret123@localhost:5432/myapp"
        assert (
            entries["DATABASE_URL_READ_ONLY"].value == "postgresql://postgres_readonly:secret123@localhost:5432/myapp"
        )
        assert entries["REDIS_URL"].value == "redis://redis-server:6379"
        assert entries["APP_DATA"].value == "/opt/myapp/data"
        assert entries["APP_LOGS"].value == "/opt/myapp/logs"

    def test_parse_interpolation_with_special_chars(self, tmp_path):
        """Test interpolation with special characters in values."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
SPECIAL_CHARS="!@#$%"
MESSAGE="Value: ${SPECIAL_CHARS}"
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["MESSAGE"].value == "Value: !@#$%"

    def test_parse_interpolation_empty_value(self, tmp_path):
        """Test interpolation with empty variable values."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
EMPTY=
RESULT=prefix${EMPTY}suffix
"""
        )

        parser = EnvFileParser(expand_vars=True, allow_os_environ=False)
        entries = parser.parse_file(env_file)

        assert entries["EMPTY"].value == ""
        assert entries["RESULT"].value == "prefixsuffix"
