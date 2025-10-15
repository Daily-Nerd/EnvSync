"""Tests for Bug 1 fix: Custom validators in schema validation.

Tests that schema validation correctly recognizes custom validators
registered via register_validator() instead of only accepting builtin validators.
"""

import tempfile
from pathlib import Path

import pytest

from tripwire.validation import (
    clear_custom_validators,
    register_validator,
    unregister_validator,
)


@pytest.fixture(autouse=True)
def cleanup_validators():
    """Clean up custom validators before and after each test."""
    clear_custom_validators()
    yield
    clear_custom_validators()


def test_schema_check_accepts_custom_validators(tmp_path: Path) -> None:
    """Test that schema check accepts custom validators from registry."""
    from click.testing import CliRunner

    from tripwire.cli import main as cli

    # Register custom validators
    def validate_username(value: str) -> bool:
        return len(value) >= 3 and value.isalnum()

    def validate_hex_color(value: str) -> bool:
        import re

        return bool(re.match(r"^#[0-9a-fA-F]{6}$", value))

    register_validator("username", validate_username)
    register_validator("hex_color", validate_hex_color)

    # Create schema with custom validators
    schema_content = """
[project]
name = "test-project"

[variables.ADMIN_USERNAME]
type = "string"
required = true
format = "username"
description = "Admin username"

[variables.BRAND_COLOR]
type = "string"
required = false
format = "hex_color"
description = "Brand color"
"""

    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)

    # Run schema check
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["schema", "check", "--schema-file", str(schema_file)])

    # Should pass validation (custom validators are registered)
    assert result.exit_code == 0
    assert "All format validators exist" in result.output
    assert "2 custom" in result.output  # Shows custom validator count


def test_schema_check_rejects_unregistered_validators(tmp_path: Path) -> None:
    """Test that schema check rejects validators that aren't registered.

    Phase 1 (v0.12.0): Schema check now guides users to use custom: prefix
    instead of asking them to register validators during AST scanning.
    """
    from click.testing import CliRunner

    from tripwire.cli import main as cli

    # Create schema with unregistered validator (no custom: prefix)
    schema_content = """
[project]
name = "test-project"

[variables.PHONE_NUMBER]
type = "string"
required = true
format = "phone_number"  # NOT registered and no custom: prefix
description = "Phone number"
"""

    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)

    # Run schema check
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["schema", "check", "--schema-file", str(schema_file)])

    # Phase 1: Should fail validation and suggest using custom: prefix
    assert result.exit_code == 1
    assert "Unknown format 'phone_number'" in result.output
    assert "Builtin formats:" in result.output
    # Phase 1: Guide users to use custom: prefix instead of register_validator()
    assert "custom:phone_number" in result.output


def test_schema_check_shows_custom_validator_count(tmp_path: Path) -> None:
    """Test that schema check shows count of custom validators."""
    from click.testing import CliRunner

    from tripwire.cli import main as cli

    # Register 3 custom validators
    register_validator("validator1", lambda v: True)
    register_validator("validator2", lambda v: True)
    register_validator("validator3", lambda v: True)

    # Create minimal schema
    schema_content = """
[project]
name = "test-project"

[variables.VAR1]
type = "string"
required = false
"""

    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)

    # Run schema check
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["schema", "check", "--schema-file", str(schema_file)])

    # Should show custom validator count
    assert result.exit_code == 0
    assert "3 custom" in result.output


def test_schema_check_mixed_builtin_and_custom(tmp_path: Path) -> None:
    """Test schema check with mix of builtin and custom validators."""
    from click.testing import CliRunner

    from tripwire.cli import main as cli

    # Register custom validator
    register_validator("zipcode", lambda v: len(v) == 5 and v.isdigit())

    # Create schema with both builtin and custom validators
    schema_content = """
[project]
name = "test-project"

[variables.USER_EMAIL]
type = "string"
format = "email"  # builtin

[variables.API_URL]
type = "string"
format = "url"  # builtin

[variables.ZIP_CODE]
type = "string"
format = "zipcode"  # custom
"""

    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)

    # Run schema check
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["schema", "check", "--schema-file", str(schema_file)])

    # Should pass validation
    assert result.exit_code == 0
    assert "All format validators exist" in result.output
    assert "1 custom" in result.output


def test_schema_from_code_with_custom_validators(tmp_path: Path) -> None:
    """Test that schema from-code works with custom validators in source.

    Phase 1 (v0.12.0): Schema from-code now emits custom: prefix for
    non-builtin validators to enable deferred validation.
    """
    import os

    from click.testing import CliRunner

    from tripwire.cli import main as cli

    # Register custom validators
    register_validator("ssn", lambda v: len(v) == 11)
    register_validator("credit_card", lambda v: len(v) == 16)

    # Create Python file using custom validators
    source_code = """
from tripwire import env
from tripwire.validation import register_validator

# Register custom validators
register_validator("ssn", lambda v: len(v) == 11)
register_validator("credit_card", lambda v: len(v) == 16)

# Use custom validators
SSN: str = env.require("SSN", format="ssn", description="Social security number", secret=True)
CARD: str = env.require("CARD", format="credit_card", description="Credit card", secret=True)
"""

    source_file = tmp_path / "app.py"
    source_file.write_text(source_code)

    # Run schema from-code
    runner = CliRunner()
    os.chdir(tmp_path)
    result = runner.invoke(cli, ["schema", "from-code", "--force"])

    # Schema should be generated
    assert result.exit_code == 0

    # Phase 1: Verify generated schema has custom: prefix for custom validators
    schema_file = tmp_path / ".tripwire.toml"
    assert schema_file.exists()
    schema_content = schema_file.read_text()
    assert 'format = "custom:ssn"' in schema_content
    assert 'format = "custom:credit_card"' in schema_content


def test_custom_validator_thread_safety_in_schema_check(tmp_path: Path) -> None:
    """Test that validator registry is thread-safe when used in schema validation."""
    import concurrent.futures

    from tripwire.validation import list_validators

    # Register custom validator
    register_validator("test_format", lambda v: True)

    # Test thread-safe access to validator registry
    def get_validators():
        # This simulates what schema check does internally
        validators = list_validators()
        assert "test_format" in validators
        assert validators["test_format"] == "custom"
        return len(validators)

    # Run 100 parallel accesses to validator registry
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_validators) for _ in range(100)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should succeed and return same count
    assert all(isinstance(r, int) and r > 0 for r in results)
    assert len(set(results)) == 1  # All threads see same validator count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
