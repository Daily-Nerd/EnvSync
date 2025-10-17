"""TripWire - Catch config errors before they explode.

TripWire provides import-time validation of environment variables with type safety,
format validation, secret detection, and git audit capabilities.

Basic usage:
    >>> from tripwire import env
    >>> API_KEY = env.require("API_KEY")
    >>> DEBUG = env.optional("DEBUG", default=False, type=bool)

Advanced usage:
    >>> from tripwire import TripWire
    >>> custom_env = TripWire(env_file=".env.production")
    >>> db_url = custom_env.require("DATABASE_URL", format="postgresql")

Version 0.9.0+ uses the modern TripWireV2 implementation by default.
The legacy implementation is available as TripWireLegacy for backward compatibility.
"""

# Legacy implementation (deprecated, will be removed in v1.0.0)
from tripwire._core_legacy import TripWireLegacy

# Modern implementation (v0.9.0+)
from tripwire.core import TripWire, TripWireV2, env
from tripwire.exceptions import (
    DriftError,
    EnvFileNotFoundError,
    MissingVariableError,
    SecretDetectedError,
    TripWireError,
    TypeCoercionError,
    ValidationError,
)
from tripwire.validation import validator

__version__ = "0.13.0"

__all__ = [
    # Core (Modern Implementation)
    "TripWire",  # Modern implementation (TripWireV2 alias, default)
    "TripWireV2",  # Modern implementation (explicit name)
    "env",  # Module-level singleton (uses modern implementation)
    # Legacy Implementation (Deprecated)
    "TripWireLegacy",  # Legacy implementation (deprecated, removed in v1.0.0)
    # Exceptions
    "TripWireError",
    "MissingVariableError",
    "ValidationError",
    "TypeCoercionError",
    "EnvFileNotFoundError",
    "SecretDetectedError",
    "DriftError",
    # Utilities
    "validator",
]
