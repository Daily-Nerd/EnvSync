"""Dependency graph construction and export for environment variable analysis.

This module provides graph-based representation of variable dependencies, with
support for multiple export formats (JSON, Mermaid, DOT).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from tripwire.analysis.models import (
    UsageAnalysisResult,
    VariableDeclaration,
    VariableUsage,
)


@dataclass
class DependencyNode:
    """Node in the dependency graph representing a variable.

    Attributes:
        variable_name: Python variable name (e.g., "DATABASE_URL")
        env_var: Environment variable name being read
        declaration: Declaration information
        usages: List of all usages across codebase

    Example:
        >>> node = DependencyNode("DATABASE_URL", "DATABASE_URL", decl, usages)
        >>> node.is_dead  # True if no usages
        >>> node.usage_count  # Number of references
    """

    variable_name: str
    env_var: str
    declaration: VariableDeclaration
    usages: List[VariableUsage]

    @property
    def is_dead(self) -> bool:
        """Check if variable is unused (dead code).

        Returns:
            True if variable has no usages
        """
        return len(self.usages) == 0

    @property
    def usage_count(self) -> int:
        """Count total number of usages.

        Returns:
            Number of times variable is referenced
        """
        return len(self.usages)

    @property
    def unique_files(self) -> List[Path]:
        """Get unique files where variable is used.

        Returns:
            Sorted list of unique file paths
        """
        return sorted(set(usage.file_path for usage in self.usages))


class DependencyGraph:
    """Graph representation of environment variable dependencies.

    This class constructs a dependency graph from usage analysis results,
    enabling queries and visualization of variable relationships.

    Example:
        >>> graph = DependencyGraph(analysis_result)
        >>> dead_nodes = graph.get_dead_nodes()
        >>> top_used = graph.get_top_used(10)
        >>> json_data = graph.export_json()
        >>> mermaid = graph.export_mermaid()

    Attributes:
        result: Original analysis result
        nodes: Dictionary mapping variable names to graph nodes
    """

    def __init__(self, analysis_result: UsageAnalysisResult):
        """Build dependency graph from analysis result.

        Args:
            analysis_result: Complete usage analysis with declarations and usages
        """
        self.result = analysis_result
        self.nodes: Dict[str, DependencyNode] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Construct graph nodes from declarations and usages.

        Creates one node per declared variable, associating all usages.
        """
        for var_name, declaration in self.result.declarations.items():
            usages = self.result.usages.get(var_name, [])

            self.nodes[var_name] = DependencyNode(
                variable_name=var_name,
                env_var=declaration.env_var,
                declaration=declaration,
                usages=usages,
            )

    def get_dead_nodes(self) -> List[DependencyNode]:
        """Get all nodes with no usages (dead code).

        Returns:
            List of nodes with zero usages, sorted by variable name
        """
        return sorted(
            [node for node in self.nodes.values() if node.is_dead],
            key=lambda n: n.variable_name,
        )

    def get_top_used(self, limit: int = 10) -> List[DependencyNode]:
        """Get most-used variables.

        Args:
            limit: Maximum number of nodes to return (default: 10)

        Returns:
            List of nodes sorted by usage count (descending)
        """
        return sorted(
            self.nodes.values(),
            key=lambda n: n.usage_count,
            reverse=True,
        )[:limit]

    def get_node(self, variable_name: str) -> Optional[DependencyNode]:
        """Get node by variable name.

        Args:
            variable_name: Name of variable to retrieve

        Returns:
            Node if found, None otherwise
        """
        return self.nodes.get(variable_name)

    def export_json(self) -> Dict[str, Any]:
        """Export graph as JSON-serializable dictionary.

        Format suitable for machine processing, CI/CD integration,
        and custom tooling.

        Returns:
            Dictionary with nodes and summary statistics

        Example output:
            {
                "nodes": [
                    {
                        "variable": "DATABASE_URL",
                        "env_var": "DATABASE_URL",
                        "is_dead": false,
                        "usage_count": 47,
                        "declaration": {
                            "file": "config.py",
                            "line": 12
                        },
                        "usages": [
                            {"file": "models.py", "line": 23, "scope": "module"},
                            {"file": "api.py", "line": 45, "scope": "function:connect"}
                        ]
                    }
                ],
                "summary": {
                    "total_variables": 23,
                    "dead_variables": 3,
                    "used_variables": 20,
                    "coverage_percentage": 86.96
                }
            }
        """
        nodes_data = []

        for node in sorted(self.nodes.values(), key=lambda n: n.variable_name):
            node_dict = {
                "variable": node.variable_name,
                "env_var": node.env_var,
                "is_dead": node.is_dead,
                "usage_count": node.usage_count,
                "declaration": {
                    "file": str(node.declaration.file_path),
                    "line": node.declaration.line_number,
                    "is_required": node.declaration.is_required,
                    "type_annotation": node.declaration.type_annotation,
                    "validator": node.declaration.validator,
                },
                "usages": [
                    {
                        "file": str(usage.file_path),
                        "line": usage.line_number,
                        "scope": usage.scope,
                        "context": usage.context,
                    }
                    for usage in node.usages
                ],
            }
            nodes_data.append(node_dict)

        summary = {
            "total_variables": self.result.total_variables,
            "dead_variables": len(self.result.dead_variables),
            "used_variables": len(self.result.used_variables),
            "coverage_percentage": round(self.result.coverage_percentage, 2),
        }

        return {
            "nodes": nodes_data,
            "summary": summary,
        }

    def export_mermaid(self) -> str:
        """Export as Mermaid diagram for GitHub markdown.

        Generates a flowchart showing variable relationships. Dead nodes
        are highlighted in red.

        Returns:
            Mermaid diagram syntax

        Example output:
            ```mermaid
            graph TD
                DATABASE_URL[DATABASE_URL<br/>47 uses]
                DATABASE_URL --> models_py[models.py]
                DATABASE_URL --> api_py[api.py]
                UNUSED_VAR[UNUSED_VAR<br/>DEAD CODE]
                style UNUSED_VAR fill:#f99
            ```
        """
        lines = ["graph TD"]

        for node in sorted(self.nodes.values(), key=lambda n: n.variable_name):
            # Create node label
            if node.is_dead:
                label = f"{node.variable_name}<br/>DEAD CODE"
            else:
                count_text = "use" if node.usage_count == 1 else "uses"
                label = f"{node.variable_name}<br/>{node.usage_count} {count_text}"

            # Define node
            node_id = self._sanitize_mermaid_id(node.variable_name)
            lines.append(f"    {node_id}[{label}]")

            # Add edges to files where variable is used
            if not node.is_dead:
                for file_path in node.unique_files:
                    file_id = self._sanitize_mermaid_id(file_path.name)
                    file_label = file_path.name
                    lines.append(f"    {node_id} --> {file_id}[{file_label}]")

            # Style dead nodes red
            if node.is_dead:
                lines.append(f"    style {node_id} fill:#f99")

        return "\n".join(lines)

    def export_dot(self) -> str:
        """Export as Graphviz DOT format.

        Generates professional-quality diagrams that can be rendered with:
            dot -Tpng graph.dot -o graph.png
            dot -Tsvg graph.dot -o graph.svg

        Returns:
            DOT format graph specification

        Example output:
            digraph dependencies {
                rankdir=LR;
                node [shape=box];

                DATABASE_URL [label="DATABASE_URL\n47 uses"];
                DATABASE_URL -> "models.py";
                DATABASE_URL -> "api.py";

                UNUSED_VAR [label="UNUSED_VAR\nDEAD CODE" color=red];
            }
        """
        lines = [
            "digraph dependencies {",
            "    rankdir=LR;",
            "    node [shape=box, style=rounded];",
            "",
        ]

        for node in sorted(self.nodes.values(), key=lambda n: n.variable_name):
            # Create node label
            if node.is_dead:
                label = f"{node.variable_name}\\nDEAD CODE"
                style = 'color=red, style="rounded,filled", fillcolor="#ffcccc"'
            else:
                count_text = "use" if node.usage_count == 1 else "uses"
                label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                style = ""

            # Define node
            node_def = f'    {self._quote_dot_id(node.variable_name)} [label="{label}"'
            if style:
                node_def += f", {style}"
            node_def += "];"
            lines.append(node_def)

            # Add edges to files
            if not node.is_dead:
                for file_path in node.unique_files:
                    lines.append(
                        f"    {self._quote_dot_id(node.variable_name)} -> {self._quote_dot_id(file_path.name)};"
                    )

        lines.append("}")
        return "\n".join(lines)

    def _sanitize_mermaid_id(self, text: str) -> str:
        """Convert text to valid Mermaid identifier.

        Args:
            text: Raw text (variable name or file path)

        Returns:
            Sanitized identifier safe for Mermaid syntax
        """
        # Replace non-alphanumeric characters with underscores
        return "".join(c if c.isalnum() else "_" for c in text)

    def _quote_dot_id(self, text: str) -> str:
        """Quote identifier for DOT format if needed.

        Args:
            text: Identifier text

        Returns:
            Quoted identifier if contains special characters
        """
        # Quote if contains spaces or special characters
        if any(c in text for c in " -."):
            return f'"{text}"'
        return text

    def __repr__(self) -> str:
        """String representation of graph.

        Returns:
            Summary string with node counts
        """
        return (
            f"DependencyGraph(nodes={len(self.nodes)}, "
            f"dead={len(self.get_dead_nodes())}, "
            f"used={len(self.nodes) - len(self.get_dead_nodes())})"
        )
