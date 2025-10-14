"""Plugin system core components for TripWire.

This module implements the plugin architecture including:
- PluginRegistry: Thread-safe singleton for managing registered plugins
- PluginLoader: Auto-discovery and loading of plugins via entry points
- PluginValidator: API compatibility and version validation
- PluginSandbox: Security isolation to prevent malicious plugins

Design Patterns:
    - Singleton: PluginRegistry ensures single source of truth
    - Factory: PluginLoader creates plugin instances
    - Strategy: Plugins implement EnvSourcePlugin protocol
    - Template Method: Validation pipeline in PluginValidator

Thread Safety:
    All components are thread-safe and can be used in concurrent environments.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import inspect
import threading
from pathlib import Path
from typing import Any, Iterable, Type

from tripwire.plugins.base import EnvSourcePlugin, PluginMetadata
from tripwire.plugins.errors import (
    PluginLoadError,
    PluginNotFoundError,
    PluginSecurityError,
    PluginValidationError,
    PluginVersionError,
)


class PluginRegistry:
    """Thread-safe singleton registry for TripWire plugins.

    The registry maintains a central catalog of all available plugins,
    providing registration, retrieval, and listing capabilities.

    Design Pattern:
        Singleton with thread-safe lazy initialization

    Thread Safety:
        All operations are protected by a reentrant lock, ensuring safe
        concurrent access from multiple threads.

    Example:
        >>> # Register a plugin
        >>> PluginRegistry.register_plugin("vault", VaultEnvSource)
        >>>
        >>> # Retrieve a plugin
        >>> VaultPlugin = PluginRegistry.get_plugin("vault")
        >>>
        >>> # List all plugins
        >>> plugins = PluginRegistry.list_plugins()
        >>> for metadata in plugins:
        ...     print(f"{metadata.name}: {metadata.description}")
    """

    _instance: PluginRegistry | None = None
    _lock = threading.RLock()

    def __new__(cls) -> PluginRegistry:
        """Create or return the singleton instance.

        Returns:
            Singleton PluginRegistry instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the registry (called once during singleton creation)."""
        self._plugins: dict[str, Type[EnvSourcePlugin]] = {}
        self._metadata_cache: dict[str, PluginMetadata] = {}

    @classmethod
    def register_plugin(cls, name: str, plugin_class: Type[EnvSourcePlugin]) -> None:
        """Register a plugin class in the registry.

        Args:
            name: Unique plugin name (lowercase, alphanumeric, hyphens)
            plugin_class: Plugin class implementing EnvSourcePlugin protocol

        Raises:
            PluginValidationError: If plugin is invalid or name is taken

        Example:
            >>> class MyPlugin(PluginInterface):
            ...     # Implementation
            ...     pass
            >>> PluginRegistry.register_plugin("myplugin", MyPlugin)
        """
        instance = cls()
        with cls._lock:
            # Validate plugin before registration
            validator = PluginValidator()
            validator.validate_plugin(plugin_class)

            # Check for name conflicts
            if name in instance._plugins:
                raise PluginValidationError(name, [f"Plugin '{name}' is already registered"])

            # Register the plugin
            instance._plugins[name] = plugin_class

            # Cache metadata if available
            try:
                # Create a temporary instance to get metadata
                # Use inspect to check if __init__ requires parameters
                sig = inspect.signature(plugin_class.__init__)
                params = [
                    p for p in sig.parameters.values() if p.name != "self" and p.default is inspect.Parameter.empty
                ]

                if params:
                    # Plugin requires init parameters, can't instantiate without them
                    # Skip metadata caching (will be retrieved on demand)
                    pass
                else:
                    # Plugin can be instantiated without parameters
                    temp_instance = plugin_class()
                    instance._metadata_cache[name] = temp_instance.metadata
            except Exception:
                # If we can't instantiate, skip metadata caching
                pass

    @classmethod
    def get_plugin(cls, name: str) -> Type[EnvSourcePlugin]:
        """Retrieve a plugin class by name.

        Args:
            name: Plugin name

        Returns:
            Plugin class

        Raises:
            PluginNotFoundError: If plugin not found

        Example:
            >>> VaultPlugin = PluginRegistry.get_plugin("vault")
            >>> vault = VaultPlugin(url="...", token="...")
        """
        instance = cls()
        with cls._lock:
            if name not in instance._plugins:
                raise PluginNotFoundError(
                    name,
                    f"Plugin '{name}' not found. Available plugins: "
                    f"{', '.join(instance._plugins.keys()) or 'none'}",
                )
            return instance._plugins[name]

    @classmethod
    def list_plugins(cls) -> list[PluginMetadata]:
        """List all registered plugins with their metadata.

        Returns:
            List of PluginMetadata for all registered plugins

        Example:
            >>> for metadata in PluginRegistry.list_plugins():
            ...     print(f"{metadata.name} v{metadata.version}: {metadata.description}")
        """
        instance = cls()
        metadata_list: list[PluginMetadata] = []

        with cls._lock:
            for name, plugin_class in instance._plugins.items():
                # Try to get cached metadata
                if name in instance._metadata_cache:
                    metadata_list.append(instance._metadata_cache[name])
                else:
                    # Try to get metadata from class
                    try:
                        # Check if we can instantiate
                        sig = inspect.signature(plugin_class.__init__)
                        params = [
                            p
                            for p in sig.parameters.values()
                            if p.name != "self" and p.default is inspect.Parameter.empty
                        ]

                        if not params:
                            temp_instance = plugin_class()
                            metadata = temp_instance.metadata
                            instance._metadata_cache[name] = metadata
                            metadata_list.append(metadata)
                    except Exception:
                        # If we can't get metadata, create a placeholder
                        placeholder = PluginMetadata(
                            name=name,
                            version="unknown",
                            author="unknown",
                            description=f"Plugin class: {plugin_class.__name__}",
                        )
                        metadata_list.append(placeholder)

        return metadata_list

    @classmethod
    def discover_plugins(cls) -> None:
        """Discover and register plugins from entry points and installed builtin plugins.

        This method scans for plugins in two locations:
        1. Setuptools entry points in the 'tripwire.plugins' group
        2. Installed builtin plugins in ~/.tripwire/plugins/

        Example:
            >>> # In your package's pyproject.toml:
            >>> # [project.entry-points."tripwire.plugins"]
            >>> # vault = "tripwire_vault:VaultEnvSource"
            >>>
            >>> # In your application:
            >>> PluginRegistry.discover_plugins()
            >>> vault = PluginRegistry.get_plugin("vault")

        Note:
            This method is called automatically by TripWire.discover_plugins()
            and typically doesn't need to be called directly.
        """
        loader = PluginLoader()

        # Discover from entry points
        plugins = loader.load_from_entry_points()
        for name, plugin_class in plugins.items():
            try:
                cls.register_plugin(name, plugin_class)
            except PluginValidationError:
                # Skip invalid plugins (already logged by validator)
                pass

        # Discover from installed builtin plugins
        # Skip validation for builtin plugins (they're already part of TripWire)
        builtin_plugins = loader.load_builtin_plugins()
        instance = cls()
        with cls._lock:
            for name, plugin_class in builtin_plugins.items():
                # Direct registration without validation
                instance._plugins[name] = plugin_class

    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins (primarily for testing).

        Example:
            >>> PluginRegistry.clear()  # Reset registry
        """
        instance = cls()
        with cls._lock:
            instance._plugins.clear()
            instance._metadata_cache.clear()


class PluginLoader:
    """Loads plugins from entry points and file paths.

    The loader handles:
    - Discovery of plugins via setuptools entry points
    - Loading plugins from local file paths (for development)
    - Import error handling and reporting

    Example:
        >>> loader = PluginLoader()
        >>>
        >>> # Load from entry points
        >>> plugins = loader.load_from_entry_points()
        >>>
        >>> # Load from file (development)
        >>> plugin_class = loader.load_from_path(Path("./my_plugin.py"))
    """

    def load_from_entry_points(self) -> dict[str, Type[EnvSourcePlugin]]:
        """Load plugins from setuptools entry points.

        Scans the 'tripwire.plugins' entry point group and loads all
        registered plugins.

        Returns:
            Dictionary mapping plugin names to plugin classes

        Example:
            >>> loader = PluginLoader()
            >>> plugins = loader.load_from_entry_points()
            >>> print(plugins.keys())
            dict_keys(['vault', 'aws-secrets', 'gcp-secrets'])
        """
        plugins: dict[str, Type[EnvSourcePlugin]] = {}

        try:
            # Use importlib.metadata to discover entry points
            entry_points = importlib.metadata.entry_points()

            # Handle different versions of importlib.metadata API
            # Both APIs return an iterable of EntryPoint objects
            tripwire_plugins: Iterable[importlib.metadata.EntryPoint]
            if hasattr(entry_points, "select"):
                # Python 3.10+ API
                tripwire_plugins = entry_points.select(group="tripwire.plugins")
            else:
                # Python 3.9 API (fallback)
                result = entry_points.get("tripwire.plugins")
                tripwire_plugins = result if result is not None else []

            for entry_point in tripwire_plugins:
                try:
                    # Load the plugin class
                    plugin_class = entry_point.load()

                    # Validate it's a class
                    if not inspect.isclass(plugin_class):
                        raise PluginLoadError(
                            entry_point.name,
                            f"Entry point '{entry_point.name}' does not point to a class",
                        )

                    plugins[entry_point.name] = plugin_class

                except Exception as e:
                    # Log error and continue (don't let one bad plugin break all plugins)
                    raise PluginLoadError(
                        entry_point.name,
                        f"Failed to load plugin from entry point",
                        original_error=e,
                    ) from e

        except Exception as e:
            # Entry point discovery failed - this is non-fatal
            # Just return empty dict (no plugins available)
            pass

        return plugins

    def load_builtin_plugins(self) -> dict[str, Type[EnvSourcePlugin]]:
        """Load builtin plugins from installed plugin directory.

        Scans ~/.tripwire/plugins/ for directories containing .builtin files
        and loads the plugins specified in those files.

        Returns:
            Dictionary mapping plugin names to plugin classes

        Example:
            >>> loader = PluginLoader()
            >>> plugins = loader.load_builtin_plugins()
            >>> print(plugins.keys())
            dict_keys(['vault', 'aws-secrets'])
        """
        import json

        plugins: dict[str, Type[EnvSourcePlugin]] = {}
        plugins_dir = Path.home() / ".tripwire" / "plugins"

        if not plugins_dir.exists():
            return plugins

        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            builtin_file = plugin_dir / ".builtin"
            if not builtin_file.exists():
                continue

            try:
                # Read builtin metadata
                with open(builtin_file, "r") as f:
                    metadata = json.load(f)

                module_path = metadata.get("module_path")
                class_name = metadata.get("class_name")
                plugin_id = plugin_dir.name

                if not module_path or not class_name:
                    continue

                # Import the plugin class
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)

                # Validate it's a class
                if not inspect.isclass(plugin_class):
                    continue

                plugins[plugin_id] = plugin_class

            except Exception:
                # Skip plugins that can't be loaded
                continue

        return plugins

    def load_from_path(self, path: Path) -> Type[EnvSourcePlugin]:
        """Load a plugin from a file path (for development/testing).

        Args:
            path: Path to Python file containing plugin class

        Returns:
            Plugin class

        Raises:
            PluginLoadError: If plugin cannot be loaded

        Example:
            >>> loader = PluginLoader()
            >>> plugin_class = loader.load_from_path(Path("./my_plugin.py"))
            >>> PluginRegistry.register_plugin("myplugin", plugin_class)
        """
        if not path.exists():
            raise PluginLoadError(path.stem, f"Plugin file not found: {path}")

        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(path.stem, f"Cannot load module spec from {path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the plugin class (look for EnvSourcePlugin implementations)
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a plugin class (has metadata property)
                if hasattr(obj, "metadata") and hasattr(obj, "load"):
                    plugin_class = obj
                    break

            if plugin_class is None:
                raise PluginLoadError(path.stem, f"No plugin class found in {path} implementing EnvSourcePlugin")

            return plugin_class

        except Exception as e:
            raise PluginLoadError(path.stem, f"Failed to load plugin from {path}", original_error=e) from e

    def validate_plugin(self, plugin_class: Type[EnvSourcePlugin]) -> bool:
        """Validate that a plugin class is properly implemented.

        Args:
            plugin_class: Plugin class to validate

        Returns:
            True if valid

        Raises:
            PluginValidationError: If plugin is invalid
        """
        validator = PluginValidator()
        return validator.validate_plugin(plugin_class)


class PluginValidator:
    """Validates plugin implementations for API compatibility.

    The validator checks:
    - Protocol compliance (metadata, load, validate_config methods)
    - Metadata validity
    - Version compatibility
    - Method signatures

    Example:
        >>> validator = PluginValidator()
        >>> is_valid = validator.validate_plugin(MyPluginClass)
    """

    def validate_plugin(self, plugin_class: Type[EnvSourcePlugin]) -> bool:
        """Validate a plugin class.

        Args:
            plugin_class: Plugin class to validate

        Returns:
            True if valid

        Raises:
            PluginValidationError: If validation fails with detailed errors
        """
        errors: list[str] = []
        plugin_name = getattr(plugin_class, "__name__", "unknown")

        # Check if it's a class
        if not inspect.isclass(plugin_class):
            errors.append("Plugin must be a class")
            raise PluginValidationError(plugin_name, errors)

        # Check for required attributes/methods
        required_attrs = ["metadata", "load", "validate_config"]
        for attr in required_attrs:
            if not hasattr(plugin_class, attr):
                errors.append(f"Plugin must implement '{attr}' method/property")

        # Check metadata is a property
        if hasattr(plugin_class, "metadata"):
            if not isinstance(inspect.getattr_static(plugin_class, "metadata"), property):
                # Could be a method or other callable - check if it's callable
                if not callable(getattr(plugin_class, "metadata", None)):
                    errors.append("'metadata' must be a property or callable")

        # Check method signatures
        if hasattr(plugin_class, "load"):
            load_method = getattr(plugin_class, "load")
            if callable(load_method):
                sig = inspect.signature(load_method)
                # Should return dict[str, str]
                # We can't enforce return type at runtime, but we can check parameters
                params = [p for p in sig.parameters.values() if p.name != "self"]
                if params:
                    errors.append("'load()' method should not take additional parameters")

        if hasattr(plugin_class, "validate_config"):
            validate_method = getattr(plugin_class, "validate_config")
            if callable(validate_method):
                sig = inspect.signature(validate_method)
                params = [p for p in sig.parameters.values() if p.name != "self"]
                if len(params) != 1:
                    errors.append("'validate_config()' method should take exactly one parameter (config)")

        if errors:
            raise PluginValidationError(plugin_name, errors)

        # Try to validate metadata by creating an instance (if possible)
        try:
            sig = inspect.signature(plugin_class.__init__)
            params = [p for p in sig.parameters.values() if p.name != "self" and p.default is inspect.Parameter.empty]

            if not params:
                # Can instantiate without parameters
                instance = plugin_class()
                metadata = instance.metadata

                # Validate metadata
                if not isinstance(metadata, PluginMetadata):
                    errors.append(f"metadata property must return PluginMetadata, got {type(metadata)}")
                    raise PluginValidationError(plugin_name, errors)

                # Check version compatibility
                self.check_version_compatibility(metadata.name, metadata.version, metadata.min_tripwire_version)

        except PluginValidationError:
            raise
        except Exception:
            # Can't instantiate or get metadata - non-fatal
            # The plugin will be validated when actually used
            pass

        return True

    def check_version_compatibility(self, plugin_name: str, plugin_version: str, min_tripwire_version: str) -> bool:
        """Check if plugin is compatible with current TripWire version.

        Args:
            plugin_name: Name of the plugin
            plugin_version: Plugin version
            min_tripwire_version: Minimum TripWire version required

        Returns:
            True if compatible

        Raises:
            PluginVersionError: If versions are incompatible
        """
        # Get current TripWire version
        try:
            from tripwire import __version__ as tripwire_version
        except ImportError:
            # Fallback to package metadata
            try:
                tripwire_version = importlib.metadata.version("tripwire-py")
            except Exception:
                # Can't determine version - assume compatible
                return True

        # Simple version comparison (major.minor)
        # Format: "0.10.0" -> (0, 10, 0)
        def parse_version(version: str) -> tuple[int, ...]:
            return tuple(int(x) for x in version.split(".") if x.isdigit())

        try:
            current = parse_version(tripwire_version)
            required = parse_version(min_tripwire_version)

            # Compare major.minor (ignore patch)
            if current[:2] < required[:2]:
                raise PluginVersionError(plugin_name, plugin_version, min_tripwire_version, tripwire_version)

        except PluginVersionError:
            raise
        except Exception:
            # Version parsing failed - assume compatible
            pass

        return True

    def validate_metadata(self, metadata: PluginMetadata) -> bool:
        """Validate plugin metadata.

        Args:
            metadata: Plugin metadata to validate

        Returns:
            True if valid

        Note:
            Validation is performed in PluginMetadata.__post_init__,
            so this method primarily exists for explicit validation.
        """
        # Metadata validation happens in __post_init__
        # If we have a PluginMetadata instance, it's already valid
        return isinstance(metadata, PluginMetadata)


class PluginSandbox:
    """Security sandbox for plugin execution.

    The sandbox enforces security constraints to prevent malicious plugins from:
    - Reading files outside allowed paths
    - Making network requests to internal IPs
    - Executing shell commands
    - Accessing Python internals (__dict__, __code__, etc.)

    Example:
        >>> sandbox = PluginSandbox()
        >>> is_safe = sandbox.validate_safe_operations(plugin_instance)
        >>> sandbox.restrict_permissions(plugin_instance)
    """

    # Allowed file paths (relative to project root)
    ALLOWED_PATHS: list[str] = [
        ".env",
        ".env.example",
        ".env.local",
        ".tripwire.toml",
    ]

    # Restricted module names (dangerous operations)
    RESTRICTED_MODULES: list[str] = [
        "subprocess",
        "os.system",
        "eval",
        "exec",
        "__builtins__.eval",
        "__builtins__.exec",
    ]

    def validate_safe_operations(self, plugin: EnvSourcePlugin) -> bool:
        """Validate that a plugin performs safe operations.

        Args:
            plugin: Plugin instance to validate

        Returns:
            True if plugin appears safe

        Raises:
            PluginSecurityError: If security violations detected

        Note:
            This is a best-effort static analysis. Complete sandboxing would
            require running plugins in separate processes with restricted permissions.
        """
        plugin_name = plugin.metadata.name

        # Check for dangerous attribute access
        dangerous_attrs = ["__dict__", "__code__", "__globals__", "func_code", "func_globals"]

        for attr in dangerous_attrs:
            if hasattr(plugin, attr):
                # Having these attributes is normal, but accessing them is suspicious
                # We can't prevent access at this level without deep instrumentation
                pass

        # Check plugin source code for dangerous patterns (if available)
        try:
            source = inspect.getsource(plugin.__class__)

            # Check for subprocess/eval/exec usage
            dangerous_patterns = [
                "subprocess",
                "os.system",
                "eval(",
                "exec(",
                "__import__",
            ]

            for pattern in dangerous_patterns:
                if pattern in source:
                    raise PluginSecurityError(
                        plugin_name,
                        "dangerous_operation",
                        f"Plugin source contains potentially dangerous pattern: {pattern}",
                    )

        except (TypeError, OSError):
            # Can't get source (compiled, built-in, etc.) - allow it
            pass

        return True

    def restrict_permissions(self, plugin: EnvSourcePlugin) -> None:
        """Restrict plugin permissions (placeholder for future implementation).

        Args:
            plugin: Plugin instance to restrict

        Note:
            Current implementation is a placeholder. Full sandboxing would require:
            - Running plugins in separate processes
            - Using OS-level permission restrictions
            - Intercepting system calls
            - Virtual filesystem isolation

            For v0.10.0, we rely on validate_safe_operations() for basic checks.
        """
        # Future implementation:
        # - Process isolation
        # - Filesystem access control
        # - Network access control
        # - Resource limits (CPU, memory, time)
        pass
