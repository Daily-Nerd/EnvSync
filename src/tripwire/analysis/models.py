"""Data models for usage analysis and dependency tracking.

This module defines the core data structures used to represent environment
variable declarations, usages, and analysis results.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class VariableDeclaration:
    """Tracks where an environment variable was declared.

    Attributes:
        name: Python variable name (e.g., "DATABASE_URL")
        env_var: Environment variable name (e.g., "DATABASE_URL")
        file_path: Path to file where variable was declared
        line_number: Line number of declaration
        is_required: Whether variable is required (vs optional)
        type_annotation: Python type annotation if present (e.g., "str", "int")
        validator: Validator/format specification (e.g., "postgresql", "email")
    """

    name: str
    env_var: str
    file_path: Path
    line_number: int
    is_required: bool
    type_annotation: Optional[str] = None
    validator: Optional[str] = None


@dataclass
class VariableUsage:
    """Tracks where a variable is referenced in code.

    Attributes:
        variable_name: Name of the variable being used
        file_path: Path to file where usage occurs
        line_number: Line number of usage
        context: Usage context (e.g., "function_arg", "fstring", "assignment")
        scope: Scope where usage occurs (e.g., "module", "function:main", "class:Config")
    """

    variable_name: str
    file_path: Path
    line_number: int
    context: str
    scope: str


@dataclass
class UsageAnalysisResult:
    """Complete analysis result containing declarations and usages.

    Attributes:
        declarations: Map from variable name to its declaration info
        usages: Map from variable name to list of usages
    """

    declarations: Dict[str, VariableDeclaration] = field(default_factory=dict)
    usages: Dict[str, List[VariableUsage]] = field(default_factory=dict)

    @property
    def dead_variables(self) -> List[str]:
        """Variables declared but never used.

        Returns:
            List of variable names that have no usages
        """
        return [name for name in self.declarations.keys() if name not in self.usages or len(self.usages[name]) == 0]

    @property
    def used_variables(self) -> List[str]:
        """Variables both declared and used.

        Returns:
            List of variable names that have at least one usage
        """
        return [name for name in self.declarations.keys() if name in self.usages and len(self.usages[name]) > 0]

    def get_usage_count(self, variable_name: str) -> int:
        """Get number of times a variable is used.

        Args:
            variable_name: Name of variable to check

        Returns:
            Count of usages, or 0 if not found
        """
        return len(self.usages.get(variable_name, []))

    def get_usage_files(self, variable_name: str) -> List[Path]:
        """Get unique files where a variable is used.

        Args:
            variable_name: Name of variable to check

        Returns:
            List of unique file paths where variable is used
        """
        usages = self.usages.get(variable_name, [])
        return list({usage.file_path for usage in usages})

    @property
    def total_variables(self) -> int:
        """Total number of declared variables.

        Returns:
            Count of all declarations
        """
        return len(self.declarations)

    @property
    def coverage_percentage(self) -> float:
        """Percentage of declared variables that are used.

        Returns:
            Percentage value (0.0 to 100.0)
        """
        if self.total_variables == 0:
            return 0.0
        return (len(self.used_variables) / self.total_variables) * 100.0
