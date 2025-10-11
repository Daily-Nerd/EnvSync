"""Core components for TripWire.

This package contains the refactored core components following SOLID principles:
- registry: Thread-safe variable registration and metadata storage
- loader: Environment file loading with source abstraction
- inference: Type inference from annotations using strategy pattern
- validation_orchestrator: Validation rule chain with Chain of Responsibility pattern
"""

# Import legacy TripWire class from _core_legacy module
# This maintains backward compatibility while we refactor
from tripwire._core_legacy import TripWire, env

# Import components from refactored modules
from tripwire.core.inference import (
    FrameInspectionStrategy,
    TypeInferenceEngine,
    TypeInferenceStrategy,
)
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
    ValidationRule,
)

__all__ = [
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
    # Legacy exports for backward compatibility
    "TripWire",
    "env",
]
