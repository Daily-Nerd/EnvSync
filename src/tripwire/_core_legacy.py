"""Core TripWire functionality (LEGACY IMPLEMENTATION).

This module contains the legacy TripWire class and is deprecated in favor
of the modern implementation in tripwire.core.

.. deprecated:: 0.9.0
   The legacy TripWire implementation in _core_legacy is deprecated.
   Use tripwire.TripWire (which now uses the modern TripWireV2 implementation).
   This legacy module will be removed in v1.0.0.

For new code, use::

    from tripwire import TripWire  # Modern implementation (TripWireV2)
    env = TripWire()

If you need the legacy implementation explicitly::

    from tripwire import TripWireLegacy
    env = TripWireLegacy()
"""

import inspect
import linecache
import os
import threading
import warnings
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from dotenv import load_dotenv

from tripwire.core.registry import VariableMetadata, VariableRegistry
from tripwire.exceptions import (
    EnvFileNotFoundError,
    MissingVariableError,
    ValidationError,
)
from tripwire.validation import (
    ValidatorFunc,
    coerce_type,
    get_validator,
    validate_choices,
    validate_pattern,
    validate_range,
)

T = TypeVar("T")

# Thread-safe lock for frame inspection to prevent race conditions
# in multi-threaded environments (web servers, async workers, etc.)
_FRAME_INFERENCE_LOCK = threading.Lock()

# Separate lock for cache operations to prevent race conditions
# (CHECK-USE-SET pattern requires atomic operations)
_TYPE_INFERENCE_CACHE_LOCK = threading.Lock()

# Performance optimization: Cache type inference results to avoid expensive operations
# Key: (filename, line_number) -> Value: inferred type (or None if inference failed)
# This provides significant speedup when same variable location is accessed multiple times
# Implements LRU eviction to prevent unbounded memory growth
_TYPE_INFERENCE_CACHE: Dict[Tuple[str, int], Optional[type]] = {}

# Maximum cache entries before LRU eviction (prevents unbounded memory growth)
_CACHE_MAX_SIZE: int = 1000


def _cache_get_or_compute(
    cache_key: Tuple[str, int],
    compute_fn: Callable[[], Optional[type]],
) -> Optional[type]:
    """Thread-safe cache lookup with LRU eviction.

    This function implements the CHECK-USE-SET pattern atomically using a lock
    to prevent race conditions where multiple threads could miss the cache
    simultaneously and duplicate expensive computations.

    Args:
        cache_key: Cache key (filename, line_number)
        compute_fn: Function to compute value if cache miss

    Returns:
        Cached or computed type, or None if computation fails

    Security:
        - Thread-safe: Uses lock to prevent race conditions
        - Memory-safe: Implements LRU eviction at _CACHE_MAX_SIZE entries
        - No unbounded growth: Evicts oldest entry when full
    """
    with _TYPE_INFERENCE_CACHE_LOCK:
        # CHECK: Try cache first (within lock to prevent TOCTOU)
        if cache_key in _TYPE_INFERENCE_CACHE:
            # Move to end for LRU (most recently used)
            value = _TYPE_INFERENCE_CACHE.pop(cache_key)
            _TYPE_INFERENCE_CACHE[cache_key] = value
            return value

        # COMPUTE: Cache miss, compute the value
        computed_value = compute_fn()

        # SET: Store in cache with LRU eviction
        if len(_TYPE_INFERENCE_CACHE) >= _CACHE_MAX_SIZE:
            # Evict oldest entry (first item in dict, since Python 3.7+ preserves insertion order)
            _TYPE_INFERENCE_CACHE.pop(next(iter(_TYPE_INFERENCE_CACHE)))

        _TYPE_INFERENCE_CACHE[cache_key] = computed_value
        return computed_value


class TripWire:
    """Main class for environment variable management with validation (DEPRECATED).

    .. deprecated:: 0.9.0
       TripWire from _core_legacy is deprecated. Import from tripwire instead:

           from tripwire import TripWire  # Uses modern TripWireV2 implementation

       If you specifically need the legacy implementation:

           from tripwire import TripWireLegacy

       This legacy implementation will be removed in v1.0.0.

    This is the legacy monolithic implementation. The modern implementation
    (TripWireV2) offers better architecture, performance, and testability.
    """

    def __init__(
        self,
        env_file: Union[str, Path, None] = None,
        auto_load: bool = True,
        strict: bool = False,
        detect_secrets: bool = False,
    ) -> None:
        """Initialize TripWire (DEPRECATED).

        Args:
            env_file: Path to .env file to load (default: .env)
            auto_load: Whether to automatically load .env file on init
            strict: Whether to enable strict mode (warnings become errors)
            detect_secrets: Whether to detect potential secrets
        """
        # Emit deprecation warning
        warnings.warn(
            "TripWire from tripwire._core_legacy is deprecated. "
            "Use 'from tripwire import TripWire' which now uses the modern TripWireV2 implementation. "
            "This legacy implementation will be removed in v1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )

        self.env_file = Path(env_file) if env_file else Path(".env")
        self.strict = strict
        self.detect_secrets = detect_secrets
        self._loaded_files: List[Path] = []
        self._registry = VariableRegistry()

        if auto_load and self.env_file.exists():
            self.load(self.env_file)

    def _infer_type_from_annotation(self) -> Optional[type]:
        """Infer type from caller's variable annotation.

        Uses stack introspection to find the calling frame and extract
        the type annotation from the assignment target. This method uses
        safe type inference techniques to avoid security risks.

        Thread Safety:
            Uses a global lock to prevent race conditions when multiple threads
            simultaneously inspect frames. Cache operations use a separate lock
            to prevent CHECK-USE-SET race conditions.

        Returns:
            Inferred type or None if cannot determine
        """
        # Thread safety: Acquire lock to prevent concurrent frame inspection
        with _FRAME_INFERENCE_LOCK:
            current_frame = inspect.currentframe()
            # Type safety: Handle None case explicitly
            if current_frame is None:
                return None

            caller_frame = None
            try:
                # Find the first frame outside the TripWire module
                # This handles both direct require() calls and indirect optional() calls
                # Type assertion: f_back returns Optional[FrameType]
                caller_frame = current_frame.f_back
                if caller_frame is None:
                    return None

                tripwire_module_file = __file__.replace(".pyc", ".py")

                # Type narrowing: Explicitly check for None in loop
                while caller_frame is not None:
                    frame_file = caller_frame.f_code.co_filename
                    # Skip frames within the TripWire module
                    if frame_file != tripwire_module_file:
                        break
                    caller_frame = caller_frame.f_back

                # Final None check after loop
                if caller_frame is None:
                    return None

                # Type narrowing: From here, caller_frame is guaranteed non-None
                # mypy understands this control flow

                # Performance: Use thread-safe cache with LRU eviction
                filename = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno
                cache_key = (filename, lineno)

                # Define computation function for cache miss
                def compute_type() -> Optional[type]:
                    """Compute type from frame (called only on cache miss)."""
                    # Get module for type hints (safest approach)
                    module = inspect.getmodule(caller_frame)
                    if module:
                        # Try get_type_hints first (safe and recommended)
                        try:
                            hints = get_type_hints(module)
                        except Exception:
                            # Fallback if type hints can't be resolved
                            hints = {}

                        # Parse source line to find variable name
                        line = linecache.getline(filename, lineno).strip()

                        # Extract variable name from pattern: VAR_NAME: type = ...
                        if ":" in line and "=" in line:
                            var_part = line.split("=")[0].strip()
                            if ":" in var_part:
                                var_name = var_part.split(":")[0].strip()

                                # Check if we have type hint for this variable
                                if var_name in hints:
                                    hint = hints[var_name]

                                    # Handle Optional[T] -> extract T
                                    origin = get_origin(hint)
                                    if origin is Union:
                                        args = get_args(hint)
                                        # Filter out NoneType (using proper comparison)
                                        non_none_args = [arg for arg in args if arg is not type(None)]
                                        if non_none_args:
                                            # Type narrowing: Ensure we return a type, not Any
                                            inferred_type = non_none_args[0]
                                            if isinstance(inferred_type, type):
                                                return inferred_type

                                    # Return the hint if it's a basic type
                                    if hint in (int, float, bool, str, list, dict):
                                        # Type assertion: These are guaranteed to be types
                                        result_type: type = hint
                                        return result_type

                                    # Handle generic types (List[T], Dict[K,V]) -> return base type
                                    if origin in (list, dict):
                                        # Type assertion: origin is guaranteed to be a type here
                                        result_type_origin: type = origin
                                        return result_type_origin

                                    # If it's already a type, return it
                                    if isinstance(hint, type):
                                        return hint

                    # Fallback: Parse annotation string with safe type mapping (NO EVAL)
                    line = linecache.getline(filename, lineno).strip()

                    # Simple pattern matching for: VAR_NAME: type = ...
                    if ":" not in line or "=" not in line:
                        return None

                    var_part = line.split("=")[0].strip()
                    if ":" not in var_part:
                        return None

                    # Extract the type annotation string
                    type_str = var_part.split(":", 1)[1].strip()

                    # Safe mapping for basic types only (NO EVAL!)
                    type_map = {
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "str": str,
                        "list": list,
                        "dict": dict,
                    }

                    # Check for Optional[T] pattern (extract T)
                    if type_str.startswith("Optional[") and type_str.endswith("]"):
                        inner_type = type_str[9:-1].strip()
                        return type_map.get(inner_type, None)

                    # Check for direct type match
                    return type_map.get(type_str, None)

                # Use thread-safe cache with LRU eviction
                return _cache_get_or_compute(cache_key, compute_type)

            finally:
                # Proper cleanup of frame references to prevent memory leaks
                if caller_frame is not None:
                    del caller_frame
                if current_frame is not None:
                    del current_frame

    def load(self, env_file: Union[str, Path, None] = None, override: bool = False) -> None:
        """Load environment variables from .env file.

        Args:
            env_file: Path to .env file (default: use instance env_file)
            override: Whether to override existing environment variables

        Raises:
            EnvFileNotFoundError: If env file doesn't exist and is required
        """
        file_path = Path(env_file) if env_file else self.env_file

        if not file_path.exists():
            if self.strict:
                raise EnvFileNotFoundError(str(file_path))
            return

        load_dotenv(file_path, override=override)
        self._loaded_files.append(file_path)

    def load_files(self, file_paths: List[Union[str, Path]], override: bool = False) -> None:
        """Load multiple .env files in order.

        Args:
            file_paths: List of .env file paths to load
            override: Whether each file should override previous values
        """
        for file_path in file_paths:
            self.load(file_path, override=override)

    def require(
        self,
        name: str,
        *,
        type: Optional[type[T]] = None,  # noqa: A002
        default: Optional[T] = None,
        description: Optional[str] = None,
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> T:
        """Get a required environment variable with validation.

        This method retrieves an environment variable and validates it according
        to the specified constraints. If validation fails, an exception is raised
        at import time, preventing the application from starting with invalid config.

        Args:
            name: Environment variable name
            type: Type to coerce to (default: infer from annotation, fallback to str)
            default: Default value if not set (makes it optional)
            description: Human-readable description
            format: Built-in format validator (email, url, uuid, ipv4, postgresql)
            pattern: Custom regex pattern to validate against
            choices: List of allowed values
            min_val: Minimum value (for int/float)
            max_val: Maximum value (for int/float)
            min_length: Minimum length (for str)
            max_length: Maximum length (for str)
            validator: Custom validator function
            secret: Mark as secret (for secret detection)
            error_message: Custom error message

        Returns:
            Validated and type-coerced value

        Raises:
            MissingVariableError: If variable is missing and no default
            ValidationError: If variable fails validation
            TypeCoercionError: If type coercion fails
        """
        # Infer type if not explicitly provided
        if type is None:
            inferred_type = self._infer_type_from_annotation()
            type = inferred_type if inferred_type is not None else str

        # Register variable for documentation generation
        self._register_variable(
            name=name,
            required=(default is None),
            type_=type,
            default=default,
            description=description,
            secret=secret,
        )

        # Get raw value from environment
        raw_value = os.getenv(name)

        # Handle missing value
        if raw_value is None:
            if default is not None:
                return default
            raise MissingVariableError(name, description)

        # Type coercion
        if type is not str:
            value = coerce_type(raw_value, type, name)  # type: ignore[type-var]
        else:
            value = raw_value  # type: ignore[assignment]

        # Format validation
        if format:
            validator_func = get_validator(format)
            if validator_func is None:
                raise ValidationError(
                    name,
                    raw_value,
                    error_message or f"Unknown format validator: {format}",
                    expected=format,
                )
            if not validator_func(raw_value):
                raise ValidationError(
                    name,
                    raw_value,
                    error_message or f"Invalid format: expected {format}",
                    expected=format,
                )

        # Pattern validation
        if pattern and not validate_pattern(raw_value, pattern):
            raise ValidationError(
                name,
                raw_value,
                error_message or f"Does not match pattern: {pattern}",
                expected=pattern,
            )

        # Choices validation
        if choices and not validate_choices(raw_value, choices):
            raise ValidationError(
                name,
                raw_value,
                error_message or f"Not in allowed choices: {choices}",
                expected=f"One of: {', '.join(choices)}",
            )

        # Range validation (for numeric types)
        if isinstance(value, (int, float)) and (min_val is not None or max_val is not None):
            if not validate_range(value, min_val, max_val):
                range_desc = []
                if min_val is not None:
                    range_desc.append(f">= {min_val}")
                if max_val is not None:
                    range_desc.append(f"<= {max_val}")
                raise ValidationError(
                    name,
                    value,
                    error_message or f"Out of range: must be {' and '.join(range_desc)}",
                    expected=" and ".join(range_desc),
                )

        # Length validation (for strings)
        if isinstance(value, str) and (min_length is not None or max_length is not None):
            length = len(value)
            if min_length is not None and length < min_length:
                raise ValidationError(
                    name,
                    value,
                    error_message or f"String too short: must be at least {min_length} characters",
                    expected=f"min length: {min_length}",
                )
            if max_length is not None and length > max_length:
                raise ValidationError(
                    name,
                    value,
                    error_message or f"String too long: must be at most {max_length} characters",
                    expected=f"max length: {max_length}",
                )

        # Custom validator
        if validator and not validator(value):
            raise ValidationError(
                name,
                value,
                error_message or "Failed custom validation",
            )

        return value

    def optional(
        self,
        name: str,
        *,
        default: T,
        type: Optional[type[T]] = None,  # noqa: A002
        description: Optional[str] = None,
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> T:
        """Get an optional environment variable with validation.

        This is a convenience wrapper around require() with a default value.

        Args:
            name: Environment variable name
            default: Default value if not set
            type: Type to coerce to (default: infer from annotation, fallback to str)
            description: Human-readable description
            format: Built-in format validator
            pattern: Custom regex pattern
            choices: List of allowed values
            min_val: Minimum value (for int/float)
            max_val: Maximum value (for int/float)
            min_length: Minimum length (for str)
            max_length: Maximum length (for str)
            validator: Custom validator function
            secret: Mark as secret
            error_message: Custom error message

        Returns:
            Validated and type-coerced value or default
        """
        return self.require(
            name,
            type=type,
            default=default,
            description=description,
            format=format,
            pattern=pattern,
            choices=choices,
            min_val=min_val,
            max_val=max_val,
            min_length=min_length,
            max_length=max_length,
            validator=validator,
            secret=secret,
            error_message=error_message,
        )

    def get(
        self,
        name: str,
        default: Optional[T] = None,
        type: type[T] = str,  # type: ignore[assignment]  # noqa: A002
    ) -> Optional[T]:
        """Get an environment variable with optional type coercion.

        Simple getter without validation (for backwards compatibility).

        Args:
            name: Environment variable name
            default: Default value if not set
            type: Type to coerce to

        Returns:
            Value or default
        """
        raw_value = os.getenv(name)
        if raw_value is None:
            return default

        if type is str or type is None:
            return raw_value  # type: ignore[return-value]

        return coerce_type(raw_value, type, name)  # type: ignore[type-var]

    def has(self, name: str) -> bool:
        """Check if environment variable exists.

        Args:
            name: Environment variable name

        Returns:
            True if variable is set
        """
        return name in os.environ

    def all(self) -> Dict[str, str]:
        """Get all environment variables.

        Returns:
            Dictionary of all environment variables
        """
        return dict(os.environ)

    # Typed convenience methods (for cases without annotations)

    def require_int(
        self,
        name: str,
        *,
        default: Optional[int] = None,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        description: Optional[str] = None,
        validator: Optional[Callable[[int], bool]] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """Get required integer environment variable.

        Convenience method equivalent to env.require(name, type=int, ...).
        Use when you can't use type annotations (e.g., in dictionaries).

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description
            validator: Custom validation function
            error_message: Custom error message

        Returns:
            Integer value from environment

        Example:
            >>> port = env.require_int("PORT", min_val=1, max_val=65535)
        """
        return self.require(
            name,
            type=int,
            default=default,
            min_val=min_val,
            max_val=max_val,
            description=description,
            validator=validator,
            error_message=error_message,
        )

    def optional_int(
        self,
        name: str,
        *,
        default: int = 0,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        description: Optional[str] = None,
        validator: Optional[Callable[[int], bool]] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """Get optional integer environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description
            validator: Custom validation function
            error_message: Custom error message

        Returns:
            Integer value from environment or default

        Example:
            >>> max_connections = env.optional_int("MAX_CONNECTIONS", default=100)
        """
        return self.optional(
            name,
            type=int,
            default=default,
            min_val=min_val,
            max_val=max_val,
            description=description,
            validator=validator,
            error_message=error_message,
        )

    def require_bool(
        self,
        name: str,
        *,
        default: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Get required boolean environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            description: Variable description

        Returns:
            Boolean value from environment

        Example:
            >>> enable_feature = env.require_bool("ENABLE_FEATURE")
        """
        return self.require(name, type=bool, default=default, description=description)

    def optional_bool(
        self,
        name: str,
        *,
        default: bool = False,
        description: Optional[str] = None,
    ) -> bool:
        """Get optional boolean environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            description: Variable description

        Returns:
            Boolean value from environment or default

        Example:
            >>> debug = env.optional_bool("DEBUG", default=False)
        """
        return self.optional(name, type=bool, default=default, description=description)

    def require_float(
        self,
        name: str,
        *,
        default: Optional[float] = None,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: Optional[str] = None,
    ) -> float:
        """Get required float environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description

        Returns:
            Float value from environment

        Example:
            >>> timeout = env.require_float("TIMEOUT")
        """
        return self.require(
            name,
            type=float,
            default=default,
            min_val=min_val,
            max_val=max_val,
            description=description,
        )

    def optional_float(
        self,
        name: str,
        *,
        default: float = 0.0,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: Optional[str] = None,
    ) -> float:
        """Get optional float environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description

        Returns:
            Float value from environment or default

        Example:
            >>> rate_limit = env.optional_float("RATE_LIMIT", default=10.5)
        """
        return self.optional(
            name,
            type=float,
            default=default,
            min_val=min_val,
            max_val=max_val,
            description=description,
        )

    def require_str(
        self,
        name: str,
        *,
        default: Optional[str] = None,
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        description: Optional[str] = None,
    ) -> str:
        """Get required string environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            format: Built-in format validator
            pattern: Custom regex pattern
            choices: List of allowed values
            min_length: Minimum length
            max_length: Maximum length
            description: Variable description

        Returns:
            String value from environment

        Example:
            >>> api_key = env.require_str("API_KEY", min_length=32)
        """
        return self.require(
            name,
            type=str,
            default=default,
            format=format,
            pattern=pattern,
            choices=choices,
            min_length=min_length,
            max_length=max_length,
            description=description,
        )

    def optional_str(
        self,
        name: str,
        *,
        default: str = "",
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        description: Optional[str] = None,
    ) -> str:
        """Get optional string environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            format: Built-in format validator
            pattern: Custom regex pattern
            choices: List of allowed values
            min_length: Minimum length
            max_length: Maximum length
            description: Variable description

        Returns:
            String value from environment or default

        Example:
            >>> log_level = env.optional_str("LOG_LEVEL", default="INFO")
        """
        return self.optional(
            name,
            type=str,
            default=default,
            format=format,
            pattern=pattern,
            choices=choices,
            min_length=min_length,
            max_length=max_length,
            description=description,
        )

    def _register_variable(
        self,
        name: str,
        required: bool,
        type_: type[Any],
        default: Any,
        description: Optional[str],
        secret: bool,
    ) -> None:
        """Register a variable for documentation generation.

        Args:
            name: Variable name
            required: Whether variable is required
            type_: Variable type
            default: Default value
            description: Description
            secret: Whether variable is secret
        """
        metadata = VariableMetadata(
            name=name,
            required=required,
            type_name=type_.__name__,
            default=default,
            description=description,
            secret=secret,
        )
        self._registry.register(metadata)

    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the registry of all registered variables.

        Returns:
            Registry dictionary in legacy format for backward compatibility
        """
        # Convert VariableRegistry to legacy dict format for backward compatibility
        all_metadata = self._registry.get_all()
        legacy_format: Dict[str, Dict[str, Any]] = {}

        for name, metadata in all_metadata.items():
            legacy_format[name] = {
                "required": metadata.required,
                "type": metadata.type_name,
                "default": metadata.default,
                "description": metadata.description,
                "secret": metadata.secret,
            }

        return legacy_format


# Module-level singleton instance for convenient usage (DEPRECATED)
# Use: from tripwire import env (which now uses TripWireV2)
env = TripWire()

# Alias for backward compatibility
TripWireLegacy = TripWire
