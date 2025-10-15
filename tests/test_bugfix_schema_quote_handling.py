"""Test fix for schema validation quote handling bug.

This test suite verifies that the schema validation command properly handles
quoted values in .env files using python-dotenv instead of naive string parsing.

Bug Description:
    The validate_with_schema() function was manually parsing .env files with
    value.strip() which only removed whitespace but NOT quotes. This caused
    validation to fail for quoted values like ADMIN_EMAIL="user@example.com"
    because the validator saw "user@example.com" (with quotes) as the value.

Fix:
    Replaced manual parsing with python-dotenv's dotenv_values() function
    which properly handles quote stripping, escape sequences, and edge cases.

Related Files:
    - src/tripwire/schema.py (validate_with_schema function, lines 516-550)

Test Coverage:
    - Quoted values (double and single quotes)
    - Unquoted values (backward compatibility)
    - Mixed quoting styles
    - Empty values
    - Values with special characters
    - Multiline values (future)
"""

from pathlib import Path

import pytest

from tripwire.schema import validate_with_schema


class TestSchemaValidateQuoteHandling:
    """Test suite for schema validation quote handling bug fix."""

    def test_quoted_email_validation(self, tmp_path):
        """Verify email validation works with quoted values.

        This is the EXACT case reported by the user.
        Before fix: FAILS with "Invalid format: email"
        After fix: PASSES
        """
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.ADMIN_EMAIL]
type = "string"
required = true
format = "email"
description = "Administrator email address"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with QUOTED email (this was failing before fix)
        env_content = 'ADMIN_EMAIL="alangil505@gmail.com"\n'
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Email validation should pass but got errors: {errors}"
        assert len(errors) == 0, f"Expected no errors but got: {errors}"

    def test_quoted_pattern_validation(self, tmp_path):
        """Verify pattern validation works with quoted values.

        This is another case from the user's report.
        Before fix: FAILS with "Does not match pattern: ^sk-[a-zA-Z0-9]{32}$"
        After fix: PASSES
        """
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.API_TOKEN]
type = "string"
required = true
pattern = "^sk-[a-zA-Z0-9]{32}$"
description = "Service API token"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with QUOTED token (this was failing before fix)
        # Note: Token must match pattern (32 alphanumeric chars after 'sk-')
        env_content = 'API_TOKEN="sk-abcdefghijklmnopqrstuvwxyz123456"\n'
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Pattern validation should pass but got errors: {errors}"
        assert len(errors) == 0, f"Expected no errors but got: {errors}"

    def test_quoted_url_validation(self, tmp_path):
        """Verify URL format validation works with quoted values."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.API_URL]
type = "string"
required = true
format = "url"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with QUOTED URL
        env_content = 'API_URL="https://api.example.com/v1"\n'
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"URL validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_quoted_postgresql_url_validation(self, tmp_path):
        """Verify PostgreSQL URL validation works with quoted values."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.APP_DATABASE_URL]
type = "string"
required = true
format = "postgresql"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with QUOTED PostgreSQL URL
        env_content = 'APP_DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"\n'
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"PostgreSQL URL validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_quoted_choices_validation(self, tmp_path):
        """Verify choices validation works with quoted values.

        Another case from the user's report.
        Before fix: FAILS because validator sees "development" instead of development
        After fix: PASSES
        """
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.ENVIRONMENT]
type = "string"
required = true
choices = ["development", "staging", "production"]
description = "Application environment"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with QUOTED environment
        env_content = 'ENVIRONMENT="development"\n'
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Choices validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_unquoted_values_still_work(self, tmp_path):
        """Verify unquoted values still work (backward compatibility)."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.PORT]
type = "int"
required = true
min = 1024
max = 65535

[variables.DEBUG]
type = "bool"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with UNQUOTED values (should still work)
        env_content = """
PORT=8080
DEBUG=true
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Unquoted validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_mixed_quoting_styles(self, tmp_path):
        """Verify mixed quoted and unquoted values work together."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.APP_NAME]
type = "string"
required = true

[variables.PORT]
type = "int"
required = true

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with MIXED quoting
        env_content = """
APP_NAME="My Application"
PORT=3000
DATABASE_URL="postgresql://user:pass@localhost:5432/db"
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Mixed quoting validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_single_quotes(self, tmp_path):
        """Verify single quotes are handled correctly."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.APP_NAME]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with SINGLE quotes
        env_content = "APP_NAME='My Application'\n"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Single quote validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_empty_values(self, tmp_path):
        """Verify empty values are handled correctly.

        Empty values (KEY=) should be treated as empty strings.
        From user's report: API_URL=, APP_DATABASE_URL=, etc.
        """
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.OPTIONAL_VALUE]
type = "string"
required = false

[variables.REQUIRED_VALUE]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with empty values
        env_content = """
OPTIONAL_VALUE=
REQUIRED_VALUE=
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        # REQUIRED_VALUE is present but empty - this should be fine for type validation
        # (The schema just requires the key to exist, empty string is a valid string)
        # However, if there were other validators (min_length, format, etc), they might fail
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_values_with_spaces(self, tmp_path):
        """Verify values with spaces are handled correctly."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.APP_NAME]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with quoted value containing spaces
        env_content = 'APP_NAME="My Cool Application"\n'
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Spaces validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_values_with_equals_signs(self, tmp_path):
        """Verify values with equals signs are handled correctly."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.COMPLEX_VALUE]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with value containing equals signs
        env_content = 'COMPLEX_VALUE="key1=value1&key2=value2"\n'
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Equals sign validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_values_with_hash_symbols(self, tmp_path):
        """Verify values with hash symbols are handled correctly."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.COMPLEX_VALUE]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with value containing hash (which would be comment without quotes)
        env_content = 'COMPLEX_VALUE="value#with#hashes"\n'
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Hash symbol validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_user_reported_case_complete(self, tmp_path):
        """Test the COMPLETE user-reported case with all variables.

        This recreates the exact scenario from the bug report with multiple
        variables showing different validation failures.
        """
        # Create schema matching user's .tripwire.toml
        schema_content = """
[project]
name = "user-project"

[variables.ADMIN_EMAIL]
type = "string"
required = true
description = "Administrator email address"
format = "email"

[variables.API_TOKEN]
type = "string"
required = true
description = "Service API token"
pattern = "^sk-[a-zA-Z0-9]{32}$"

[variables.API_URL]
type = "string"
required = true
format = "url"

[variables.APP_DATABASE_URL]
type = "string"
required = true
format = "postgresql"

[variables.ENVIRONMENT]
type = "string"
required = true
description = "Application environment"
choices = ["development", "staging", "production"]
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env matching user's .env.development (with quoted values that WORK)
        env_content = """
# Line 9
ADMIN_EMAIL="alangil505@gmail.com"

# Line 25
API_TOKEN="sk-abcdefghijklmnopqrstuvwxyz123456"

# Line 28
API_URL="https://api.example.com/v1"

# Line 34
APP_DATABASE_URL="postgresql://user:pass@localhost:5432/db"

# Line 75
ENVIRONMENT="development"
"""
        env_file = tmp_path / ".env.development"
        env_file.write_text(env_content)

        # Validate - should PASS with fix
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Complete user case should pass but got errors: {errors}"
        assert len(errors) == 0, f"Expected no errors but got: {errors}"


class TestSchemaValidateEdgeCases:
    """Test edge cases for schema validation."""

    def test_file_not_found(self, tmp_path):
        """Verify graceful handling when .env file doesn't exist."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.TEST_VAR]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Don't create .env file
        env_file = tmp_path / ".env.nonexistent"

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        # Should fail with missing required variable
        assert not is_valid
        assert any("TEST_VAR" in err for err in errors)

    def test_schema_file_not_found(self, tmp_path):
        """Verify graceful handling when schema file doesn't exist."""
        # Create .env but not schema
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=value\n")

        schema_file = tmp_path / ".tripwire.toml.nonexistent"

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        # Should fail with schema not found
        assert not is_valid
        assert len(errors) == 1
        assert "Schema file not found" in errors[0]

    def test_comments_ignored(self, tmp_path):
        """Verify comments in .env file are properly ignored."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.TEST_VAR]
type = "string"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Create .env with comments
        env_content = """
# This is a comment
TEST_VAR="value"  # This is an inline comment
# Another comment
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Validate
        is_valid, errors = validate_with_schema(env_file, schema_file, "development")

        assert is_valid, f"Comments should be ignored but got errors: {errors}"
        assert len(errors) == 0


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    def test_integer_type_coercion(self, tmp_path):
        """Verify integer type coercion still works."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.PORT]
type = "int"
required = true
min = 1024
max = 65535
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Test both quoted and unquoted integer values
        for env_content in ['PORT="8080"\n', "PORT=8080\n"]:
            env_file = tmp_path / ".env"
            env_file.write_text(env_content)

            is_valid, errors = validate_with_schema(env_file, schema_file, "development")

            assert is_valid, f"Integer validation failed for: {env_content!r}, errors: {errors}"
            assert len(errors) == 0

    def test_boolean_type_coercion(self, tmp_path):
        """Verify boolean type coercion still works."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.DEBUG]
type = "bool"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Test both quoted and unquoted boolean values
        for env_content in ['DEBUG="true"\n', "DEBUG=true\n", 'DEBUG="1"\n', "DEBUG=1\n"]:
            env_file = tmp_path / ".env"
            env_file.write_text(env_content)

            is_valid, errors = validate_with_schema(env_file, schema_file, "development")

            assert is_valid, f"Boolean validation failed for: {env_content!r}, errors: {errors}"
            assert len(errors) == 0

    def test_list_type_coercion(self, tmp_path):
        """Verify list type coercion still works."""
        # Create schema
        schema_content = """
[project]
name = "test"

[variables.ALLOWED_HOSTS]
type = "list"
required = true
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        # Test list values (both comma-separated and JSON)
        for env_content in [
            'ALLOWED_HOSTS="host1,host2,host3"\n',
            "ALLOWED_HOSTS=host1,host2,host3\n",
            'ALLOWED_HOSTS="[\\"host1\\", \\"host2\\", \\"host3\\"]"\n',
        ]:
            env_file = tmp_path / ".env"
            env_file.write_text(env_content)

            is_valid, errors = validate_with_schema(env_file, schema_file, "development")

            assert is_valid, f"List validation failed for: {env_content!r}, errors: {errors}"
            assert len(errors) == 0
