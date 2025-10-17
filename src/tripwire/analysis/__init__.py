"""Analysis module for environment variable usage tracking and dependency graphs.

This module provides AST-based analysis to track where environment variables
are declared and used across the codebase, enabling dead code detection and
dependency visualization.
"""

from tripwire.analysis.dependency_graph import (
    DependencyGraph,
    DependencyNode,
)
from tripwire.analysis.models import (
    UsageAnalysisResult,
    VariableDeclaration,
    VariableUsage,
)
from tripwire.analysis.usage_tracker import (
    UsageAnalyzer,
    UsageTrackingVisitor,
)

__all__ = [
    "VariableDeclaration",
    "VariableUsage",
    "UsageAnalysisResult",
    "UsageTrackingVisitor",
    "UsageAnalyzer",
    "DependencyGraph",
    "DependencyNode",
]
