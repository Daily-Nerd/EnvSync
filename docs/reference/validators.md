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

## Advanced Validators

TripWire provides advanced validators for complex validation scenarios including URL component validation and datetime validation (v0.10.1+).

### URL Components Validation

Fine-grained URL validation for security policies and API requirements. Goes beyond basic URL format validation to enforce protocol whitelists, port restrictions, path patterns, and query parameter policies.

**Function Signature:**
```python
from tripwire.validation import validate_url_components

valid, error = validate_url_components(
    value: str,
    protocols: Optional[List[str]] = None,
    allowed_ports: Optional[List[int]] = None,
    forbidden_ports: Optional[List[int]] = None,
    required_path: Optional[str] = None,
    required_params: Optional[List[str]] = None,
    forbidden_params: Optional[List[str]] = None,
) -> tuple[bool, Optional[str]]
```

**Parameters:**
- `protocols`: Whitelist of allowed protocols (e.g., `["https", "wss"]` for secure-only)
- `allowed_ports`: Whitelist of allowed port numbers (e.g., `[443, 8443]`)
- `forbidden_ports`: Blacklist of forbidden ports (e.g., `[22, 3389]` to prevent SSH/RDP)
- `required_path`: Regex pattern for path validation (e.g., `"^/api/v[0-9]+/"` for versioning)
- `required_params`: List of required query parameters (e.g., `["api_key"]`)
- `forbidden_params`: List of forbidden query parameters (e.g., `["debug", "test"]`)

**Basic Usage:**
```python
from tripwire import env
from tripwire.validation import validate_url_components

# Simple HTTPS-only validation
API_URL: str = env.require(
    "API_URL",
    validator=lambda v: validate_url_components(v, protocols=["https"])[0]
)
```

**Security Example - HTTPS Only:**
```python
# Enforce HTTPS for production API endpoints
API_ENDPOINT: str = env.require(
    "API_ENDPOINT",
    validator=lambda url: validate_url_components(
        url,
        protocols=["https"],  # Only HTTPS allowed
        forbidden_ports=[22, 23, 3389, 5900],  # Block SSH, Telnet, RDP, VNC
    )[0],
    error_message="API endpoint must use HTTPS and not use privileged ports"
)

# .env
API_ENDPOINT=https://api.example.com/v1
```

**API Versioning Example:**
```python
# Enforce versioned API paths with authentication
API_URL: str = env.require(
    "API_URL",
    validator=lambda url: validate_url_components(
        url,
        protocols=["https"],
        allowed_ports=[443, 8443],
        required_path="^/api/v[0-9]+/",  # Must have /api/v1/, /api/v2/, etc.
        required_params=["api_key"],  # Must have api_key parameter
        forbidden_params=["debug", "test"],  # Prevent debug flags in production
    )[0],
    error_message="API URL must be HTTPS with versioned path and api_key parameter"
)

# .env - Valid
API_URL=https://api.example.com:443/api/v2/users?api_key=secret123

# .env - Invalid (missing version in path)
API_URL=https://api.example.com/users?api_key=secret123
```

**Using with ValidationOrchestrator (TripWireV2):**
```python
from tripwire import TripWire
from tripwire.core.validation_orchestrator import (
    URLComponentsValidationRule,
    ValidationOrchestrator,
    FormatValidationRule,
)

# Create orchestrator with multiple validation rules
orchestrator = (
    ValidationOrchestrator()
    .add_rule(FormatValidationRule("url"))  # Basic format check first
    .add_rule(
        URLComponentsValidationRule(
            protocols=["https"],
            allowed_ports=[443, 8443],
            required_path="^/api/v[0-9]+/",
            required_params=["api_key"],
            forbidden_params=["debug"],
            error_message="Invalid API URL configuration"
        )
    )
)

# Use with custom TripWire instance
env = TripWire()
# ... configure with orchestrator
```

**Real-World Use Cases:**

1. **Microservice Communication**: Enforce mTLS (mutual TLS) for internal services
   ```python
   SERVICE_URL: str = env.require(
       "SERVICE_URL",
       validator=lambda url: validate_url_components(
           url,
           protocols=["https"],
           allowed_ports=[443, 8443],
       )[0]
   )
   ```

2. **Webhook URLs**: Prevent SSRF attacks by restricting protocols
   ```python
   WEBHOOK_URL: str = env.require(
       "WEBHOOK_URL",
       validator=lambda url: validate_url_components(
           url,
           protocols=["https"],  # Prevent file://, gopher://, etc.
           forbidden_ports=[22, 23, 25, 3306, 5432],  # Block common service ports
       )[0]
   )
   ```

3. **OAuth Callback URLs**: Enforce URL structure for security
   ```python
   OAUTH_CALLBACK: str = env.require(
       "OAUTH_CALLBACK",
       validator=lambda url: validate_url_components(
           url,
           protocols=["https"],
           required_path="^/auth/callback$",
       )[0]
   )
   ```

---

### DateTime Validation

Flexible datetime validation for timestamps, scheduled tasks, expiration dates, and time-sensitive configurations. Supports ISO 8601 and custom formats with timezone awareness and date range validation.

**Function Signature:**
```python
from tripwire.validation import validate_datetime

valid, error = validate_datetime(
    value: str,
    formats: Optional[List[str]] = None,
    require_timezone: Optional[bool] = None,
    min_datetime: Optional[str] = None,
    max_datetime: Optional[str] = None,
) -> tuple[bool, Optional[str]]
```

**Parameters:**
- `formats`: List of accepted datetime formats. Use `"ISO8601"` for ISO 8601, or provide strptime format strings (e.g., `"%Y-%m-%d %H:%M:%S"`). Default: `["ISO8601"]`
- `require_timezone`: If `True`, datetime must be timezone-aware. If `False`, must be timezone-naive. If `None`, both allowed.
- `min_datetime`: Minimum allowed datetime in ISO 8601 format (e.g., `"2020-01-01T00:00:00Z"`)
- `max_datetime`: Maximum allowed datetime in ISO 8601 format (e.g., `"2030-12-31T23:59:59Z"`)

**Basic Usage:**
```python
from tripwire import env
from tripwire.validation import validate_datetime

# ISO 8601 datetime with timezone required
SCHEDULED_TIME: str = env.require(
    "SCHEDULED_TIME",
    validator=lambda v: validate_datetime(
        v,
        formats=["ISO8601"],
        require_timezone=True
    )[0]
)

# .env
SCHEDULED_TIME=2025-10-13T14:30:00Z
```

**SSL Certificate Expiration Example:**
```python
# Validate SSL certificate expiration date
CERT_EXPIRY: str = env.require(
    "CERT_EXPIRY",
    validator=lambda dt: validate_datetime(
        dt,
        formats=["ISO8601"],
        require_timezone=True,
        min_datetime="2025-01-01T00:00:00Z",  # Must be in future
        max_datetime="2027-12-31T23:59:59Z",  # Not too far in future (2-year max)
    )[0],
    error_message="SSL certificate expiration must be between 2025-2027 with timezone"
)

# .env
CERT_EXPIRY=2026-06-15T00:00:00Z
```

**Scheduled Task Example:**
```python
# Daily backup time (time-only format)
BACKUP_TIME: str = env.require(
    "BACKUP_TIME",
    validator=lambda t: validate_datetime(
        t,
        formats=["%H:%M:%S"],
        require_timezone=False  # Time-only doesn't need timezone
    )[0],
    error_message="Backup time must be in HH:MM:SS format"
)

# .env
BACKUP_TIME=02:30:00
```

**Multiple Format Support:**
```python
# Accept multiple date formats for flexibility
START_DATE: str = env.require(
    "START_DATE",
    validator=lambda d: validate_datetime(
        d,
        formats=["ISO8601", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    )[0]
)

# .env - Any of these work:
START_DATE=2025-10-13T00:00:00Z
START_DATE=2025-10-13
START_DATE=13/10/2025
START_DATE=10/13/2025
```

**Date Range Validation:**
```python
# Project milestone date must be within project timeline
MILESTONE_DATE: str = env.require(
    "MILESTONE_DATE",
    validator=lambda d: validate_datetime(
        d,
        formats=["ISO8601"],
        min_datetime="2025-01-01T00:00:00Z",  # Project start
        max_datetime="2025-12-31T23:59:59Z",  # Project end
    )[0],
    error_message="Milestone must be within 2025 project timeline"
)

# .env
MILESTONE_DATE=2025-06-15T00:00:00Z
```

**Using with ValidationOrchestrator (TripWireV2):**
```python
from tripwire import TripWire
from tripwire.core.validation_orchestrator import (
    DateTimeValidationRule,
    ValidationOrchestrator,
    LengthValidationRule,
)

# Create orchestrator with multiple validation rules
orchestrator = (
    ValidationOrchestrator()
    .add_rule(LengthValidationRule(min_length=10))  # Basic length check
    .add_rule(
        DateTimeValidationRule(
            formats=["ISO8601"],
            require_timezone=True,
            min_datetime="2020-01-01T00:00:00Z",
            max_datetime="2030-12-31T23:59:59Z",
            error_message="Invalid datetime format or range"
        )
    )
)

# Use with custom TripWire instance
env = TripWire()
# ... configure with orchestrator
```

**Real-World Use Cases:**

1. **API Token Expiration**: Validate token expiry timestamps
   ```python
   TOKEN_EXPIRY: str = env.require(
       "TOKEN_EXPIRY",
       validator=lambda dt: validate_datetime(
           dt,
           formats=["ISO8601"],
           require_timezone=True,
           min_datetime="2025-01-01T00:00:00Z",  # Must be in future
       )[0]
   )
   ```

2. **Scheduled Jobs**: Cron-like time specifications
   ```python
   DAILY_REPORT_TIME: str = env.require(
       "DAILY_REPORT_TIME",
       validator=lambda t: validate_datetime(
           t,
           formats=["%H:%M"],
           require_timezone=False
       )[0]
   )
   # .env
   DAILY_REPORT_TIME=14:30
   ```

3. **Log Retention**: Date-based retention policies
   ```python
   LOG_RETENTION_UNTIL: str = env.require(
       "LOG_RETENTION_UNTIL",
       validator=lambda d: validate_datetime(
           d,
           formats=["ISO8601"],
           min_datetime="2025-01-01T00:00:00Z",
       )[0]
   )
   ```

4. **License Expiration**: Software license validation
   ```python
   LICENSE_VALID_UNTIL: str = env.require(
       "LICENSE_VALID_UNTIL",
       validator=lambda dt: validate_datetime(
           dt,
           formats=["ISO8601"],
           require_timezone=True,
           min_datetime="2025-01-01T00:00:00Z",
           max_datetime="2030-12-31T23:59:59Z",
       )[0],
       error_message="License expiration must be within valid range (2025-2030)"
   )
   ```

**Supported Date Formats:**

- **ISO 8601**: `2025-10-13T14:30:00Z`, `2025-10-13T14:30:00+05:30`, `2025-10-13`
- **Custom strptime formats**: Any format supported by Python's `datetime.strptime()`
  - `%Y-%m-%d`: `2025-10-13`
  - `%Y-%m-%d %H:%M:%S`: `2025-10-13 14:30:00`
  - `%d/%m/%Y`: `13/10/2025`
  - `%m/%d/%Y`: `10/13/2025`
  - `%H:%M:%S`: `14:30:00`
  - `%H:%M`: `14:30`

**Timezone Handling:**

- **Timezone-aware**: `2025-10-13T14:30:00Z` (UTC), `2025-10-13T14:30:00+05:30` (offset)
- **Timezone-naive**: `2025-10-13T14:30:00`, `2025-10-13 14:30:00`
- **Requirement enforcement**: Use `require_timezone=True/False` to enforce consistency
- **Comparison handling**: Automatically normalizes timezones for min/max comparisons

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
