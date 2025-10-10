[Home](../README.md) / [Advanced](README.md) / Custom Validators

# Writing Custom Validators

Advanced guide to creating custom validation logic for TripWire.

---

## Basic Custom Validator

```python
from tripwire import env, validator

@validator
def validate_s3_bucket(value: str) -> bool:
    """
    S3 bucket names must be:
    - 3-63 characters long
    - Lowercase letters, numbers, hyphens
    - No underscores
    """
    if not 3 <= len(value) <= 63:
        return False
    if not value.islower():
        return False
    if "_" in value:
        return False
    return True

S3_BUCKET: str = env.require("S3_BUCKET", validator=validate_s3_bucket)
```

---

## Validator with Error Messages

Return `(bool, str)` tuple for custom error messages:

```python
@validator
def validate_api_key(value: str) -> tuple[bool, str]:
    """Validate API key format with descriptive errors."""

    if not value.startswith("sk-"):
        return False, "API key must start with 'sk-'"

    if len(value) < 32:
        return False, f"API key too short: {len(value)} chars (minimum 32)"

    if not value[3:].isalnum():
        return False, "API key contains invalid characters"

    return True, ""  # Success

API_KEY: str = env.require("API_KEY", validator=validate_api_key)
```

---

## Complex Validators

### Multi-Format Validator

```python
import re
from typing import Union

@validator
def validate_database_url(value: str) -> tuple[bool, str]:
    """Support multiple database formats."""

    # PostgreSQL
    pg_pattern = r"^postgresql://[^/]+/\w+$"
    # MySQL
    mysql_pattern = r"^mysql://[^/]+/\w+$"
    # SQLite
    sqlite_pattern = r"^sqlite:///.*\.db$"

    if re.match(pg_pattern, value):
        return True, ""
    elif re.match(mysql_pattern, value):
        return True, ""
    elif re.match(sqlite_pattern, value):
        return True, ""
    else:
        return False, "Invalid database URL (supported: postgresql, mysql, sqlite)"

DATABASE_URL: str = env.require("DATABASE_URL", validator=validate_database_url)
```

### List Validator

```python
@validator
def validate_email_list(value: str) -> tuple[bool, str]:
    """Validate comma-separated email addresses."""

    emails = [email.strip() for email in value.split(",")]

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    for email in emails:
        if not re.match(email_pattern, email):
            return False, f"Invalid email in list: {email}"

    return True, ""

ADMIN_EMAILS: str = env.require("ADMIN_EMAILS", validator=validate_email_list)
```

### Range Validator with Custom Logic

```python
@validator
def validate_port_range(value: int) -> tuple[bool, str]:
    """Validate port is in privileged or unprivileged range."""

    # Unprivileged ports: 1024-65535
    if 1024 <= value <= 65535:
        return True, ""

    # Privileged ports: 1-1023 (require warning)
    if 1 <= value < 1024:
        return False, f"Port {value} is privileged (< 1024). Use 1024+ for unprivileged."

    return False, f"Port {value} outside valid range (1-65535)"

PORT: int = env.require("PORT", validator=validate_port_range)
```

---

## Reusable Validator Library

Create a validators module:

```python
# my_validators.py
"""Custom validators for my project."""

from tripwire import validator
import re

@validator
def is_hex_color(value: str) -> tuple[bool, str]:
    """Validate hex color code (#RRGGBB)."""
    pattern = r"^#[0-9A-Fa-f]{6}$"
    if not re.match(pattern, value):
        return False, f"Invalid hex color: {value} (expected #RRGGBB)"
    return True, ""

@validator
def is_semver(value: str) -> tuple[bool, str]:
    """Validate semantic version (major.minor.patch)."""
    pattern = r"^\d+\.\d+\.\d+$"
    if not re.match(pattern, value):
        return False, f"Invalid semver: {value} (expected X.Y.Z)"
    return True, ""

@validator
def is_aws_region(value: str) -> tuple[bool, str]:
    """Validate AWS region code."""
    valid_regions = [
        "us-east-1", "us-west-1", "us-west-2",
        "eu-west-1", "eu-central-1", "ap-southeast-1"
    ]
    if value not in valid_regions:
        return False, f"Invalid region: {value}. Valid: {', '.join(valid_regions)}"
    return True, ""

@validator
def is_cron_expression(value: str) -> tuple[bool, str]:
    """Validate cron expression format."""
    parts = value.split()
    if len(parts) != 5:
        return False, f"Invalid cron: {value} (expected 5 fields)"

    # Basic validation of each field
    # (full cron validation is complex, this is simplified)
    for part in parts:
        if not (part.isdigit() or part == "*" or "/" in part or "-" in part):
            return False, f"Invalid cron field: {part}"

    return True, ""
```

Use in config:

```python
# config.py
from my_validators import is_hex_color, is_semver, is_aws_region, is_cron_expression

PRIMARY_COLOR: str = env.optional(
    "PRIMARY_COLOR",
    default="#3498db",
    validator=is_hex_color
)

APP_VERSION: str = env.require("APP_VERSION", validator=is_semver)
AWS_REGION: str = env.require("AWS_REGION", validator=is_aws_region)
BACKUP_SCHEDULE: str = env.optional(
    "BACKUP_SCHEDULE",
    default="0 0 * * *",
    validator=is_cron_expression
)
```

---

## Testing Validators

```python
# test_validators.py
import pytest
from my_validators import is_hex_color, is_semver

def test_hex_color_validator():
    # Valid colors
    assert is_hex_color("#000000") == (True, "")
    assert is_hex_color("#FFFFFF") == (True, "")
    assert is_hex_color("#3498db") == (True, "")

    # Invalid colors
    result = is_hex_color("#ZZZ")
    assert result[0] is False
    assert "Invalid hex color" in result[1]

    result = is_hex_color("3498db")  # Missing #
    assert result[0] is False

def test_semver_validator():
    # Valid versions
    assert is_semver("1.0.0") == (True, "")
    assert is_semver("2.3.4") == (True, "")

    # Invalid versions
    result = is_semver("1.0")
    assert result[0] is False

    result = is_semver("v1.0.0")
    assert result[0] is False
```

---

## Best Practices

### 1. Return Descriptive Errors

```python
# ✅ DO
@validator
def validate_port(value: int) -> tuple[bool, str]:
    if value < 1 or value > 65535:
        return False, f"Port {value} outside range 1-65535"
    return True, ""

# ❌ DON'T
@validator
def validate_port(value: int) -> bool:
    return 1 <= value <= 65535  # No error message
```

### 2. Fail Fast

```python
# ✅ DO: Check simple conditions first
@validator
def validate_url(value: str) -> tuple[bool, str]:
    if not value:
        return False, "URL cannot be empty"

    if not value.startswith("http"):
        return False, "URL must start with http:// or https://"

    # More complex checks...
    return True, ""
```

### 3. Document Expected Format

```python
# ✅ DO: Include examples in docstring
@validator
def validate_cron_expression(value: str) -> tuple[bool, str]:
    """
    Validate cron expression format.

    Expected format: minute hour day month weekday
    Examples:
        "0 0 * * *" - Daily at midnight
        "*/5 * * * *" - Every 5 minutes
        "0 9-17 * * MON-FRI" - Weekdays 9am-5pm
    """
    # Validation logic...
```

### 4. Make Validators Pure Functions

```python
# ✅ DO: No side effects
@validator
def validate_api_key(value: str) -> tuple[bool, str]:
    # Only validates, doesn't modify state
    return value.startswith("sk-"), ""

# ❌ DON'T: Side effects
@validator
def validate_api_key(value: str) -> tuple[bool, str]:
    global api_key_count  # Don't modify global state!
    api_key_count += 1
    return value.startswith("sk-"), ""
```

---

**[Back to Advanced](README.md)**
