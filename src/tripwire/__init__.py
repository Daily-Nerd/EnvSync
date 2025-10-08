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
"""

from tripwire.core import TripWire, env
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

__version__ = "0.2.0-rc1"

__all__ = [
    # Core
    "TripWire",
    "env",
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
