[Home](../README.md) / [Reference](README.md) / Python API

# Python API Reference

Complete reference for TripWire's Python API.

---

## Module: `tripwire`

### `env` (Singleton Instance)

The primary interface for environment variable management.

```python
from tripwire import env
```

This is a singleton instance of the `TripWire` class, pre-configured for immediate use.

---

## Core Methods

### `env.require()`

Require an environment variable (fails if not set or invalid).

**Signature:**
```python
def require(
    name: str,
    *,
    type: Optional[type] = None,
    default: Any = None,
    format: Optional[str] = None,
    pattern: Optional[str] = None,
    choices: Optional[List[Any]] = None,
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    validator: Optional[Callable] = None,
    secret: bool = False,
    description: Optional[str] = None,
    error_message: Optional[str] = None
) -> Any
```

**Parameters:**

- `name` (str): Environment variable name
- `type` (type, optional): Python type (str, int, float, bool, list, dict). Auto-inferred from annotation if not provided.
- `default` (Any, optional): Default value if not set (makes it optional)
- `format` (str, optional): Built-in format validator ("email", "url", "postgresql", "uuid", "ipv4")
- `pattern` (str, optional): Regex pattern to match
- `choices` (List, optional): List of allowed values
- `min_val` / `max_val` (int/float, optional): Numeric range validation
- `min_length` / `max_length` (int, optional): String length validation
- `validator` (Callable, optional): Custom validation function
- `secret` (bool): Mark as secret (masked in logs)
- `description` (str, optional): Human-readable description
- `error_message` (str, optional): Custom error message

**Returns:** Validated value with correct type

**Raises:** `EnvironmentError` if validation fails

**Examples:**

```python
# Basic usage
API_KEY: str = env.require("API_KEY")

# With type inference
PORT: int = env.require("PORT", min_val=1024, max_val=65535)

# With format validation
EMAIL: str = env.require("ADMIN_EMAIL", format="email")

# With pattern matching
API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")

# With choices
ENV: str = env.require("ENVIRONMENT", choices=["dev", "staging", "prod"])

# With custom validator
def validate_url(value: str) -> bool:
    return value.startswith("https://")

API_URL: str = env.require("API_URL", validator=validate_url)

# Mark as secret
SECRET: str = env.require("SECRET_KEY", secret=True, min_length=32)
```

---

### `env.optional()`

Declare an optional environment variable with default.

**Signature:**
```python
def optional(
    name: str,
    *,
    default: Any,
    type: Optional[type] = None,
    format: Optional[str] = None,
    pattern: Optional[str] = None,
    choices: Optional[List[Any]] = None,
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    validator: Optional[Callable] = None,
    secret: bool = False,
    description: Optional[str] = None
) -> Any
```

**Parameters:** Same as `require()`, but `default` is required.

**Examples:**

```python
# Basic optional with default
DEBUG: bool = env.optional("DEBUG", default=False)

# Optional with type inference
PORT: int = env.optional("PORT", default=8000, min_val=1024)

# Optional with validation
LOG_LEVEL: str = env.optional(
    "LOG_LEVEL",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"]
)
```

---

## Typed Methods (New in v0.4.0)

For cases where type annotations aren't available (e.g., in dictionaries).

### `env.require_str()`

```python
def require_str(name: str, **kwargs) -> str
```

### `env.require_int()`

```python
def require_int(name: str, min_val: Optional[int] = None, max_val: Optional[int] = None, **kwargs) -> int
```

### `env.require_float()`

```python
def require_float(name: str, min_val: Optional[float] = None, max_val: Optional[float] = None, **kwargs) -> float
```

### `env.require_bool()`

```python
def require_bool(name: str, **kwargs) -> bool
```

### `env.require_list()`

```python
def require_list(name: str, **kwargs) -> list
```

### `env.require_dict()`

```python
def require_dict(name: str, **kwargs) -> dict
```

**Optional Variants:**

- `env.optional_str()`
- `env.optional_int()`
- `env.optional_float()`
- `env.optional_bool()`
- `env.optional_list()`
- `env.optional_dict()`

**Example:**

```python
config = {
    "port": env.require_int("PORT", min_val=1024, max_val=65535),
    "debug": env.optional_bool("DEBUG", default=False),
    "api_key": env.require_str("API_KEY", secret=True),
}
```

---

## Configuration Methods

### `env.load()`

Load environment variables from a file.

**Signature:**
```python
def load(
    dotenv_path: str = ".env",
    *,
    override: bool = False,
    silent: bool = False
) -> None
```

**Parameters:**

- `dotenv_path` (str): Path to .env file
- `override` (bool): Override existing environment variables
- `silent` (bool): Don't raise error if file doesn't exist

**Examples:**

```python
# Load default .env
env.load()

# Load specific file
env.load(".env.production")

# Load with override
env.load(".env.local", override=True)

# Load silently (no error if missing)
env.load(".env.local", override=True, silent=True)
```

### `env.load_files()`

Load multiple .env files in order.

**Signature:**
```python
def load_files(
    paths: List[str],
    *,
    override: bool = False
) -> None
```

**Example:**

```python
env.load_files([
    ".env",
    ".env.development",
    ".env.local"
], override=True)
```

---

## Utility Methods

### `env.has()`

Check if environment variable exists.

**Signature:**
```python
def has(name: str) -> bool
```

**Example:**

```python
if env.has("FEATURE_FLAG"):
    feature_enabled = env.optional_bool("FEATURE_FLAG", default=False)
```

### `env.get()`

Get environment variable value (no validation).

**Signature:**
```python
def get(name: str, default: Any = None, type: Optional[type] = None) -> Any
```

**Example:**

```python
log_level = env.get("LOG_LEVEL", default="INFO")
```

### `env.all()`

Get all environment variables as dictionary.

**Signature:**
```python
def all() -> Dict[str, str]
```

**Example:**

```python
all_vars = env.all()
print(f"Total variables: {len(all_vars)}")
```

---

## TripWire Class

For advanced use cases, create custom instances.

```python
from tripwire import TripWire

custom_env = TripWire(
    env_file=".env.custom",
    auto_load=True,
    strict=False,
    detect_secrets=False
)
```

**Constructor Parameters:**

- `env_file` (str): Path to .env file
- `auto_load` (bool): Automatically load file on initialization
- `strict` (bool): Strict validation mode
- `detect_secrets` (bool): Enable secret detection

---

## Custom Validators

### `@validator` Decorator

Register a custom validator function.

**Signature:**
```python
def validator(func: Callable[[Any], bool]) -> Callable
```

**Example:**

```python
from tripwire import validator, env

@validator
def validate_s3_bucket(value: str) -> bool:
    """S3 bucket name must be 3-63 chars, lowercase."""
    if not 3 <= len(value) <= 63:
        return False
    if not value.islower():
        return False
    return "_" not in value

# Use validator
BUCKET: str = env.require(
    "S3_BUCKET",
    validator=validate_s3_bucket,
    error_message="Invalid S3 bucket name format"
)
```

### Validator with Error Messages

```python
@validator
def validate_api_key(value: str) -> Union[bool, Tuple[bool, str]]:
    """Return (bool, error_message) tuple for custom errors."""
    if not value.startswith("sk-"):
        return False, "API key must start with 'sk-'"
    if len(value) < 32:
        return False, "API key must be at least 32 characters"
    return True

API_KEY: str = env.require("API_KEY", validator=validate_api_key)
```

---

## Type System

### Automatic Type Inference (v0.4.0+)

TripWire automatically infers types from variable annotations:

```python
# Type inferred from annotation
PORT: int = env.require("PORT")  # Inferred as int
DEBUG: bool = env.optional("DEBUG", default=False)  # Inferred as bool
TIMEOUT: float = env.optional("TIMEOUT", default=30.0)  # Inferred as float
```

### Supported Types

- `str` - String values (default)
- `int` - Integer values
- `float` - Floating-point values
- `bool` - Boolean values (handles "true", "false", "1", "0", "yes", "no")
- `list` - Comma-separated or JSON arrays
- `dict` - JSON objects or key=value pairs

### Type Coercion

```python
# .env
PORT=8000
DEBUG=true
TIMEOUT=30.5
HOSTS=localhost,example.com
CONFIG={"key": "value"}

# Python
PORT: int = env.require("PORT")  # 8000 (int)
DEBUG: bool = env.optional("DEBUG", default=False)  # True (bool)
TIMEOUT: float = env.optional("TIMEOUT", default=30.0)  # 30.5 (float)
HOSTS: list = env.require("HOSTS")  # ["localhost", "example.com"]
CONFIG: dict = env.require("CONFIG")  # {"key": "value"}
```

---

## Exceptions

### `EnvironmentError`

Raised when environment variable validation fails.

**Attributes:**

- `variable_name` (str): Name of the variable
- `message` (str): Error description
- `suggestions` (List[str]): Helpful suggestions

**Example:**

```python
try:
    API_KEY: str = env.require("API_KEY")
except EnvironmentError as e:
    print(f"Variable: {e.variable_name}")
    print(f"Error: {e.message}")
    for suggestion in e.suggestions:
        print(f"  - {suggestion}")
```

---

## Configuration as Code API

Work with `.tripwire.toml` schemas programmatically.

```python
from tripwire.schema import Schema

# Load schema
schema = Schema.load(".tripwire.toml")

# Validate environment
schema.validate(".env", environment="production")

# Generate .env.example
schema.generate_example(".env.example")
```

---

## Best Practices

### 1. Module-Level Declarations

```python
# ✅ DO: Declare at module level
from tripwire import env

DATABASE_URL: str = env.require("DATABASE_URL")  # Validated at import
```

### 2. Use Type Annotations

```python
# ✅ DO: Use type annotations for inference
PORT: int = env.require("PORT", min_val=1024)

# ❌ DON'T: Specify type twice
PORT: int = env.require("PORT", type=int, min_val=1024)
```

### 3. Mark Secrets

```python
# ✅ DO: Mark sensitive data
API_KEY: str = env.require("API_KEY", secret=True)

# ❌ DON'T: Leave secrets unmarked
API_KEY: str = env.require("API_KEY")  # Will appear in logs!
```

### 4. Add Descriptions

```python
# ✅ DO: Document variables
DATABASE_URL: str = env.require(
    "DATABASE_URL",
    format="postgresql",
    description="PostgreSQL connection string for main database"
)
```

---

## Complete Example

```python
# config.py
"""Application configuration using TripWire."""

from tripwire import env, validator
from typing import Dict

# Database Configuration
DATABASE_URL: str = env.require(
    "DATABASE_URL",
    format="postgresql",
    secret=True,
    description="PostgreSQL connection string"
)

DB_POOL_SIZE: int = env.optional(
    "DB_POOL_SIZE",
    default=5,
    min_val=1,
    max_val=50,
    description="Database connection pool size"
)

# Security
SECRET_KEY: str = env.require(
    "SECRET_KEY",
    secret=True,
    min_length=32,
    description="Secret key for session signing"
)

# Application Settings
DEBUG: bool = env.optional("DEBUG", default=False)
LOG_LEVEL: str = env.optional(
    "LOG_LEVEL",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
)

# Custom Validator Example
@validator
def validate_url_list(value: str) -> bool:
    """Validate comma-separated URLs."""
    urls = value.split(",")
    return all(url.startswith("http") for url in urls)

ALLOWED_ORIGINS: str = env.require(
    "ALLOWED_ORIGINS",
    validator=validate_url_list,
    description="Comma-separated list of allowed CORS origins"
)

# Export configuration
__all__ = [
    "DATABASE_URL",
    "DB_POOL_SIZE",
    "SECRET_KEY",
    "DEBUG",
    "LOG_LEVEL",
    "ALLOWED_ORIGINS",
]
```

---

**[Back to Reference](README.md)**
