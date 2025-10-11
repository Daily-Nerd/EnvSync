"""Type inference from annotations using strategy pattern.

This module provides type inference from variable annotations in calling code.
It uses frame introspection to detect type hints and cache results for performance.
"""

from __future__ import annotations

import inspect
import linecache
import threading
from abc import ABC, abstractmethod
from typing import (
    Callable,
    Dict,
    Optional,
    Tuple,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

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
        computed_value: Optional[type] = compute_fn()

        # SET: Store in cache with LRU eviction
        if len(_TYPE_INFERENCE_CACHE) >= _CACHE_MAX_SIZE:
            # Evict oldest entry (first item in dict, since Python 3.7+ preserves insertion order)
            _TYPE_INFERENCE_CACHE.pop(next(iter(_TYPE_INFERENCE_CACHE)))

        _TYPE_INFERENCE_CACHE[cache_key] = computed_value
        return computed_value


class TypeInferenceStrategy(ABC):
    """Abstract strategy for type inference.

    Different strategies can be implemented:
    - Frame inspection (current implementation)
    - AST analysis (future)
    - Type stub parsing (future)

    Design Pattern: Strategy pattern for pluggable inference methods
    """

    @abstractmethod
    def infer_type(self) -> Optional[type]:
        """Infer type from context.

        Returns:
            Inferred type or None if cannot determine
        """
        pass


class FrameInspectionStrategy(TypeInferenceStrategy):
    """Infer type by inspecting caller's stack frame for annotations.

    This strategy uses Python's inspect module to walk up the call stack
    and find type annotations. It's safe, doesn't use eval(), and caches
    results for performance.

    Thread Safety:
        Uses global locks to prevent race conditions in multi-threaded apps.

    Security:
        - No eval() or exec() - uses safe get_type_hints()
        - Read-only frame inspection
        - Caching prevents resource exhaustion
    """

    def __init__(self) -> None:
        """Initialize frame inspection strategy.

        The strategy automatically determines which module file to skip
        based on its own location.
        """
        # Use this module's file as the boundary to skip
        self.inference_module_file = __file__.replace(".pyc", ".py")

    def infer_type(self) -> Optional[type]:
        """Infer type from caller's variable annotation.

        Uses stack introspection to find the calling frame and extract
        the type annotation from the assignment target.

        Returns:
            Inferred type or None if cannot determine

        Thread Safety:
            Uses global lock to prevent concurrent frame inspection
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
                caller_frame = current_frame.f_back
                if caller_frame is None:
                    return None

                # Skip frames within inference module
                while caller_frame is not None:
                    frame_file = caller_frame.f_code.co_filename
                    # Skip frames within the inference module
                    if frame_file != self.inference_module_file:
                        break
                    caller_frame = caller_frame.f_back

                # Final None check after loop
                if caller_frame is None:
                    return None

                # Now we're at the first frame outside inference module
                # But we might need to go up more frames to find the annotation
                # Keep walking up frames until we find one with an annotation
                # (handles wrapper functions like require() → optional() → helper())
                max_depth = 5  # Limit depth to prevent infinite loops
                depth = 0
                while caller_frame is not None and depth < max_depth:
                    filename = caller_frame.f_code.co_filename
                    lineno = caller_frame.f_lineno
                    line = linecache.getline(filename, lineno).strip()

                    # If we found an annotation, stop here
                    if ":" in line and "=" in line:
                        break

                    # Try parent frame
                    caller_frame = caller_frame.f_back
                    depth += 1

                # If we exhausted all frames, return None
                if caller_frame is None:
                    return None

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
                                    return self._extract_type_from_hint(hint)

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

                    # Check for Union[T, U, ...] pattern (extract first type)
                    if type_str.startswith("Union[") and type_str.endswith("]"):
                        # Extract first type from Union[int, str] -> "int"
                        inner = type_str[6:-1].strip()
                        first_type = inner.split(",")[0].strip()
                        return type_map.get(first_type, None)

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

    def _extract_type_from_hint(self, hint: type) -> Optional[type]:
        """Extract actual type from type hint.

        Handles:
        - Optional[T] -> T
        - Union types -> first non-None type
        - Generic types (List[T], Dict[K,V]) -> base type
        - Basic types -> return as-is

        Args:
            hint: Type hint to extract from

        Returns:
            Extracted type or None
        """
        # Handle Optional[T] and Union types
        origin = get_origin(hint)
        if origin is Union:
            args = get_args(hint)
            # Filter out NoneType
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                first_arg = non_none_args[0]
                # Type narrowing: ensure we return a type, not Any
                if isinstance(first_arg, type):
                    return first_arg
                return None

        # Return the hint if it's a basic type
        if hint in (int, float, bool, str, list, dict):
            return hint

        # Handle generic types (List[T], Dict[K,V]) -> return base type
        if origin in (list, dict):
            # Type narrowing: origin must be a type if it matches list or dict
            if isinstance(origin, type):
                return origin

        # Unknown/unsupported type
        return None


class TypeInferenceEngine:
    """Orchestrates type inference using a configurable strategy.

    This engine provides a clean interface for type inference while allowing
    different strategies to be plugged in.

    Design Pattern:
        - Strategy pattern for inference method
        - Facade pattern for simplified interface

    Example:
        >>> strategy = FrameInspectionStrategy()
        >>> engine = TypeInferenceEngine(strategy)
        >>> inferred_type = engine.infer_or_default(None, default=str)
        >>> # Returns: int (if annotation is int:), or str (if no annotation)
    """

    def __init__(self, strategy: TypeInferenceStrategy) -> None:
        """Initialize type inference engine.

        Args:
            strategy: Type inference strategy to use
        """
        self.strategy = strategy

    def infer_or_default(
        self,
        explicit_type: Optional[type],
        default: type = str,
    ) -> type:
        """Infer type from annotation or use explicit/default type.

        Precedence:
        1. Explicit type parameter (if provided)
        2. Inferred type from annotation
        3. Default type (usually str)

        Args:
            explicit_type: Explicitly provided type (takes precedence)
            default: Default type if inference fails

        Returns:
            Type to use for validation/coercion
        """
        # 1. Explicit type takes precedence
        if explicit_type is not None:
            return explicit_type

        # 2. Try to infer from annotation
        inferred = self.strategy.infer_type()
        if inferred is not None:
            return inferred

        # 3. Fall back to default
        return default
