"""Core components for TripWire.

This package contains the refactored core components following SOLID principles:
- registry: Thread-safe variable registration and metadata storage
- loader: Environment file loading with source abstraction
- inference: Type inference from annotations using strategy pattern
- validation_orchestrator: Validation rule chain with Chain of Responsibility pattern

Version 0.9.0+:
- TripWire and env now use the modern TripWireV2 implementation
- TripWireLegacy is available for backward compatibility (deprecated)
"""

# Import components from refactored modules
from tripwire.core.inference import (
    FrameInspectionStrategy,
    TypeInferenceEngine,
    TypeInferenceStrategy,
)
from tripwire.core.loader import DotenvFileSource, EnvFileLoader, EnvSource

# Plugin system (v0.10.0+)
from tripwire.core.plugin_system import (
    PluginLoader,
    PluginRegistry,
    PluginSandbox,
    PluginValidator,
)
from tripwire.core.registry import VariableMetadata, VariableRegistry

# Import modern TripWire implementation (v0.9.0+)
from tripwire.core.tripwire_v2 import TripWire, TripWireV2, env
from tripwire.core.validation_orchestrator import (
    ChoicesValidationRule,
    CustomValidationRule,
    FormatValidationRule,
    LengthValidationRule,
    PatternValidationRule,
    RangeValidationRule,
    ValidationContext,
    ValidationOrchestrator,
    ValidationRule,
)

__all__ = [
    # Modern TripWire implementation (v0.9.0+)
    "TripWire",  # Modern implementation (alias for TripWireV2)
    "TripWireV2",  # Modern implementation (explicit name)
    "env",  # Module-level singleton (uses modern implementation)
    # Refactored components
    "VariableMetadata",
    "VariableRegistry",
    "EnvSource",
    "DotenvFileSource",
    "EnvFileLoader",
    "TypeInferenceStrategy",
    "FrameInspectionStrategy",
    "TypeInferenceEngine",
    "ValidationContext",
    "ValidationRule",
    "ValidationOrchestrator",
    "FormatValidationRule",
    "PatternValidationRule",
    "ChoicesValidationRule",
    "RangeValidationRule",
    "LengthValidationRule",
    "CustomValidationRule",
    # Plugin system (v0.10.0+)
    "PluginRegistry",
    "PluginLoader",
    "PluginValidator",
    "PluginSandbox",
]
