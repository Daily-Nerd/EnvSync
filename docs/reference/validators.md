[Home](../README.md) / [Reference](README.md) / Validators

# Validator Reference

Complete reference for TripWire's built-in and custom validators.

---

## Table of Contents

- [Built-in Format Validators](#built-in-format-validators)
- [Built-in Type Validators](#built-in-type-validators)
- [Constraint Validators](#constraint-validators)
- [Custom Validators](#custom-validators)
- [Validator Chaining](#validator-chaining)

---

## Built-in Format Validators

### Email Validator

Validates email address format.

**Usage:**
```python
EMAIL: str = env.require("ADMIN_EMAIL", format="email")
```

**Valid Examples:**
```
user@example.com
admin+tag@example.co.uk
first.last@subdomain.example.com
```

**Invalid Examples:**
```
invalid@
@example.com
user @example.com
```

---

### URL Validator

Validates URL format.

**Usage:**
```python
API_URL: str = env.require("API_BASE_URL", format="url")
```

**Valid Examples:**
```
https://example.com
http://localhost:8000
https://api.example.com/v1
ws://websocket.example.com
```

**Invalid Examples:**
```
not-a-url
htp://typo.com
example.com (missing protocol)
```

---

### PostgreSQL Validator

Validates PostgreSQL connection string format.

**Usage:**
```python
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
```

**Valid Examples:**
```
postgresql://localhost/mydb
postgresql://user:password@localhost:5432/mydb
postgres://user@host/database
postgresql://user:password@host:port/database?sslmode=require
```

**Invalid Examples:**
```
mysql://localhost/mydb
localhost:5432/mydb
```

---

### UUID Validator

Validates UUID format (v4).

**Usage:**
```python
REQUEST_ID: str = env.require("REQUEST_ID", format="uuid")
```

**Valid Examples:**
```
123e4567-e89b-12d3-a456-426614174000
550e8400-e29b-41d4-a716-446655440000
```

**Invalid Examples:**
```
not-a-uuid
123-456-789
```

---

### IPv4 Validator

Validates IPv4 address format.

**Usage:**
```python
SERVER_IP: str = env.require("SERVER_IP", format="ipv4")
```

**Valid Examples:**
```
192.168.1.1
10.0.0.1
127.0.0.1
```

**Invalid Examples:**
```
256.1.1.1
192.168.1
192.168.1.1.1
```

---

## Built-in Type Validators

### String (`str`)

Default type. No conversion needed.

**Usage:**
```python
API_KEY: str = env.require("API_KEY")
```

**Options:**
- `min_length` - Minimum string length
- `max_length` - Maximum string length
- `pattern` - Regex pattern to match

**Example:**
```python
API_KEY: str = env.require(
    "API_KEY",
    min_length=32,
    max_length=64,
    pattern=r"^sk-[a-zA-Z0-9]+$"
)
```

---

### Integer (`int`)

Converts string to integer.

**Usage:**
```python
PORT: int = env.require("PORT")
```

**Options:**
- `min_val` - Minimum value
- `max_val` - Maximum value

**Example:**
```python
PORT: int = env.require("PORT", min_val=1024, max_val=65535)
```

**Conversion Examples:**
```
"8000" → 8000
"1024" → 1024
"-1" → -1
"3.14" → ValueError (not an integer)
"abc" → ValueError
```

---

### Float (`float`)

Converts string to floating-point number.

**Usage:**
```python
TIMEOUT: float = env.require("TIMEOUT")
```

**Options:**
- `min_val` - Minimum value
- `max_val` - Maximum value

**Example:**
```python
TIMEOUT: float = env.require("TIMEOUT", min_val=0.0, max_val=300.0)
```

**Conversion Examples:**
```
"3.14" → 3.14
"30" → 30.0
"-0.5" → -0.5
"inf" → float('inf')
"abc" → ValueError
```

---

### Boolean (`bool`)

Converts string to boolean.

**Usage:**
```python
DEBUG: bool = env.optional("DEBUG", default=False)
```

**Truthy Values:**
```
"true", "True", "TRUE"
"yes", "Yes", "YES"
"on", "On", "ON"
"1"
```

**Falsy Values:**
```
"false", "False", "FALSE"
"no", "No", "NO"
"off", "Off", "OFF"
"0"
""
```

**Example:**
```python
# .env
DEBUG=true
MAINTENANCE=yes
STRICT_MODE=1

# Python
DEBUG: bool = env.optional("DEBUG", default=False)  # True
MAINTENANCE: bool = env.optional("MAINTENANCE", default=False)  # True
STRICT_MODE: bool = env.optional("STRICT_MODE", default=False)  # True
```

---

### List (`list`)

Parses comma-separated values or JSON array.

**Usage:**
```python
ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS")
```

**Formats Supported:**

**Comma-Separated:**
```bash
# .env
ALLOWED_HOSTS=localhost,example.com,api.example.com
```
```python
# Result: ["localhost", "example.com", "api.example.com"]
```

**JSON Array:**
```bash
# .env
ALLOWED_HOSTS=["localhost", "example.com", "api.example.com"]
```
```python
# Result: ["localhost", "example.com", "api.example.com"]
```

**With Whitespace:**
```bash
# .env
TAGS=web, api, backend, python
```
```python
# Result: ["web", "api", "backend", "python"]
```

---

### Dictionary (`dict`)

Parses JSON object or key=value pairs.

**Usage:**
```python
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={})
```

**Formats Supported:**

**JSON Object:**
```bash
# .env
FEATURE_FLAGS={"new_ui": true, "beta_api": false, "analytics": true}
```
```python
# Result: {"new_ui": True, "beta_api": False, "analytics": True}
```

**Key=Value Pairs:**
```bash
# .env
FEATURE_FLAGS=new_ui=true,beta_api=false,analytics=true
```
```python
# Result: {"new_ui": "true", "beta_api": "false", "analytics": "true"}
```

---

## Constraint Validators

### Range Validation

**For Integers and Floats:**

```python
# Integer range
PORT: int = env.require("PORT", min_val=1024, max_val=65535)
WORKERS: int = env.require("WORKERS", min_val=1, max_val=32)

# Float range
TIMEOUT: float = env.require("TIMEOUT", min_val=0.1, max_val=300.0)
RATE_LIMIT: float = env.optional("RATE_LIMIT", default=1.0, min_val=0.1)
```

---

### Length Validation

**For Strings:**

```python
# Minimum length
API_KEY: str = env.require("API_KEY", min_length=32)

# Maximum length
USERNAME: str = env.require("USERNAME", max_length=50)

# Both
PASSWORD: str = env.require("PASSWORD", min_length=8, max_length=128)
```

---

### Pattern Validation (Regex)

```python
# API key format
API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")

# GitHub token
GITHUB_TOKEN: str = env.require("GITHUB_TOKEN", pattern=r"^ghp_[a-zA-Z0-9]{36}$")

# Alphanumeric only
USERNAME: str = env.require("USERNAME", pattern=r"^[a-zA-Z0-9_]+$")

# SemVer version
VERSION: str = env.optional("VERSION", default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
```

---

### Choices Validation (Enum)

```python
# String choices
ENVIRONMENT: str = env.require(
    "ENVIRONMENT",
    choices=["development", "staging", "production"]
)

LOG_LEVEL: str = env.optional(
    "LOG_LEVEL",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
)

# Integer choices
HTTP_VERSION: int = env.optional(
    "HTTP_VERSION",
    default=2,
    choices=[1, 2, 3]
)
```

---

## Custom Validators

### Basic Custom Validator

```python
from tripwire import env, validator

@validator
def validate_s3_bucket(value: str) -> bool:
    """S3 bucket names: 3-63 chars, lowercase, no underscores."""
    if not 3 <= len(value) <= 63:
        return False
    if not value.islower():
        return False
    return "_" not in value

S3_BUCKET: str = env.require("S3_BUCKET", validator=validate_s3_bucket)
```

---

### Custom Validator with Error Messages

```python
@validator
def validate_api_key(value: str) -> tuple[bool, str]:
    """Return (success, error_message) for detailed errors."""
    if not value.startswith("sk-"):
        return False, "API key must start with 'sk-'"

    if len(value) < 32:
        return False, f"API key too short ({len(value)} chars, minimum 32)"

    if not value[3:].replace("-", "").isalnum():
        return False, "API key contains invalid characters"

    return True, ""

API_KEY: str = env.require("API_KEY", validator=validate_api_key)
```

---

### Lambda Validators

For simple inline validation:

```python
# Port in valid range
PORT: int = env.require(
    "PORT",
    validator=lambda x: 1024 <= x <= 65535,
    error_message="Port must be between 1024 and 65535"
)

# URL must be HTTPS
API_URL: str = env.require(
    "API_URL",
    validator=lambda x: x.startswith("https://"),
    error_message="API URL must use HTTPS"
)

# Even number only
WORKERS: int = env.require(
    "WORKERS",
    validator=lambda x: x % 2 == 0,
    error_message="WORKERS must be an even number"
)
```

---

### Complex Custom Validators

```python
import re
from typing import Union

@validator
def validate_url_list(value: str) -> Union[bool, tuple[bool, str]]:
    """Validate comma-separated list of URLs."""
    urls = [url.strip() for url in value.split(",")]

    url_pattern = re.compile(r"^https?://[^\s]+$")

    for url in urls:
        if not url_pattern.match(url):
            return False, f"Invalid URL in list: {url}"

    return True, ""

ALLOWED_ORIGINS: str = env.require(
    "ALLOWED_ORIGINS",
    validator=validate_url_list
)
```

---

### Reusable Validators

```python
# validators.py
from tripwire import validator

@validator
def is_port_number(value: int) -> tuple[bool, str]:
    """Validate port number (1024-65535)."""
    if not isinstance(value, int):
        return False, "Port must be an integer"
    if not 1024 <= value <= 65535:
        return False, f"Port {value} outside valid range (1024-65535)"
    return True, ""

@validator
def is_valid_domain(value: str) -> tuple[bool, str]:
    """Validate domain name format."""
    pattern = r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    if not re.match(pattern, value):
        return False, f"Invalid domain: {value}"
    return True, ""

@validator
def is_hex_color(value: str) -> tuple[bool, str]:
    """Validate hex color code."""
    pattern = r"^#[0-9A-Fa-f]{6}$"
    if not re.match(pattern, value):
        return False, f"Invalid hex color: {value} (expected #RRGGBB)"
    return True, ""
```

```python
# config.py
from validators import is_port_number, is_valid_domain, is_hex_color

PORT: int = env.require("PORT", validator=is_port_number)
DOMAIN: str = env.require("DOMAIN", validator=is_valid_domain)
PRIMARY_COLOR: str = env.optional("PRIMARY_COLOR", default="#3498db", validator=is_hex_color)
```

---

## Validator Chaining

Combine multiple validators:

```python
@validator
def validate_api_key_format(value: str) -> tuple[bool, str]:
    """Check format."""
    if not value.startswith("sk-"):
        return False, "Must start with 'sk-'"
    return True, ""

@validator
def validate_api_key_length(value: str) -> tuple[bool, str]:
    """Check length."""
    if len(value) < 32:
        return False, f"Too short: {len(value)} chars (minimum 32)"
    return True, ""

# Use both validators
API_KEY: str = env.require(
    "API_KEY",
    pattern=r"^sk-[a-zA-Z0-9]+$",  # Pattern validation
    min_length=32,                  # Length validation
    validator=validate_api_key_format  # Custom validation
)
```

**Validation Order:**
1. Type coercion
2. Format validation
3. Pattern validation
4. Length/range validation
5. Choices validation
6. Custom validator

---

## Best Practices

### 1. Descriptive Error Messages

```python
# ✅ DO: Provide helpful errors
@validator
def validate_aws_region(value: str) -> tuple[bool, str]:
    valid_regions = ["us-east-1", "us-west-2", "eu-west-1"]
    if value not in valid_regions:
        return False, f"Invalid region: {value}. Valid: {', '.join(valid_regions)}"
    return True, ""

# ❌ DON'T: Generic errors
@validator
def validate_aws_region(value: str) -> bool:
    return value in ["us-east-1", "us-west-2", "eu-west-1"]
```

### 2. Fail Fast

```python
# ✅ DO: Check simplest conditions first
@validator
def validate_url(value: str) -> tuple[bool, str]:
    if not value:
        return False, "URL cannot be empty"
    if not value.startswith("http"):
        return False, "URL must start with http:// or https://"
    # More complex checks...
    return True, ""
```

### 3. Document Validators

```python
# ✅ DO: Add docstrings
@validator
def validate_cron_expression(value: str) -> tuple[bool, str]:
    """
    Validate cron expression format.

    Expected format: minute hour day month weekday
    Example: "0 0 * * *" (daily at midnight)

    Returns:
        (True, "") if valid
        (False, error_message) if invalid
    """
    # Validation logic...
```

---

**[Back to Reference](README.md)**
