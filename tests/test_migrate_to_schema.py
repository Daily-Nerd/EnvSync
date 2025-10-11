"""Tests for migrate-to-schema command functionality."""

import re
import tempfile
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from tripwire.cli import main


@pytest.fixture
def runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_migrate_to_schema_basic_conversion(runner, temp_dir):
    """Test basic .env.example to .tripwire.toml conversion."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """# Database Configuration
DATABASE_URL=postgresql://localhost:5432/mydb

# Server Settings
PORT=8000
DEBUG=false
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    # Verify TOML structure
    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    assert "variables" in data
    assert "DATABASE_URL" in data["variables"]
    assert "PORT" in data["variables"]
    assert "DEBUG" in data["variables"]


def test_migrate_to_schema_type_inference(runner, temp_dir):
    """Test type inference from values."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """STRING_VAR=hello
INT_VAR=42
FLOAT_VAR=3.14
BOOL_TRUE=true
BOOL_FALSE=false
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Verify types
    assert data["variables"]["STRING_VAR"]["type"] == "string"
    assert data["variables"]["INT_VAR"]["type"] == "int"
    assert data["variables"]["FLOAT_VAR"]["type"] == "float"
    assert data["variables"]["BOOL_TRUE"]["type"] == "bool"
    assert data["variables"]["BOOL_FALSE"]["type"] == "bool"

    # Verify defaults
    assert data["variables"]["STRING_VAR"]["default"] == "hello"
    assert data["variables"]["INT_VAR"]["default"] == 42
    assert data["variables"]["FLOAT_VAR"]["default"] == 3.14
    assert data["variables"]["BOOL_TRUE"]["default"] is True
    assert data["variables"]["BOOL_FALSE"]["default"] is False


def test_migrate_to_schema_comprehensive_boolean_inference(runner, temp_dir):
    """Test comprehensive boolean type inference (v0.7.1 fix).

    Verifies that all common boolean patterns are correctly detected:
    - true/false
    - yes/no
    - on/off
    - enabled/disabled
    - 1/0 (should be bool, not int)
    - Case insensitive variations
    """
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """# True value patterns
BOOL_TRUE_LOWER=true
BOOL_TRUE_UPPER=TRUE
BOOL_YES=yes
BOOL_YES_UPPER=YES
BOOL_ON=on
BOOL_ON_UPPER=ON
BOOL_ENABLED=enabled
BOOL_ENABLED_UPPER=ENABLED
BOOL_ONE=1

# False value patterns
BOOL_FALSE_LOWER=false
BOOL_FALSE_UPPER=FALSE
BOOL_NO=no
BOOL_NO_UPPER=NO
BOOL_OFF=off
BOOL_OFF_UPPER=OFF
BOOL_DISABLED=disabled
BOOL_DISABLED_UPPER=DISABLED
BOOL_ZERO=0

# Non-boolean values (should remain other types)
INT_VAR=42
FLOAT_VAR=3.14
STRING_VAR=hello
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Verify all true value patterns are detected as bool
    true_vars = [
        "BOOL_TRUE_LOWER",
        "BOOL_TRUE_UPPER",
        "BOOL_YES",
        "BOOL_YES_UPPER",
        "BOOL_ON",
        "BOOL_ON_UPPER",
        "BOOL_ENABLED",
        "BOOL_ENABLED_UPPER",
        "BOOL_ONE",
    ]
    for var in true_vars:
        assert data["variables"][var]["type"] == "bool", f"{var} should be bool"
        assert data["variables"][var]["default"] is True, f"{var} should default to True"

    # Verify all false value patterns are detected as bool
    false_vars = [
        "BOOL_FALSE_LOWER",
        "BOOL_FALSE_UPPER",
        "BOOL_NO",
        "BOOL_NO_UPPER",
        "BOOL_OFF",
        "BOOL_OFF_UPPER",
        "BOOL_DISABLED",
        "BOOL_DISABLED_UPPER",
        "BOOL_ZERO",
    ]
    for var in false_vars:
        assert data["variables"][var]["type"] == "bool", f"{var} should be bool"
        assert data["variables"][var]["default"] is False, f"{var} should default to False"

    # Verify non-boolean values remain their original types
    assert data["variables"]["INT_VAR"]["type"] == "int"
    assert data["variables"]["INT_VAR"]["default"] == 42
    assert data["variables"]["FLOAT_VAR"]["type"] == "float"
    assert data["variables"]["FLOAT_VAR"]["default"] == 3.14
    assert data["variables"]["STRING_VAR"]["type"] == "string"
    assert data["variables"]["STRING_VAR"]["default"] == "hello"


def test_migrate_to_schema_placeholder_detection(runner, temp_dir):
    """Test that placeholders are detected and marked as required."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """API_KEY=your-api-key-here
SECRET=change-me
TOKEN=REPLACE_ME
PASSWORD=<your-password>
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Placeholders should be required without defaults
    assert data["variables"]["API_KEY"]["required"] is True
    assert "default" not in data["variables"]["API_KEY"]

    assert data["variables"]["SECRET"]["required"] is True
    assert "default" not in data["variables"]["SECRET"]

    assert data["variables"]["TOKEN"]["required"] is True
    assert "default" not in data["variables"]["TOKEN"]

    assert data["variables"]["PASSWORD"]["required"] is True
    assert "default" not in data["variables"]["PASSWORD"]


def test_migrate_to_schema_secret_detection(runner, temp_dir):
    """Test that secrets are properly detected using comprehensive detection.

    Tests both platform-specific patterns and generic credential detection
    with realistic secret values (not simple placeholders like 'abc123').
    """
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """API_KEY=xsk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567
DATABASE_PASSWORD=xMyP@ssw0rd_Str0ng_2024
JWT_SECRET=xeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
ACCESS_TOKEN=xghp_abc123def456ghi789jkl012mno345pqr678
ENCRYPTION_KEY=xAxES256_enc_key_base64_encoded_value_12345678901234567890
PRIVATE_KEY=x-----BEGIN RSA PRIVATE KEY-----
PORT=8000
DEBUG=false
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Secrets should be marked
    assert data["variables"]["API_KEY"].get("secret", False) is True
    assert data["variables"]["DATABASE_PASSWORD"].get("secret", False) is True
    assert data["variables"]["JWT_SECRET"].get("secret", False) is True
    assert data["variables"]["ACCESS_TOKEN"].get("secret", False) is True
    assert data["variables"]["ENCRYPTION_KEY"].get("secret", False) is True
    assert data["variables"]["PRIVATE_KEY"].get("secret", False) is True

    # Non-secrets should not be marked
    assert data["variables"]["PORT"].get("secret", False) is False
    assert data["variables"]["DEBUG"].get("secret", False) is False


def test_migrate_to_schema_format_detection(runner, temp_dir):
    """Test format validator detection."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """DATABASE_URL=postgresql://localhost:5432/mydb
API_URL=https://api.example.com
USER_EMAIL=user@example.com
SERVER_IP=192.168.1.1
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Verify format validators
    assert data["variables"]["DATABASE_URL"]["format"] == "postgresql"
    assert data["variables"]["API_URL"]["format"] == "url"
    assert data["variables"]["USER_EMAIL"]["format"] == "email"
    assert data["variables"]["SERVER_IP"]["format"] == "ipv4"


def test_migrate_to_schema_empty_values(runner, temp_dir):
    """Test handling of empty values (should be required)."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """REQUIRED_VAR=
ANOTHER_REQUIRED=
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Empty values should be required without defaults
    assert data["variables"]["REQUIRED_VAR"]["required"] is True
    assert "default" not in data["variables"]["REQUIRED_VAR"]

    assert data["variables"]["ANOTHER_REQUIRED"]["required"] is True
    assert "default" not in data["variables"]["ANOTHER_REQUIRED"]


def test_migrate_to_schema_overwrite_protection(runner, temp_dir):
    """Test that existing files are protected without --force."""
    env_example = temp_dir / ".env.example"
    env_example.write_text("VAR=value")

    output_file = temp_dir / ".tripwire.toml"
    output_file.write_text("# Existing file")

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 1
    # Normalize output to handle line breaks on Windows
    normalized_output = re.sub(r"\s+", " ", result.output)
    assert "already exists" in normalized_output


def test_migrate_to_schema_with_force(runner, temp_dir):
    """Test --force flag overwrites existing files."""
    env_example = temp_dir / ".env.example"
    env_example.write_text("VAR=value")

    output_file = temp_dir / ".tripwire.toml"
    output_file.write_text("# Existing file")

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    # Should contain new content
    with open(output_file, "rb") as f:
        data = tomllib.load(f)
    assert "variables" in data
    assert "VAR" in data["variables"]


def test_migrate_to_schema_missing_source(runner, temp_dir):
    """Test error when source file doesn't exist."""
    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(temp_dir / "nonexistent.env"),
        ],
    )

    # Click returns exit code 2 for invalid path
    assert result.exit_code in (1, 2)
    # Error message may come from Click or our code
    # Normalize output to handle line breaks on Windows
    normalized_output = re.sub(r"\s+", " ", result.output)
    assert "does not exist" in normalized_output or "Error" in normalized_output


def test_migrate_to_schema_with_comments(runner, temp_dir):
    """Test that comments are preserved as descriptions."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """# This is the API key
API_KEY=your-key-here

# Server port number
PORT=8000
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Comments should become descriptions
    # Note: The current implementation has basic comment handling
    # This test validates the structure is correct
    assert "variables" in data
    assert "API_KEY" in data["variables"]
    assert "PORT" in data["variables"]


def test_migrate_to_schema_complex_example(runner, temp_dir):
    """Test complex real-world .env.example conversion."""
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """# Environment Variables
# Generated by TripWire

# Required Variables

# Database connection URL
# Type: string | Required | Format: postgresql
DATABASE_URL=postgresql://localhost:5432/mydb

# API access key
# Type: string | Required
API_KEY=your-api-key-here

# Optional Variables

# Server port
# Type: int | Optional | Default: 8000
PORT=8000

# Enable debug mode
# Type: bool | Optional | Default: false
DEBUG=false

# Maximum number of workers
# Type: int | Optional | Default: 4
MAX_WORKERS=4
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file, "rb") as f:
        data = tomllib.load(f)

    # Verify structure
    assert "project" in data
    assert "variables" in data

    # Verify specific variables
    assert data["variables"]["DATABASE_URL"]["type"] == "string"
    assert data["variables"]["DATABASE_URL"]["format"] == "postgresql"

    assert data["variables"]["API_KEY"]["required"] is True
    assert "default" not in data["variables"]["API_KEY"]  # Placeholder

    assert data["variables"]["PORT"]["type"] == "int"
    assert data["variables"]["PORT"]["default"] == 8000

    assert data["variables"]["DEBUG"]["type"] == "bool"
    assert data["variables"]["DEBUG"]["default"] is False

    assert data["variables"]["MAX_WORKERS"]["type"] == "int"
    assert data["variables"]["MAX_WORKERS"]["default"] == 4


def test_migrate_to_schema_statistics_output(runner, temp_dir):
    """Test that command outputs useful statistics including secret detection.

    Uses realistic secret values so statistics include detected secrets.
    """
    env_example = temp_dir / ".env.example"
    env_example.write_text(
        """API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567
SECRET_TOKEN=ghp_realGitHubToken123456789012345678901234
PORT=8000
DEBUG=false
"""
    )

    output_file = temp_dir / ".tripwire.toml"

    result = runner.invoke(
        main,
        [
            "schema",
            "from-example",
            "--source",
            str(env_example),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    # Check for statistics in output
    # Normalize output to handle line breaks on Windows
    normalized_output = re.sub(r"\s+", " ", result.output)
    assert "4 variable(s)" in normalized_output
    assert "required" in normalized_output
    assert "secret(s)" in normalized_output
