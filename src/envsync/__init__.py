"""EnvSync - Smart environment variable management for Python.

EnvSync provides import-time validation of environment variables with type safety,
format validation, and team synchronization features.

Basic usage:
    >>> from envsync import env
    >>> API_KEY = env.require("API_KEY")
    >>> DEBUG = env.optional("DEBUG", default=False, type=bool)

Advanced usage:
    >>> from envsync import EnvSync
    >>> custom_env = EnvSync(env_file=".env.production")
    >>> db_url = custom_env.require("DATABASE_URL", format="postgresql")
"""

from envsync.core import EnvSync, env
from envsync.exceptions import (
    DriftError,
    EnvFileNotFoundError,
    EnvSyncError,
    MissingVariableError,
    SecretDetectedError,
    TypeCoercionError,
    ValidationError,
)
from envsync.validation import validator

__version__ = "0.1.2"

__all__ = [
    # Core
    "EnvSync",
    "env",
    # Exceptions
    "EnvSyncError",
    "MissingVariableError",
    "ValidationError",
    "TypeCoercionError",
    "EnvFileNotFoundError",
    "SecretDetectedError",
    "DriftError",
    # Utilities
    "validator",
]
