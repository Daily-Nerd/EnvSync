# Plugin Development Guide

This guide covers everything you need to know to create custom TripWire plugins for loading environment variables from external sources like cloud secrets managers, configuration services, and key vaults.

## Table of Contents

- [Introduction](#introduction)
- [Plugin Architecture](#plugin-architecture)
- [Creating Your First Plugin](#creating-your-first-plugin)
- [Plugin Metadata](#plugin-metadata)
- [Configuration Validation](#configuration-validation)
- [Loading Environment Variables](#loading-environment-variables)
- [Error Handling](#error-handling)
- [Testing Your Plugin](#testing-your-plugin)
- [Security Best Practices](#security-best-practices)
- [Advanced Topics](#advanced-topics)
- [Publishing Your Plugin](#publishing-your-plugin)

## Introduction

### What Are TripWire Plugins?

TripWire plugins extend TripWire's environment variable management capabilities by allowing you to load configuration from external sources. Instead of relying solely on `.env` files, plugins enable integration with:

- **Cloud Secrets Managers**: AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
- **Configuration Services**: Remote HTTP endpoints, Consul, etcd
- **Custom Sources**: Databases, internal APIs, legacy systems

### Why Create a Plugin?

Create a custom plugin when you need to:

- Integrate with proprietary or internal configuration systems
- Support a secrets manager not included in TripWire's built-in plugins
- Implement custom authentication or access patterns
- Bridge legacy systems with modern TripWire workflows

### Prerequisites

Before building plugins, you should be familiar with:

- Python 3.11+ type hints and protocols
- Environment variable management concepts
- The external service/API you're integrating with
- Basic error handling and validation patterns

## Plugin Architecture

### The EnvSourcePlugin Protocol

TripWire uses Python's Protocol system (PEP 544) to define the plugin interface. This provides structural subtyping without requiring explicit inheritance.

All plugins must implement three core components:

```python
from typing import Protocol, Any
from tripwire.plugins.base import PluginMetadata

class EnvSourcePlugin(Protocol):
    """Protocol defining the interface all TripWire plugins must implement."""

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata for registration and discovery."""
        ...

    def load(self) -> dict[str, str]:
        """Load environment variables from the plugin source."""
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        ...
```

### The PluginInterface Base Class

While you can implement the protocol directly, TripWire provides `PluginInterface` as a convenient abstract base class:

```python
from abc import abstractmethod
from tripwire.plugins.base import PluginInterface, PluginMetadata

class MyPlugin(PluginInterface):
    def __init__(self, metadata: PluginMetadata) -> None:
        super().__init__(metadata)
        # Your initialization code

    @abstractmethod
    def load(self) -> dict[str, str]:
        # Must implement
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        # Must implement
        pass
```

### Plugin Lifecycle

1. **Registration**: Plugin class is registered with `PluginRegistry`
2. **Validation**: TripWire validates the plugin implements required methods
3. **Instantiation**: User creates plugin instance with configuration
4. **Configuration Validation**: Plugin validates its configuration
5. **Loading**: Plugin's `load()` method retrieves environment variables
6. **Injection**: TripWire merges loaded variables into environment

## Creating Your First Plugin

Let's build a simple plugin that loads environment variables from a JSON file over HTTP.

### Step 1: Define Plugin Metadata

```python
from tripwire.plugins.base import PluginInterface, PluginMetadata
from tripwire.plugins.errors import PluginAPIError, PluginValidationError
from typing import Any

class HTTPConfigPlugin(PluginInterface):
    """Plugin to load environment variables from an HTTP JSON endpoint."""

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        timeout: int = 10
    ) -> None:
        """Initialize HTTP config plugin.

        Args:
            url: HTTP(S) URL to fetch configuration from
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 10)

        Raises:
            PluginValidationError: If configuration is invalid
        """
        # Define plugin metadata
        metadata = PluginMetadata(
            name="http-config",
            version="1.0.0",
            author="Your Name",
            description="Load environment variables from HTTP JSON endpoint",
            homepage="https://github.com/yourusername/tripwire-http-config",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["http", "remote", "json"],
        )
        super().__init__(metadata)

        # Store configuration
        self.url = url
        self.api_key = api_key
        self.timeout = timeout

        # Validate configuration during initialization
        errors: list[str] = []
        if not self.url:
            errors.append("URL is required")
        if not self.url.startswith(("http://", "https://")):
            errors.append("URL must start with http:// or https://")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)
```

### Step 2: Implement the load() Method

```python
    def load(self) -> dict[str, str]:
        """Load environment variables from HTTP endpoint.

        Returns:
            Dictionary mapping environment variable names to values

        Raises:
            PluginAPIError: If HTTP request fails or response is invalid
        """
        try:
            import requests
        except ImportError as e:
            raise PluginAPIError(
                self.metadata.name,
                "load",
                original_error=e,
                message="requests library not installed. Install with: pip install requests"
            ) from e

        try:
            # Build request headers
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Make HTTP request
            response = requests.get(
                self.url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Convert to string dictionary (TripWire expects string values)
            env_vars: dict[str, str] = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    env_vars[key] = str(value)
                else:
                    # Skip complex types (lists, dicts)
                    continue

            return env_vars

        except requests.RequestException as e:
            raise PluginAPIError(
                self.metadata.name,
                "load",
                original_error=e,
                message=f"HTTP request to {self.url} failed: {str(e)}"
            ) from e
        except ValueError as e:
            raise PluginAPIError(
                self.metadata.name,
                "load",
                original_error=e,
                message=f"Invalid JSON response from {self.url}"
            ) from e
```

### Step 3: Implement validate_config()

```python
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Configuration dictionary with keys:
                - url: HTTP endpoint URL (required)
                - api_key: API key for authentication (optional)
                - timeout: Request timeout in seconds (optional)

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid
        """
        errors: list[str] = []

        # Check required fields
        if "url" not in config or not config["url"]:
            errors.append("Missing required field: url")
        else:
            url = config["url"]
            if not isinstance(url, str):
                errors.append("url must be a string")
            elif not url.startswith(("http://", "https://")):
                errors.append("url must start with http:// or https://")

        # Validate optional fields
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("timeout must be a positive number")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        return True
```

### Step 4: Use Your Plugin

```python
from tripwire import TripWire

# Instantiate your plugin
http_plugin = HTTPConfigPlugin(
    url="https://config.example.com/api/env",
    api_key="your-api-key",
    timeout=15
)

# Use with TripWire
env = TripWire(sources=[http_plugin])

# Access environment variables loaded from HTTP endpoint
DATABASE_URL: str = env.require("DATABASE_URL")
API_KEY: str = env.require("API_KEY")
```

## Plugin Metadata

### PluginMetadata Fields

The `PluginMetadata` dataclass contains information about your plugin:

```python
@dataclass(frozen=True)
class PluginMetadata:
    name: str                           # Unique plugin identifier (lowercase, hyphens/underscores)
    version: str                        # Semantic version (e.g., "1.0.0")
    author: str                         # Author name or organization
    description: str                    # Human-readable description
    homepage: str | None = None         # URL to documentation/repository
    license: str | None = None          # License identifier (e.g., "MIT")
    min_tripwire_version: str = "0.10.0"  # Minimum TripWire version required
    tags: list[str] = field(default_factory=list)  # Tags for categorization
```

### Metadata Validation Rules

TripWire automatically validates plugin metadata:

1. **Name**: Must be non-empty, contain only alphanumeric characters, hyphens, and underscores
2. **Version**: Must follow semantic versioning (e.g., "1.0.0" or "1.0")
3. **Author**: Must be non-empty
4. **Description**: Must be non-empty

Example of invalid metadata:

```python
# INVALID - will raise PluginValidationError
metadata = PluginMetadata(
    name="my plugin!",  # Contains space and special character
    version="invalid",   # Not semantic versioning
    author="",          # Empty author
    description=""      # Empty description
)
```

### Choosing Good Metadata

**Name**: Use lowercase with hyphens for multi-word names:
- ✅ Good: `vault`, `aws-secrets`, `http-config`
- ❌ Bad: `VaultPlugin`, `AWS_Secrets`, `http config`

**Version**: Follow [Semantic Versioning](https://semver.org):
- `1.0.0` - Initial release
- `1.1.0` - New features (backward compatible)
- `2.0.0` - Breaking changes

**Tags**: Use descriptive tags for discovery:
- Service type: `vault`, `aws`, `azure`, `http`
- Purpose: `secrets`, `config`, `cloud`
- Category: `database`, `api`, `messaging`

## Configuration Validation

### Why Validate Configuration?

Configuration validation ensures:
- **Fail-Fast Behavior**: Catch errors at initialization, not during load
- **Clear Error Messages**: Help users fix configuration issues
- **Security**: Prevent malicious or malformed inputs
- **Type Safety**: Ensure configuration matches expected types

### Validation Best Practices

#### 1. Validate in __init__() AND validate_config()

```python
def __init__(self, url: str, api_key: str | None = None) -> None:
    metadata = PluginMetadata(...)
    super().__init__(metadata)

    # Validate during initialization
    errors: list[str] = []
    if not url:
        errors.append("URL is required")
    if not url.startswith("https://"):
        errors.append("URL must use HTTPS")

    if errors:
        raise PluginValidationError(self.metadata.name, errors)

    self.url = url
    self.api_key = api_key

def validate_config(self, config: dict[str, Any]) -> bool:
    """Validate configuration dictionary (for programmatic usage)."""
    errors: list[str] = []

    if "url" not in config or not config["url"]:
        errors.append("Missing required field: url")
    else:
        url = config["url"]
        if not url.startswith("https://"):
            errors.append("URL must use HTTPS")

    if errors:
        raise PluginValidationError(self.metadata.name, errors)

    return True
```

#### 2. Use Accumulative Error Reporting

Collect ALL errors before raising exception:

```python
# ✅ Good - reports all errors at once
errors: list[str] = []
if not url:
    errors.append("URL is required")
if not api_key:
    errors.append("API key is required")
if timeout <= 0:
    errors.append("Timeout must be positive")

if errors:
    raise PluginValidationError(self.metadata.name, errors)

# ❌ Bad - only reports first error
if not url:
    raise PluginValidationError(self.metadata.name, ["URL is required"])
if not api_key:
    raise PluginValidationError(self.metadata.name, ["API key is required"])
```

#### 3. Validate URL Formats Carefully

```python
from urllib.parse import urlparse

def _validate_vault_url(self, url: str) -> list[str]:
    """Validate Azure Key Vault URL format."""
    errors: list[str] = []

    try:
        parsed = urlparse(url)

        # Must use HTTPS
        if parsed.scheme != "https":
            errors.append(f"URL must use HTTPS: {url}")

        # Validate domain suffix
        if not parsed.hostname or not parsed.hostname.endswith(".vault.azure.net"):
            errors.append(
                f"Invalid Azure Key Vault URL format. "
                f"Hostname must end with '.vault.azure.net': {url}"
            )
    except Exception as e:
        errors.append(f"Invalid URL format: {url} - {e}")

    return errors
```

#### 4. Support Environment Variable Fallbacks

```python
import os

def __init__(
    self,
    api_key: str | None = None,
    region: str | None = None
) -> None:
    # Allow environment variables as fallback
    self.api_key = api_key or os.getenv("PLUGIN_API_KEY")
    self.region = region or os.getenv("PLUGIN_REGION", "us-east-1")

    # Validate after fallback resolution
    errors: list[str] = []
    if not self.api_key:
        errors.append("API key is required (api_key parameter or PLUGIN_API_KEY env var)")
    if not self.region:
        errors.append("Region is required (region parameter or PLUGIN_REGION env var)")

    if errors:
        raise PluginValidationError(self.metadata.name, errors)
```

## Loading Environment Variables

### The load() Method Contract

The `load()` method must:

1. **Return dict[str, str]**: Map environment variable names to string values
2. **Not modify os.environ**: TripWire handles environment injection
3. **Raise PluginAPIError**: On failures (network errors, authentication, etc.)
4. **Be idempotent**: Multiple calls should return same result (if source unchanged)

### Loading Patterns

#### 1. Lazy-Load External Dependencies

```python
def __init__(self, url: str, token: str) -> None:
    # ... initialization code ...
    # Don't import boto3/requests/etc. in __init__
    self._client: Any | None = None

@property
def client(self) -> Any:
    """Get or create client (lazy initialization)."""
    if self._client is None:
        try:
            import boto3
        except ImportError as e:
            raise PluginAPIError(
                self.metadata.name,
                "load",
                original_error=e,
                message="boto3 library not installed. Install with: pip install boto3"
            ) from e

        self._client = boto3.client("secretsmanager", region_name=self.region)

    return self._client

def load(self) -> dict[str, str]:
    # Use self.client (triggers lazy initialization)
    response = self.client.get_secret_value(SecretId=self.secret_name)
    # ... rest of load logic ...
```

#### 2. Handle JSON Secrets

```python
import json

def load(self) -> dict[str, str]:
    # Fetch secret string from external source
    secret_string = self._fetch_secret()

    env_vars: dict[str, str] = {}

    try:
        # Try parsing as JSON
        secret_data = json.loads(secret_string)

        if isinstance(secret_data, dict):
            # JSON object - expand into individual env vars
            for key, value in secret_data.items():
                if isinstance(value, (str, int, float, bool)):
                    env_vars[key] = str(value)
                # Skip complex types (lists, dicts)
        else:
            # JSON but not object - use secret name as key
            env_vars[self._sanitize_key(self.secret_name)] = str(secret_data)

    except json.JSONDecodeError:
        # Not JSON - treat as plain string
        env_vars[self._sanitize_key(self.secret_name)] = secret_string

    return env_vars
```

#### 3. Sanitize Keys for Environment Variables

```python
def _sanitize_key(self, key: str) -> str:
    """Convert secret name to valid environment variable name.

    Args:
        key: Raw secret/key name

    Returns:
        Uppercase name with underscores (no hyphens or special chars)
    """
    # Replace non-alphanumeric with underscores
    sanitized = "".join(c if c.isalnum() else "_" for c in key)
    return sanitized.upper()

# Examples:
# "database-url" -> "DATABASE_URL"
# "myapp/api-key" -> "MYAPP_API_KEY"
# "arn:aws:secretsmanager:region:account:secret:name-xxxxx" -> "NAME"
```

#### 4. Filter Secrets by Prefix

```python
def load(self) -> dict[str, str]:
    """Load secrets with optional prefix filtering."""
    env_vars: dict[str, str] = {}

    # List all secrets
    all_secrets = self._list_all_secrets()

    for secret_name, secret_value in all_secrets.items():
        # Apply prefix filter if specified
        if self.secret_prefix and not secret_name.startswith(self.secret_prefix):
            continue

        # Remove prefix from environment variable name
        env_var_name = self._sanitize_key(secret_name)
        if self.secret_prefix:
            prefix_sanitized = self._sanitize_key(self.secret_prefix)
            if env_var_name.startswith(prefix_sanitized):
                env_var_name = env_var_name[len(prefix_sanitized):]

        env_vars[env_var_name] = secret_value

    return env_vars
```

#### 5. Handle Authentication Failures

```python
def load(self) -> dict[str, str]:
    try:
        # Verify authentication before loading
        if hasattr(self.client, "is_authenticated"):
            if not self.client.is_authenticated():
                raise PluginAPIError(
                    self.metadata.name,
                    "load",
                    message="Authentication failed. Token may be invalid or expired."
                )

        # Load secrets
        secrets = self.client.get_secrets()
        return self._parse_secrets(secrets)

    except Exception as e:
        if isinstance(e, PluginAPIError):
            raise
        raise PluginAPIError(
            self.metadata.name,
            "load",
            original_error=e,
            message=f"Failed to load secrets: {str(e)}"
        ) from e
```

## Error Handling

### Plugin Exception Hierarchy

TripWire provides a comprehensive exception hierarchy:

```python
from tripwire.plugins.errors import (
    PluginError,              # Base exception
    PluginNotFoundError,      # Plugin not registered
    PluginValidationError,    # Invalid configuration/metadata
    PluginAPIError,           # Error during load()/validate_config()
    PluginLoadError,          # Failed to import/initialize plugin
    PluginSecurityError,      # Security violation
    PluginVersionError,       # Incompatible TripWire version
)
```

### When to Use Each Exception

#### PluginValidationError

Use for invalid configuration or metadata:

```python
errors: list[str] = []
if not self.url:
    errors.append("URL is required")
if not self.url.startswith("https://"):
    errors.append("URL must use HTTPS")

if errors:
    raise PluginValidationError(self.metadata.name, errors)
```

#### PluginAPIError

Use for runtime errors in `load()` or other plugin methods:

```python
def load(self) -> dict[str, str]:
    try:
        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise PluginAPIError(
            self.metadata.name,
            "load",
            original_error=e,
            message=f"HTTP request failed: {str(e)}"
        ) from e
```

#### PluginLoadError

TripWire raises this when plugin import fails (you typically don't raise it):

```python
# TripWire raises this internally
# You raise PluginAPIError if external dependencies are missing
try:
    import hvac
except ImportError as e:
    raise PluginAPIError(
        self.metadata.name,
        "load",
        original_error=e,
        message="hvac library not installed. Install with: pip install hvac"
    ) from e
```

### Error Handling Best Practices

#### 1. Preserve Exception Chains

Always use `from e` to preserve exception context:

```python
# ✅ Good - preserves stack trace
try:
    data = self.client.fetch()
except ClientError as e:
    raise PluginAPIError(
        self.metadata.name,
        "load",
        original_error=e
    ) from e

# ❌ Bad - loses original exception context
try:
    data = self.client.fetch()
except ClientError as e:
    raise PluginAPIError(self.metadata.name, "load")
```

#### 2. Provide Actionable Error Messages

```python
# ✅ Good - tells user what to do
raise PluginAPIError(
    self.metadata.name,
    "load",
    message="boto3 library not installed. Install with: pip install boto3"
)

# ❌ Bad - unhelpful error
raise PluginAPIError(self.metadata.name, "load", message="Import failed")
```

#### 3. Don't Swallow Errors

```python
# ✅ Good - propagates plugin errors
def load(self) -> dict[str, str]:
    try:
        return self._fetch_secrets()
    except Exception as e:
        if isinstance(e, PluginAPIError):
            raise  # Re-raise plugin errors as-is
        raise PluginAPIError(
            self.metadata.name,
            "load",
            original_error=e
        ) from e

# ❌ Bad - silently swallows errors
def load(self) -> dict[str, str]:
    try:
        return self._fetch_secrets()
    except Exception:
        return {}  # Don't do this!
```

## Testing Your Plugin

### Basic Test Structure

```python
import pytest
from tripwire.plugins.errors import PluginValidationError, PluginAPIError
from my_plugin import HTTPConfigPlugin

class TestHTTPConfigPlugin:
    """Tests for HTTPConfigPlugin."""

    def test_valid_initialization(self):
        """Test creating plugin with valid configuration."""
        plugin = HTTPConfigPlugin(
            url="https://config.example.com/api/env",
            api_key="test-key",
            timeout=10
        )

        assert plugin.url == "https://config.example.com/api/env"
        assert plugin.api_key == "test-key"
        assert plugin.timeout == 10

    def test_initialization_validates_url(self):
        """Test that invalid URL raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            HTTPConfigPlugin(url="not-a-url")

        assert "http://" in str(exc_info.value) or "https://" in str(exc_info.value)

    def test_initialization_requires_url(self):
        """Test that missing URL raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            HTTPConfigPlugin(url="")

        assert "required" in str(exc_info.value).lower()

    def test_metadata_properties(self):
        """Test plugin metadata is correctly set."""
        plugin = HTTPConfigPlugin(url="https://example.com")

        assert plugin.metadata.name == "http-config"
        assert plugin.metadata.version == "1.0.0"
        assert plugin.metadata.author == "Your Name"
        assert "http" in plugin.metadata.tags

    def test_validate_config_with_valid_config(self):
        """Test validate_config accepts valid configuration."""
        plugin = HTTPConfigPlugin(url="https://example.com")

        config = {
            "url": "https://config.example.com",
            "api_key": "test-key",
            "timeout": 10
        }

        assert plugin.validate_config(config) is True

    def test_validate_config_rejects_missing_url(self):
        """Test validate_config rejects missing URL."""
        plugin = HTTPConfigPlugin(url="https://example.com")

        with pytest.raises(PluginValidationError) as exc_info:
            plugin.validate_config({})

        assert "url" in str(exc_info.value).lower()
```

### Testing load() with Mocking

```python
import pytest
from unittest.mock import Mock, patch
from my_plugin import HTTPConfigPlugin

class TestHTTPConfigPluginLoad:
    """Tests for HTTPConfigPlugin.load() method."""

    @patch("my_plugin.requests.get")
    def test_load_successful(self, mock_get):
        """Test successful loading of environment variables."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "sk_test_123",
            "DEBUG": True,
            "PORT": 8000
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Create plugin and load
        plugin = HTTPConfigPlugin(
            url="https://config.example.com",
            api_key="test-key"
        )
        env_vars = plugin.load()

        # Verify results
        assert env_vars["DATABASE_URL"] == "postgresql://localhost/db"
        assert env_vars["API_KEY"] == "sk_test_123"
        assert env_vars["DEBUG"] == "True"  # Converted to string
        assert env_vars["PORT"] == "8000"   # Converted to string

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://config.example.com"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"

    @patch("my_plugin.requests.get")
    def test_load_handles_http_errors(self, mock_get):
        """Test that HTTP errors raise PluginAPIError."""
        # Setup mock to raise exception
        mock_get.side_effect = requests.RequestException("Connection refused")

        plugin = HTTPConfigPlugin(url="https://config.example.com")

        with pytest.raises(PluginAPIError) as exc_info:
            plugin.load()

        assert "Connection refused" in str(exc_info.value)
        assert exc_info.value.plugin_name == "http-config"

    @patch("my_plugin.requests.get")
    def test_load_handles_invalid_json(self, mock_get):
        """Test that invalid JSON raises PluginAPIError."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        plugin = HTTPConfigPlugin(url="https://config.example.com")

        with pytest.raises(PluginAPIError) as exc_info:
            plugin.load()

        assert "json" in str(exc_info.value).lower()
```

### Integration Testing

```python
import pytest
from tripwire import TripWire
from my_plugin import HTTPConfigPlugin

@pytest.mark.integration
def test_plugin_integration_with_tripwire(mock_http_server):
    """Test plugin works with TripWire end-to-end."""
    # Setup mock HTTP server (using pytest fixture)
    mock_http_server.set_response({
        "DATABASE_URL": "postgresql://localhost/test",
        "API_KEY": "test-key-123"
    })

    # Create plugin pointing to mock server
    plugin = HTTPConfigPlugin(
        url=f"http://localhost:{mock_http_server.port}/config"
    )

    # Use with TripWire
    env = TripWire(sources=[plugin])

    # Verify environment variables loaded correctly
    DATABASE_URL: str = env.require("DATABASE_URL")
    API_KEY: str = env.require("API_KEY")

    assert DATABASE_URL == "postgresql://localhost/test"
    assert API_KEY == "test-key-123"
```

## Security Best Practices

### 1. Always Use HTTPS for Network Requests

```python
def __init__(self, url: str) -> None:
    # Enforce HTTPS
    if not url.startswith("https://"):
        raise PluginValidationError(
            self.metadata.name,
            ["URL must use HTTPS for security"]
        )

    # Allow opt-out with explicit parameter (for testing only)
    self.url = url
```

### 2. Validate URL Domains

```python
from urllib.parse import urlparse

def __init__(self, vault_url: str) -> None:
    parsed = urlparse(vault_url)

    # Whitelist allowed domains
    allowed_domains = [".vault.azure.net", ".vaultproject.io"]

    if not any(parsed.hostname.endswith(domain) for domain in allowed_domains):
        raise PluginValidationError(
            self.metadata.name,
            [f"Invalid domain. Must end with one of: {allowed_domains}"]
        )
```

### 3. Never Log Secrets

```python
def load(self) -> dict[str, str]:
    secrets = self._fetch_secrets()

    # ✅ Good - log count, not content
    logger.info(f"Loaded {len(secrets)} environment variables")

    # ❌ BAD - logs actual secrets!
    # logger.debug(f"Loaded secrets: {secrets}")

    return secrets
```

### 4. Implement Request Timeouts

```python
def load(self) -> dict[str, str]:
    # Always use timeouts to prevent hanging
    response = requests.get(
        self.url,
        timeout=self.timeout  # Default: 10 seconds
    )
```

### 5. Sanitize Input for Shell Commands

```python
# ❌ NEVER do this - shell injection vulnerability
import subprocess
subprocess.run(f"curl {self.url}", shell=True)

# ✅ Use proper libraries instead
import requests
response = requests.get(self.url)
```

### 6. Verify SSL Certificates

```python
def __init__(
    self,
    url: str,
    verify_ssl: bool = True  # Default to True
) -> None:
    self.url = url
    self.verify_ssl = verify_ssl

    if not verify_ssl:
        # Warn about security risk
        import warnings
        warnings.warn(
            "SSL verification disabled. This is insecure and should only be used for testing.",
            SecurityWarning
        )

def load(self) -> dict[str, str]:
    response = requests.get(
        self.url,
        verify=self.verify_ssl  # Verify SSL by default
    )
```

## Advanced Topics

### Supporting Multiple Authentication Methods

```python
from enum import Enum
from typing import Any

class AuthMethod(Enum):
    """Supported authentication methods."""
    API_KEY = "api_key"
    OAUTH = "oauth"
    BASIC = "basic"
    IAM_ROLE = "iam_role"

class MultiAuthPlugin(PluginInterface):
    def __init__(
        self,
        url: str,
        auth_method: AuthMethod,
        credentials: dict[str, Any]
    ) -> None:
        # ... initialization ...
        self.auth_method = auth_method
        self.credentials = credentials

    def _get_auth_headers(self) -> dict[str, str]:
        """Build authentication headers based on method."""
        if self.auth_method == AuthMethod.API_KEY:
            return {"Authorization": f"Bearer {self.credentials['api_key']}"}

        elif self.auth_method == AuthMethod.BASIC:
            import base64
            username = self.credentials["username"]
            password = self.credentials["password"]
            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {creds}"}

        elif self.auth_method == AuthMethod.IAM_ROLE:
            # Use AWS STS to get temporary credentials
            return self._get_iam_role_headers()

        else:
            raise PluginValidationError(
                self.metadata.name,
                [f"Unsupported auth method: {self.auth_method}"]
            )
```

### Implementing Caching

```python
from datetime import datetime, timedelta
from typing import Optional

class CachedPlugin(PluginInterface):
    def __init__(self, url: str, cache_ttl: int = 300) -> None:
        # ... initialization ...
        self.cache_ttl = cache_ttl  # seconds
        self._cache: Optional[dict[str, str]] = None
        self._cache_time: Optional[datetime] = None

    def load(self) -> dict[str, str]:
        """Load with caching support."""
        # Check if cache is valid
        if self._cache is not None and self._cache_time is not None:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < self.cache_ttl:
                return self._cache.copy()

        # Cache miss or expired - fetch fresh data
        env_vars = self._fetch_from_source()

        # Update cache
        self._cache = env_vars
        self._cache_time = datetime.now()

        return env_vars.copy()
```

### Batch Loading from Multiple Sources

```python
class BatchPlugin(PluginInterface):
    def __init__(self, secret_paths: list[str], **kwargs) -> None:
        # ... initialization ...
        self.secret_paths = secret_paths

    def load(self) -> dict[str, str]:
        """Load and merge secrets from multiple paths."""
        env_vars: dict[str, str] = {}

        for path in self.secret_paths:
            try:
                secrets = self._fetch_secrets_from_path(path)
                # Merge (later paths override earlier ones)
                env_vars.update(secrets)
            except Exception as e:
                # Log error but continue with other paths
                logger.warning(f"Failed to load from {path}: {e}")
                continue

        return env_vars
```

## Publishing Your Plugin

### 1. Package Structure

```
tripwire-http-config/
├── src/
│   └── tripwire_http_config/
│       ├── __init__.py
│       └── plugin.py
├── tests/
│   ├── __init__.py
│   └── test_plugin.py
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

### 2. pyproject.toml Configuration

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tripwire-http-config"
version = "1.0.0"
description = "Load TripWire environment variables from HTTP JSON endpoints"
authors = [{name = "Your Name", email = "you@example.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "tripwire>=0.10.0",
    "requests>=2.31.0",
]

[project.entry-points."tripwire.plugins"]
http-config = "tripwire_http_config:HTTPConfigPlugin"

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.5.0",
    "ruff>=0.1.0",
]
```

### 3. Entry Point Registration

The `[project.entry-points."tripwire.plugins"]` section registers your plugin for automatic discovery:

```toml
[project.entry-points."tripwire.plugins"]
http-config = "tripwire_http_config:HTTPConfigPlugin"
#  ^           ^                      ^
#  |           |                      |
#  |           |                      +--- Plugin class name
#  |           +--------------------------- Module path
#  +---------------------------------------- Plugin registry name
```

### 4. Publishing to PyPI

```bash
# Build package
python -m build

# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ tripwire-http-config

# Upload to PyPI
python -m twine upload dist/*
```

### 5. Documentation Requirements

Your README should include:

- **Installation**: `pip install tripwire-http-config`
- **Quick Start**: Basic usage example
- **Configuration**: All parameters and environment variables
- **Examples**: Common use cases
- **Authentication**: How to authenticate with your service
- **Error Handling**: Common errors and solutions
- **Security**: Security considerations and best practices
- **Contributing**: How others can contribute
- **License**: License information

### 6. Versioning Strategy

Follow Semantic Versioning:

- **Patch (1.0.1)**: Bug fixes, no API changes
- **Minor (1.1.0)**: New features, backward compatible
- **Major (2.0.0)**: Breaking changes

Update `min_tripwire_version` when using new TripWire features:

```python
metadata = PluginMetadata(
    name="http-config",
    version="2.0.0",
    # ...
    min_tripwire_version="0.11.0",  # Requires TripWire 0.11.0+
)
```

## Example Plugins Reference

TripWire includes three production-ready plugins you can reference:

### HashiCorp Vault Plugin

**Source**: `/src/tripwire/plugins/sources/vault.py`

**Features**:
- Supports KV v1 and KV v2 engines
- Token-based authentication
- Namespace support (Enterprise)
- Environment variable fallbacks

**Key Learnings**:
- Lazy-load external dependencies (`hvac`)
- Validate authentication before loading
- Handle different API versions gracefully

### AWS Secrets Manager Plugin

**Source**: `/src/tripwire/plugins/sources/aws_secrets.py`

**Features**:
- Multiple authentication methods (IAM, credentials, profiles)
- JSON secret parsing
- ARN support
- Automatic key sanitization

**Key Learnings**:
- Support multiple auth flows with precedence
- Parse JSON secrets into individual env vars
- Sanitize AWS ARNs to valid env var names

### Azure Key Vault Plugin

**Source**: `/src/tripwire/plugins/sources/azure_keyvault.py`

**Features**:
- DefaultAzureCredential support
- Secret prefix filtering
- Hyphen-to-underscore conversion
- Domain validation

**Key Learnings**:
- Validate URL formats with proper domain checking
- Convert naming conventions (hyphens → underscores)
- Handle disabled secrets gracefully

## Troubleshooting

### Common Issues

#### ImportError: Cannot import plugin dependency

**Problem**: External library not installed

**Solution**: Lazy-load dependencies and provide clear error messages

```python
try:
    import external_lib
except ImportError as e:
    raise PluginAPIError(
        self.metadata.name,
        "load",
        original_error=e,
        message="external_lib not installed. Install with: pip install external_lib"
    ) from e
```

#### PluginValidationError: Plugin metadata validation failed

**Problem**: Invalid plugin metadata

**Solution**: Ensure name is lowercase with hyphens/underscores, version follows semantic versioning

#### Plugin not discovered by TripWire

**Problem**: Entry point not registered correctly

**Solution**: Verify `pyproject.toml` entry point configuration and reinstall package

```bash
pip uninstall tripwire-your-plugin
pip install -e .  # Reinstall in editable mode
```

## Conclusion

You now have all the knowledge needed to create robust, secure TripWire plugins. Key takeaways:

1. **Implement the Protocol**: `metadata` property, `load()`, and `validate_config()`
2. **Validate Configuration**: Fail fast with clear error messages
3. **Handle Errors Properly**: Use appropriate exceptions with context
4. **Prioritize Security**: HTTPS, timeouts, no secret logging
5. **Test Thoroughly**: Unit tests, mocking, integration tests
6. **Document Well**: Clear README with examples

For questions or support, see:
- [TripWire Documentation](https://github.com/Daily-Nerd/TripWire/tree/main/docs)
- [Example Plugins](https://github.com/Daily-Nerd/TripWire/tree/main/src/tripwire/plugins/sources)
- [Plugin System Source](https://github.com/Daily-Nerd/TripWire/tree/main/src/tripwire/plugins)

Happy plugin development!
