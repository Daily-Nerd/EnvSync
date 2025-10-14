"""Modern TripWire implementation using dependency injection and composition.

This module contains the TripWireV2 class which represents the next generation
of TripWire with a composable architecture following SOLID principles.

Design Patterns:
    - Dependency Injection: All components can be injected for flexibility
    - Strategy Pattern: Pluggable type inference strategies
    - Builder Pattern: Fluent validation pipeline construction
    - Factory Pattern: Default component creation when not injected
    - Chain of Responsibility: Composable validation rules
"""

from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path
from typing import Any, List, Optional, Sequence, TypeVar, Union, cast

from tripwire.core.inference import FrameInspectionStrategy, TypeInferenceEngine
from tripwire.core.loader import DotenvFileSource, EnvFileLoader, EnvSource
from tripwire.core.registry import VariableMetadata, VariableRegistry
from tripwire.core.validation_orchestrator import (
    ChoicesValidationRule,
    CustomValidationRule,
    FormatValidationRule,
    LengthValidationRule,
    PatternValidationRule,
    RangeValidationRule,
    ValidationContext,
    ValidationOrchestrator,
)
from tripwire.exceptions import (
    MissingVariableError,
    TripWireMultiValidationError,
    ValidationError,
)
from tripwire.security.secret import Secret
from tripwire.validation import ValidatorFunc, coerce_type

T = TypeVar("T")

# Import plugin system (lazy import to avoid circular dependencies)
_plugin_system_imported = False


class TripWireV2:
    """Modern environment variable management with composable architecture.

    TripWireV2 uses dependency injection and the strategy pattern to provide
    a flexible, testable, and extensible environment variable management system.

    Key Improvements over TripWire (legacy):
        - Dependency injection for all components
        - Composable validation pipeline
        - Pluggable type inference strategies
        - Cleaner separation of concerns
        - Enhanced testability
        - Better performance through component reuse

    Design Principles:
        - Single Responsibility: Each component has one job
        - Open/Closed: Open for extension, closed for modification
        - Dependency Inversion: Depends on abstractions, not concretions

    Example:
        Basic usage (uses default components):
            >>> env = TripWireV2()
            >>> PORT: int = env.require("PORT", min_val=1, max_val=65535)

        Advanced usage with multiple sources (RECOMMENDED for plugins):
            >>> from tripwire.plugins.sources import VaultEnvSource
            >>> dotenv = DotenvFileSource(Path(".env"))
            >>> vault = VaultEnvSource(url="https://vault.example.com", token="...")
            >>> env = TripWireV2(sources=[dotenv, vault])  # Pass sources directly
            >>> DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

        Advanced usage with custom loader (alternative pattern):
            >>> custom_loader = EnvFileLoader([
            ...     DotenvFileSource(Path(".env")),
            ...     DotenvFileSource(Path(".env.local"))
            ... ])
            >>> env = TripWireV2(loader=custom_loader)  # Pass loader, not sources
            >>> DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

        Dependency injection for testing:
            >>> mock_registry = MockRegistry()
            >>> mock_engine = MockInferenceEngine(returns=int)
            >>> env = TripWireV2(
            ...     registry=mock_registry,
            ...     inference_engine=mock_engine,
            ...     auto_load=False
            ... )
    """

    def __init__(
        self,
        env_file: Union[str, Path, None] = None,
        auto_load: bool = True,
        strict: bool = False,
        detect_secrets: bool = False,
        registry: Optional[VariableRegistry] = None,
        loader: Optional[EnvFileLoader] = None,
        inference_engine: Optional[TypeInferenceEngine] = None,
        sources: Optional[List[EnvSource]] = None,
        collect_errors: bool = True,
    ) -> None:
        """Initialize TripWireV2 with optional component injection.

        Args:
            env_file: Path to .env file (default: .env)
            auto_load: Whether to automatically load .env file on init
            strict: Whether to enable strict mode (errors on missing files)
            detect_secrets: Whether to detect potential secrets (deprecated, unused)
            registry: Custom variable registry (default: create new VariableRegistry)
            loader: Custom EnvFileLoader instance (mutually exclusive with sources)
                    Use when you need fine-grained control over loading behavior
            inference_engine: Custom type inference engine (default: FrameInspection)
            sources: List of EnvSource instances (e.g., DotenvFileSource, VaultEnvSource)
                     When provided, creates an EnvFileLoader internally
                     Mutually exclusive with loader parameter
                     RECOMMENDED for plugin usage - pass plugin instances here
            collect_errors: Whether to collect all validation errors and report together
                           (default: True for better UX, set False for legacy fail-fast behavior)

        Important Usage Patterns:
            Pattern 1 - Direct sources (RECOMMENDED):
                >>> vault = VaultEnvSource(url="...", token="...")
                >>> env = TripWire(sources=[vault])  # [green] Pass EnvSource instances

            Pattern 2 - Custom loader (advanced):
                >>> loader = EnvFileLoader([source1, source2])
                >>> env = TripWire(loader=loader)  # [green] Pass EnvFileLoader instance

            ANTI-PATTERN (will raise ValueError):
                >>> loader = EnvFileLoader([source1, source2])
                >>> env = TripWire(sources=[loader])  # [red] Wrong! loader is not EnvSource

        Design Pattern:
            Factory Pattern: Creates default instances if not provided
            Dependency Injection: Accepts custom components for flexibility

        Thread Safety:
            All injected components are expected to be thread-safe.
            Default components (VariableRegistry, etc.) are thread-safe by design.

        Example with plugin sources (OFFICIAL PLUGINS):
            >>> from tripwire import TripWire
            >>> from tripwire.plugins.sources import VaultEnvSource
            >>>
            >>> # Create plugin source (implements EnvSource protocol)
            >>> vault = VaultEnvSource(
            ...     url="https://vault.example.com",
            ...     token="hvs.xxx",
            ...     mount_point="secret",
            ...     path="myapp/config"
            ... )
            >>>
            >>> # Pass plugin to sources= (NOT loader=)
            >>> env = TripWire(sources=[vault])
            >>> DATABASE_URL = env.require("DATABASE_URL")

        Example with multiple sources (combining .env + plugins):
            >>> from tripwire import TripWire
            >>> from tripwire.core.loader import DotenvFileSource
            >>> from tripwire.plugins.sources import VaultEnvSource, AWSSecretsSource
            >>> from pathlib import Path
            >>>
            >>> # Create multiple sources
            >>> dotenv = DotenvFileSource(Path(".env"))
            >>> vault = VaultEnvSource(url="...", token="...", path="...")
            >>> aws = AWSSecretsSource(secret_name="myapp/prod", region="us-east-1")
            >>>
            >>> # TripWire loads in order (later sources override earlier)
            >>> env = TripWire(sources=[dotenv, vault, aws])
            >>> DATABASE_URL = env.require("DATABASE_URL")
        """
        # Core configuration
        self.env_file = Path(env_file) if env_file else Path(".env")
        self.strict = strict
        self.collect_errors = collect_errors

        # Backward compatibility attributes (deprecated but maintained for legacy tests)
        self.detect_secrets = detect_secrets  # Unused, kept for API compatibility
        self._loaded_files: List[Path] = []  # Track loaded .env files

        # Error collection state (thread-safe)
        self._validation_errors: List[ValidationError] = []
        self._error_lock = threading.Lock()  # Thread-safe error collection
        self._finalized = False  # Track if errors have been finalized

        # Dependency injection with sensible defaults (Factory Pattern)
        self._registry = registry if registry is not None else VariableRegistry()

        # Inference engine with pluggable strategy (Strategy Pattern)
        if inference_engine is None:
            strategy = FrameInspectionStrategy()
            self._inference_engine = TypeInferenceEngine(strategy)
        else:
            self._inference_engine = inference_engine

        # File loader with pluggable sources (Strategy Pattern)
        # Track whether sources were explicitly provided (for auto_load logic)
        _sources_provided = sources is not None

        # VALIDATION: Prevent common API misuse - passing EnvFileLoader to sources=
        if sources is not None:
            for idx, source in enumerate(sources):
                if isinstance(source, EnvFileLoader):
                    raise ValueError(
                        f"Invalid sources parameter: item at index {idx} is an EnvFileLoader, "
                        f"but sources= expects a list of EnvSource instances.\n\n"
                        f"COMMON MISTAKE:\n"
                        f"  [red] loader = EnvFileLoader([source1, source2])\n"
                        f"  [red] env = TripWire(sources=[loader])  # Wrong!\n\n"
                        f"CORRECT USAGE (choose one pattern):\n"
                        f"  [green] Pattern 1: Pass sources directly\n"
                        f"     env = TripWire(sources=[source1, source2])\n\n"
                        f"  [green] Pattern 2: Pass loader to loader= parameter\n"
                        f"     loader = EnvFileLoader([source1, source2])\n"
                        f"     env = TripWire(loader=loader)\n\n"
                        f"See documentation for more details."
                    )

        if loader is None:
            # Use provided sources or default to DotenvFileSource
            if sources is None:
                source_list: List[EnvSource] = [DotenvFileSource(self.env_file)]
            else:
                source_list = sources
            self._loader = EnvFileLoader(source_list, strict=self.strict)
        else:
            self._loader = loader

        # Auto-load if enabled
        # Logic:
        # 1. Custom loader injected OR custom sources provided → always load (they know what to load)
        # 2. Default .env source → only load if file exists (backward compatibility)
        if auto_load:
            if loader is not None or _sources_provided:
                # Custom loader/sources injected - always load (they know what to provide)
                self._loader.load_all()
                # Track loaded files from the loader
                loaded_files = self._loader.get_loaded_files()
                self._loaded_files.extend(loaded_files)
            elif self.env_file.exists():
                # Default .env source - only load if file exists
                self._loader.load_all()
                # Track loaded file for backward compatibility
                if self.env_file not in self._loaded_files:
                    self._loaded_files.append(self.env_file)

        # Register finalization hook for automatic error reporting
        # This ensures all collected errors are raised when module import completes
        if self.collect_errors:
            atexit.register(self._finalize_validation)

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

        This method orchestrates the entire variable retrieval and validation
        pipeline using injected components. The logic is ~50 lines vs 300+ in legacy.

        Pipeline:
            1. Type Inference: Infer type from annotation using inference engine
            2. Registration: Register variable metadata in registry
            3. Retrieval: Get value from environment with type coercion
            4. Validation: Build and execute validation pipeline
            5. Return: Validated and type-coerced value

        Args:
            name: Environment variable name
            type: Type to coerce to (default: infer from annotation, fallback to str)
            default: Default value if not set (makes it optional)
            description: Human-readable description for documentation
            format: Built-in format validator (email, url, uuid, ipv4, postgresql)
            pattern: Custom regex pattern to validate against
            choices: List of allowed values
            min_val: Minimum value (for int/float)
            max_val: Maximum value (for int/float)
            min_length: Minimum length (for str)
            max_length: Maximum length (for str)
            validator: Custom validator function
            secret: Mark as secret - wraps value in Secret[T] to prevent accidental exposure
                   through print(), logging, JSON serialization, etc.
            error_message: Custom error message for validation failures

        Returns:
            Validated and type-coerced value. If secret=True, returns Secret[T] wrapper.
            Use .get_secret_value() to access the unwrapped value when needed.

        Raises:
            MissingVariableError: If variable missing and no default provided
            ValidationError: If validation fails
            TypeCoercionError: If type coercion fails

        Example:
            >>> # Type inference from annotation
            >>> PORT: int = env.require("PORT", min_val=1, max_val=65535)

            >>> # Explicit type with validation
            >>> EMAIL: str = env.require("EMAIL", type=str, format="email")

            >>> # Secret values (wrapped in Secret[T])
            >>> from tripwire.security import Secret
            >>> API_KEY: Secret[str] = env.require("API_KEY", secret=True)
            >>> print(API_KEY)  # Output: **********
            >>> actual = API_KEY.get_secret_value()  # Unwrap when needed

            >>> # Optional with default
            >>> DEBUG: bool = env.require("DEBUG", default=False)
        """
        # Step 1: Type Inference (using injected engine)
        inferred_type = self._inference_engine.infer_or_default(explicit_type=type, default=str)

        # Step 2: Register variable for documentation generation
        self._register_variable(
            name=name,
            required=(default is None),
            type_=inferred_type,
            default=default,
            description=description,
            secret=secret,
        )

        # Step 3: Retrieve and coerce value
        raw_value = os.getenv(name)
        if raw_value is None:
            if default is not None:
                return default

            # Handle missing variable based on error collection mode
            if self.collect_errors:
                # Collect error and return placeholder (will be caught at finalization)
                error = ValidationError(
                    variable_name=name,
                    value=None,
                    reason="Required but not set",
                )
                with self._error_lock:
                    self._validation_errors.append(error)
                # Return type-appropriate placeholder (will fail at finalization anyway)
                return self._get_placeholder_value(inferred_type)  # type: ignore
            else:
                # Fail-fast mode
                raise MissingVariableError(name, description)

        # Type coercion with error collection
        try:
            if inferred_type is not str:
                coerced_value = coerce_type(raw_value, inferred_type, name)
            else:
                coerced_value = raw_value  # type: ignore[assignment]
        except Exception as e:
            # Type coercion failed
            if self.collect_errors:
                # Convert to ValidationError and collect
                error = ValidationError(
                    variable_name=name,
                    value=raw_value,
                    reason=f"Cannot coerce to {inferred_type.__name__}: {e}",
                )
                with self._error_lock:
                    self._validation_errors.append(error)
                return self._get_placeholder_value(inferred_type)  # type: ignore
            else:
                # Fail-fast mode
                raise

        # Step 4: Build validation pipeline (Builder Pattern)
        orchestrator = self._build_validation_pipeline(
            format=format,
            pattern=pattern,
            choices=choices,
            min_val=min_val,
            max_val=max_val,
            min_length=min_length,
            max_length=max_length,
            validator=validator,
            error_message=error_message,
        )

        # Step 5: Execute validation chain (Chain of Responsibility)
        context = ValidationContext(
            name=name,
            raw_value=raw_value,
            coerced_value=coerced_value,
            expected_type=inferred_type,
        )

        if self.collect_errors:
            # Enable error collection in orchestrator
            orchestrator.collect_errors = True
            orchestrator.validate(context)

            # Collect any errors from orchestrator
            if orchestrator.has_errors():
                with self._error_lock:
                    self._validation_errors.extend(orchestrator.get_collected_errors())
        else:
            # Fail-fast mode (legacy behavior)
            orchestrator.validate(context)

        # Step 6: Wrap in Secret if marked as secret
        if secret and raw_value is not None:
            # Only wrap non-None values in Secret
            # Import logging integration to auto-register secret
            try:
                from tripwire.security.logging import register_secret

                register_secret(str(coerced_value))  # Register for logging redaction
            except ImportError:
                pass  # Logging integration not available (shouldn't happen)

            # Wrap the coerced value in Secret wrapper
            # This prevents accidental exposure through print(), logging, JSON, etc.
            return cast(T, Secret(coerced_value))

        return cast(T, coerced_value)

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

        Convenience wrapper around require() with a default value.

        Args:
            name: Environment variable name
            default: Default value if not set (required for optional variables)
            type: Type to coerce to (default: infer from annotation)
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

        Example:
            >>> DEBUG: bool = env.optional("DEBUG", default=False)
            >>> LOG_LEVEL: str = env.optional("LOG_LEVEL", default="INFO")
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

    def load(self, env_file: Union[str, Path, None] = None, override: bool = False) -> None:
        """Load environment variables from .env file.

        Args:
            env_file: Path to .env file (default: use instance env_file)
            override: Whether to override existing environment variables

        Example:
            >>> env = TripWireV2(auto_load=False)
            >>> env.load(".env.production")
        """
        file_path = Path(env_file) if env_file else self.env_file
        source = DotenvFileSource(file_path, override=override)
        temp_loader = EnvFileLoader([source], strict=self.strict)
        temp_loader.load_all()

        # Track loaded file for backward compatibility
        if file_path not in self._loaded_files:
            self._loaded_files.append(file_path)

    def load_files(self, file_paths: List[Union[str, Path]], override: bool = False) -> None:
        """Load multiple .env files in order.

        Later files override earlier files if override=True.

        Args:
            file_paths: List of .env file paths to load
            override: Whether each file should override previous values

        Example:
            >>> env = TripWireV2(auto_load=False)
            >>> env.load_files([".env", ".env.local", ".env.production"])
        """
        sources: List[EnvSource] = [DotenvFileSource(Path(p), override=override) for p in file_paths]
        temp_loader = EnvFileLoader(sources, strict=self.strict)
        temp_loader.load_all()

    def get_registry(self) -> dict[str, dict[str, Any]]:
        """Get the registry of all registered variables.

        Returns:
            Registry dictionary in legacy format for backward compatibility

        Example:
            >>> registry = env.get_registry()
            >>> print(registry["PORT"])
            {'required': True, 'type': 'int', 'default': None, ...}
        """
        all_metadata = self._registry.get_all()
        legacy_format: dict[str, dict[str, Any]] = {}

        for name, metadata in all_metadata.items():
            legacy_format[name] = {
                "required": metadata.required,
                "type": metadata.type_name,
                "default": metadata.default,
                "description": metadata.description,
                "secret": metadata.secret,
            }

        return legacy_format

    # --- Simple Getter Methods (Backward Compatibility) ---

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

        Example:
            >>> api_key = env.get("API_KEY")
            >>> port = env.get("PORT", default=8000, type=int)
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

        Example:
            >>> if env.has("DEBUG"):
            ...     print("Debug mode enabled")
        """
        return name in os.environ

    def all(self) -> dict[str, str]:
        """Get all environment variables.

        Returns:
            Dictionary of all environment variables

        Example:
            >>> all_vars = env.all()
            >>> print(all_vars.keys())
        """
        return dict(os.environ)

    # --- Typed Convenience Methods (Backward Compatibility) ---

    def require_int(
        self,
        name: str,
        *,
        default: Optional[int] = None,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        description: Optional[str] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
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
            secret: Mark as secret
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
            secret=secret,
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
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
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
            secret: Mark as secret
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
            secret=secret,
            error_message=error_message,
        )

    def require_bool(
        self,
        name: str,
        *,
        default: Optional[bool] = None,
        description: Optional[str] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> bool:
        """Get required boolean environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            description: Variable description
            secret: Mark as secret
            error_message: Custom error message

        Returns:
            Boolean value from environment

        Example:
            >>> enable_feature = env.require_bool("ENABLE_FEATURE")
        """
        return self.require(
            name,
            type=bool,
            default=default,
            description=description,
            secret=secret,
            error_message=error_message,
        )

    def optional_bool(
        self,
        name: str,
        *,
        default: bool = False,
        description: Optional[str] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> bool:
        """Get optional boolean environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            description: Variable description
            secret: Mark as secret
            error_message: Custom error message

        Returns:
            Boolean value from environment or default

        Example:
            >>> debug = env.optional_bool("DEBUG", default=False)
        """
        return self.optional(
            name,
            type=bool,
            default=default,
            description=description,
            secret=secret,
            error_message=error_message,
        )

    def require_float(
        self,
        name: str,
        *,
        default: Optional[float] = None,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: Optional[str] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> float:
        """Get required float environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description
            validator: Custom validation function
            secret: Mark as secret
            error_message: Custom error message

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
            validator=validator,
            secret=secret,
            error_message=error_message,
        )

    def optional_float(
        self,
        name: str,
        *,
        default: float = 0.0,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: Optional[str] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> float:
        """Get optional float environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            description: Variable description
            validator: Custom validation function
            secret: Mark as secret
            error_message: Custom error message

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
            validator=validator,
            secret=secret,
            error_message=error_message,
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
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
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
            validator: Custom validation function
            secret: Mark as secret
            error_message: Custom error message

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
            validator=validator,
            secret=secret,
            error_message=error_message,
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
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
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
            validator: Custom validation function
            secret: Mark as secret
            error_message: Custom error message

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
            validator=validator,
            secret=secret,
            error_message=error_message,
        )

    # --- Private Helper Methods ---

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
            description: Variable description
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

    def _build_validation_pipeline(
        self,
        format: Optional[str],
        pattern: Optional[str],
        choices: Optional[List[str]],
        min_val: Optional[Union[int, float]],
        max_val: Optional[Union[int, float]],
        min_length: Optional[int],
        max_length: Optional[int],
        validator: Optional[ValidatorFunc],
        error_message: Optional[str],
    ) -> ValidationOrchestrator:
        """Build validation pipeline based on provided constraints.

        This method uses the Builder pattern to compose a validation chain.
        Each constraint adds a rule to the orchestrator.

        Design Pattern:
            Builder Pattern: Fluent API for constructing validation chains

        Args:
            format: Format validator name (email, url, etc.)
            pattern: Regex pattern to validate
            choices: List of allowed values
            min_val: Minimum numeric value
            max_val: Maximum numeric value
            min_length: Minimum string length
            max_length: Maximum string length
            validator: Custom validator function
            error_message: Custom error message

        Returns:
            ValidationOrchestrator with all applicable rules

        Note:
            Rules are added in this specific order to ensure consistent
            error reporting (format before pattern, etc.)
        """
        orchestrator = ValidationOrchestrator()

        # Format validation (first - most specific)
        if format:
            orchestrator.add_rule(FormatValidationRule(format, error_message))

        # Pattern validation (second - structural validation)
        if pattern:
            orchestrator.add_rule(PatternValidationRule(pattern, error_message))

        # Choices validation (third - value enumeration)
        if choices:
            orchestrator.add_rule(ChoicesValidationRule(choices, error_message))

        # Range validation (fourth - numeric constraints)
        if min_val is not None or max_val is not None:
            orchestrator.add_rule(RangeValidationRule(min_val, max_val, error_message))

        # Length validation (fifth - string constraints)
        if min_length is not None or max_length is not None:
            orchestrator.add_rule(LengthValidationRule(min_length, max_length, error_message))

        # Custom validator (last - application-specific logic)
        if validator:
            orchestrator.add_rule(CustomValidationRule(validator, error_message))

        return orchestrator

    def _get_placeholder_value(self, type_: type[Any]) -> Any:
        """Get placeholder value for a given type when collecting errors.

        This is used to return a value when validation fails but we're in error
        collection mode. The actual value doesn't matter since we'll raise an
        exception during finalization.

        Args:
            type_: Type to get placeholder for

        Returns:
            Placeholder value of the appropriate type
        """
        # Return type-appropriate placeholders
        if type_ is int:
            return 0
        elif type_ is float:
            return 0.0
        elif type_ is bool:
            return False
        elif type_ is str:
            return ""
        elif type_ is list:
            return []
        elif type_ is dict:
            return {}
        else:
            # For unknown types, return None
            return None

    def _finalize_validation(self) -> None:
        """Finalize validation by printing collected errors and setting exit code.

        This method is called automatically via atexit when the module finishes
        importing. If any validation errors were collected, it prints them to
        stderr and schedules the process to exit with code 1.

        Note:
            This method does NOT raise exceptions or call sys.exit() (to avoid
            "Exception ignored in atexit callback" messages). Instead, it prints
            errors cleanly and uses os._exit(1) which bypasses atexit handlers
            and exits immediately.

        Thread Safety:
            Uses lock to ensure thread-safe access to error list.
        """
        # Prevent double finalization
        if self._finalized:
            return

        with self._error_lock:
            self._finalized = True

            # No errors collected - success!
            if not self._validation_errors:
                return

            # Import sys here to avoid circular imports
            import sys

            # Create the appropriate error object for formatting
            error: Union[ValidationError, TripWireMultiValidationError]
            if len(self._validation_errors) == 1:
                # Single error - use its string representation
                error = self._validation_errors[0]
            else:
                # Multiple errors - use multi-error representation
                error = TripWireMultiValidationError(self._validation_errors)

            # Print to stderr (not raise) to avoid "Exception ignored" message
            print(f"\n{error}", file=sys.stderr)

            # Flush stderr to ensure message is displayed
            sys.stderr.flush()

            # Use os._exit(1) instead of sys.exit(1)
            # os._exit bypasses cleanup (including remaining atexit handlers) but
            # ensures clean exit without "Exception ignored" messages
            os._exit(1)

    def finalize(self) -> None:
        """Manually finalize validation (useful for testing or explicit control).

        Raises any collected validation errors. This method is for manual/explicit
        control and DOES raise exceptions (unlike the atexit callback which prints
        and exits cleanly).

        Example:
            >>> env = TripWireV2()
            >>> DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
            >>> SECRET_KEY: str = env.require("SECRET_KEY", min_length=32)
            >>> env.finalize()  # Explicitly check for errors now

        Raises:
            ValidationError: If single validation error was collected
            TripWireMultiValidationError: If multiple validation errors were collected
        """
        # Prevent double finalization
        if self._finalized:
            return

        with self._error_lock:
            self._finalized = True

            # No errors collected - success!
            if not self._validation_errors:
                return

            # Manual finalization - raise exceptions normally
            # (This is different from atexit finalization which prints and exits)
            if len(self._validation_errors) == 1:
                raise self._validation_errors[0]

            # Multiple errors - raise multi-error exception
            raise TripWireMultiValidationError(self._validation_errors)

    def has_validation_errors(self) -> bool:
        """Check if any validation errors have been collected.

        Returns:
            True if validation errors exist, False otherwise
        """
        with self._error_lock:
            return len(self._validation_errors) > 0

    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of collected validation errors without raising.

        Useful for testing or custom error handling.

        Returns:
            List of ValidationError instances collected so far
        """
        with self._error_lock:
            return self._validation_errors.copy()

    @classmethod
    def discover_plugins(cls) -> None:
        """Discover and register plugins from entry points.

        This method scans for plugins registered via setuptools entry points
        in the 'tripwire.plugins' group and registers them with the PluginRegistry.

        Plugins can then be retrieved using PluginRegistry.get_plugin() and used
        as sources when creating TripWire instances.

        Example:
            >>> from tripwire import TripWire
            >>> from tripwire.plugins import PluginRegistry
            >>>
            >>> # Discover all installed plugins
            >>> TripWire.discover_plugins()
            >>>
            >>> # Get and use a plugin
            >>> VaultPlugin = PluginRegistry.get_plugin("vault")
            >>> vault = VaultPlugin(url="...", token="...")
            >>> env = TripWire(sources=[vault])

        Note:
            This method is typically called once at application startup.
            Plugins registered in pyproject.toml entry points will be
            automatically discovered and validated.
        """
        global _plugin_system_imported
        if not _plugin_system_imported:
            # Lazy import to avoid circular dependencies
            from tripwire.core.plugin_system import PluginRegistry

            _plugin_system_imported = True
        else:
            from tripwire.core.plugin_system import PluginRegistry

        PluginRegistry.discover_plugins()


# Module-level singleton instance for convenient usage
# Uses default components - users can create custom instances with DI
env = TripWireV2()


# Alias for backward compatibility and clarity during migration
TripWire = TripWireV2
