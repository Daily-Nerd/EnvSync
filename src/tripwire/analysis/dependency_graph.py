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

    def filter_by_top_n(self, n: int) -> "DependencyGraph":
        """Create filtered graph with only top N most-used variables.

        Args:
            n: Number of top variables to include

        Returns:
            New DependencyGraph with filtered nodes
        """
        top_nodes = self.get_top_used(limit=n)
        return self._create_filtered_graph([node.variable_name for node in top_nodes])

    def filter_by_min_usage(self, min_uses: int) -> "DependencyGraph":
        """Create filtered graph with only variables used >= min_uses times.

        Args:
            min_uses: Minimum usage count threshold

        Returns:
            New DependencyGraph with filtered nodes
        """
        filtered_vars = [name for name, node in self.nodes.items() if node.usage_count >= min_uses]
        return self._create_filtered_graph(filtered_vars)

    def filter_dead_only(self) -> "DependencyGraph":
        """Create filtered graph with only dead (unused) variables.

        Returns:
            New DependencyGraph containing only dead nodes
        """
        dead_vars = [node.variable_name for node in self.get_dead_nodes()]
        return self._create_filtered_graph(dead_vars)

    def filter_used_only(self) -> "DependencyGraph":
        """Create filtered graph excluding dead variables.

        Returns:
            New DependencyGraph containing only used nodes
        """
        used_vars = [name for name, node in self.nodes.items() if not node.is_dead]
        return self._create_filtered_graph(used_vars)

    def filter_by_variables(self, variable_names: List[str]) -> "DependencyGraph":
        """Create filtered graph with specific variables only.

        Args:
            variable_names: List of variable names to include

        Returns:
            New DependencyGraph with only specified nodes

        Raises:
            ValueError: If any variable name not found in graph
        """
        missing = [name for name in variable_names if name not in self.nodes]
        if missing:
            raise ValueError(f"Variables not found in graph: {', '.join(missing)}")

        return self._create_filtered_graph(variable_names)

    def _create_filtered_graph(self, variable_names: List[str]) -> "DependencyGraph":
        """Create new graph with subset of variables.

        Args:
            variable_names: List of variable names to include

        Returns:
            New DependencyGraph with filtered nodes
        """
        # Create filtered result
        filtered_result = UsageAnalysisResult()

        for var_name in variable_names:
            if var_name in self.result.declarations:
                filtered_result.declarations[var_name] = self.result.declarations[var_name]
            if var_name in self.result.usages:
                filtered_result.usages[var_name] = self.result.usages[var_name]

        return DependencyGraph(filtered_result)

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

    def export_mermaid(self, use_subgraphs: bool = True) -> str:
        """Export as Mermaid diagram for GitHub markdown.

        Generates a flowchart showing variable relationships. Dead nodes
        are highlighted in red. Large graphs are organized into subgraphs
        for better readability.

        Args:
            use_subgraphs: Group variables by usage tier (default: True)

        Returns:
            Mermaid diagram syntax

        Example output:
            ```mermaid
            graph TD
                subgraph Heavy[Heavy Usage (>20 uses)]
                    DATABASE_URL[DATABASE_URL<br/>47 uses]
                end
                DATABASE_URL --> models_py[models.py]
                UNUSED_VAR[UNUSED_VAR<br/>DEAD CODE]
                style UNUSED_VAR fill:#f99
            ```
        """
        lines = ["graph TD"]

        # Add summary comment for large graphs
        node_count = len(self.nodes)
        if node_count > 10:
            dead_count = len(self.get_dead_nodes())
            used_count = node_count - dead_count
            lines.append(f"    %% Total: {node_count} variables ({used_count} used, {dead_count} dead)")
            lines.append("")

        # Categorize nodes by usage
        if use_subgraphs and node_count > 10:
            heavy_nodes = [n for n in self.nodes.values() if n.usage_count >= 20]
            medium_nodes = [n for n in self.nodes.values() if 5 <= n.usage_count < 20]
            light_nodes = [n for n in self.nodes.values() if 1 <= n.usage_count < 5]
            dead_nodes = [n for n in self.nodes.values() if n.is_dead]

            # Heavy usage subgraph
            if heavy_nodes:
                lines.append('    subgraph Heavy["Heavy Usage (20+ uses)"]')
                for node in sorted(heavy_nodes, key=lambda n: n.variable_name):
                    node_id = self._sanitize_mermaid_id(node.variable_name)
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}<br/>{node.usage_count} {count_text}"
                    lines.append(f"        {node_id}[{label}]")
                    lines.append(f"        style {node_id} fill:#90EE90,stroke:#2E8B57,stroke-width:2px")
                lines.append("    end")
                lines.append("")

            # Medium usage subgraph
            if medium_nodes:
                lines.append('    subgraph Medium["Medium Usage (5-19 uses)"]')
                for node in sorted(medium_nodes, key=lambda n: n.variable_name):
                    node_id = self._sanitize_mermaid_id(node.variable_name)
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}<br/>{node.usage_count} {count_text}"
                    lines.append(f"        {node_id}[{label}]")
                    lines.append(f"        style {node_id} fill:#FFE4B5,stroke:#DAA520")
                lines.append("    end")
                lines.append("")

            # Light usage subgraph
            if light_nodes:
                lines.append('    subgraph Light["Light Usage (1-4 uses)"]')
                for node in sorted(light_nodes, key=lambda n: n.variable_name):
                    node_id = self._sanitize_mermaid_id(node.variable_name)
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}<br/>{node.usage_count} {count_text}"
                    lines.append(f"        {node_id}[{label}]")
                    lines.append(f"        style {node_id} fill:#E0E0E0,stroke:#808080")
                lines.append("    end")
                lines.append("")

            # Dead code subgraph
            if dead_nodes:
                lines.append('    subgraph Dead["Dead Code (0 uses)"]')
                for node in sorted(dead_nodes, key=lambda n: n.variable_name):
                    node_id = self._sanitize_mermaid_id(node.variable_name)
                    label = f"{node.variable_name}<br/>DEAD CODE"
                    lines.append(f"        {node_id}[{label}]")
                    lines.append(f"        style {node_id} fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
                lines.append("    end")
                lines.append("")

            # Add edges (outside subgraphs)
            for node in self.nodes.values():
                if not node.is_dead:
                    node_id = self._sanitize_mermaid_id(node.variable_name)
                    for file_path in node.unique_files:
                        file_id = self._sanitize_mermaid_id(file_path.name)
                        file_label = file_path.name
                        lines.append(f"    {node_id} --> {file_id}[{file_label}]")

        else:
            # Simple flat graph for small graphs
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

                # Color coding by usage
                if node.is_dead:
                    lines.append(f"    style {node_id} fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
                elif node.usage_count >= 20:
                    lines.append(f"    style {node_id} fill:#90EE90,stroke:#2E8B57,stroke-width:2px")
                elif node.usage_count >= 5:
                    lines.append(f"    style {node_id} fill:#FFE4B5,stroke:#DAA520")
                else:
                    lines.append(f"    style {node_id} fill:#E0E0E0,stroke:#808080")

                # Add edges to files where variable is used
                if not node.is_dead:
                    for file_path in node.unique_files:
                        file_id = self._sanitize_mermaid_id(file_path.name)
                        file_label = file_path.name
                        lines.append(f"    {node_id} --> {file_id}[{file_label}]")

        return "\n".join(lines)

    def export_dot(self, use_clusters: bool = True) -> str:
        """Export as Graphviz DOT format.

        Generates professional-quality diagrams that can be rendered with:
            dot -Tpng graph.dot -o graph.png
            dot -Tsvg graph.dot -o graph.svg

        Args:
            use_clusters: Group variables by usage tier (default: True)

        Returns:
            DOT format graph specification

        Example output:
            digraph dependencies {
                rankdir=LR;
                node [shape=box];

                subgraph cluster_heavy {
                    label="Heavy Usage (20+ uses)";
                    DATABASE_URL [label="DATABASE_URL\n47 uses"];
                }

                DATABASE_URL -> "models.py";
                DATABASE_URL -> "api.py";
            }
        """
        lines = [
            "digraph dependencies {",
            "    rankdir=TB;",
            '    graph [fontname="Helvetica", fontsize=12];',
            '    node [shape=box, style="rounded,filled", fontname="Helvetica"];',
            '    edge [fontname="Helvetica", fontsize=10];',
            "",
        ]

        node_count = len(self.nodes)

        # Add summary comment for large graphs
        if node_count > 10:
            dead_count = len(self.get_dead_nodes())
            used_count = node_count - dead_count
            lines.append(
                f'    label="Environment Variables\\n{node_count} total ({used_count} used, {dead_count} dead)";'
            )
            lines.append('    labelloc="t";')
            lines.append("")

        # Categorize nodes by usage
        if use_clusters and node_count > 10:
            heavy_nodes = [n for n in self.nodes.values() if n.usage_count >= 20]
            medium_nodes = [n for n in self.nodes.values() if 5 <= n.usage_count < 20]
            light_nodes = [n for n in self.nodes.values() if 1 <= n.usage_count < 5]
            dead_nodes = [n for n in self.nodes.values() if n.is_dead]

            cluster_num = 0

            # Heavy usage cluster
            if heavy_nodes:
                lines.append(f"    subgraph cluster_{cluster_num} {{")
                cluster_num += 1
                lines.append('        label="Heavy Usage (20+ uses)";')
                lines.append("        style=filled;")
                lines.append("        color=lightgreen;")
                lines.append('        fillcolor="#f0fff0";')
                lines.append("")

                for node in sorted(heavy_nodes, key=lambda n: n.variable_name):
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    lines.append(
                        f"        {self._quote_dot_id(node.variable_name)} " f'[label="{label}", fillcolor="#90EE90"];'
                    )

                lines.append("    }")
                lines.append("")

            # Medium usage cluster
            if medium_nodes:
                lines.append(f"    subgraph cluster_{cluster_num} {{")
                cluster_num += 1
                lines.append('        label="Medium Usage (5-19 uses)";')
                lines.append("        style=filled;")
                lines.append("        color=goldenrod;")
                lines.append('        fillcolor="#fffaf0";')
                lines.append("")

                for node in sorted(medium_nodes, key=lambda n: n.variable_name):
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    lines.append(
                        f"        {self._quote_dot_id(node.variable_name)} " f'[label="{label}", fillcolor="#FFE4B5"];'
                    )

                lines.append("    }")
                lines.append("")

            # Light usage cluster
            if light_nodes:
                lines.append(f"    subgraph cluster_{cluster_num} {{")
                cluster_num += 1
                lines.append('        label="Light Usage (1-4 uses)";')
                lines.append("        style=filled;")
                lines.append("        color=gray;")
                lines.append('        fillcolor="#f5f5f5";')
                lines.append("")

                for node in sorted(light_nodes, key=lambda n: n.variable_name):
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    lines.append(
                        f"        {self._quote_dot_id(node.variable_name)} " f'[label="{label}", fillcolor="#E0E0E0"];'
                    )

                lines.append("    }")
                lines.append("")

            # Dead code cluster
            if dead_nodes:
                lines.append(f"    subgraph cluster_{cluster_num} {{")
                lines.append('        label="Dead Code (0 uses)";')
                lines.append('        style="filled,dashed";')
                lines.append("        color=red;")
                lines.append('        fillcolor="#fff0f0";')
                lines.append("")

                for node in sorted(dead_nodes, key=lambda n: n.variable_name):
                    label = f"{node.variable_name}\\nDEAD CODE"
                    lines.append(
                        f"        {self._quote_dot_id(node.variable_name)} "
                        f'[label="{label}", fillcolor="#FFB6C1", color=red, penwidth=2];'
                    )

                lines.append("    }")
                lines.append("")

            # Add edges (outside clusters)
            lines.append("    // Variable to file dependencies")
            for node in self.nodes.values():
                if not node.is_dead:
                    for file_path in node.unique_files:
                        lines.append(
                            f"    {self._quote_dot_id(node.variable_name)} -> " f"{self._quote_dot_id(file_path.name)};"
                        )

        else:
            # Simple flat graph for small graphs
            for node in sorted(self.nodes.values(), key=lambda n: n.variable_name):
                # Create node label
                if node.is_dead:
                    label = f"{node.variable_name}\\nDEAD CODE"
                    style = 'fillcolor="#FFB6C1", color=red, penwidth=2'
                elif node.usage_count >= 20:
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    style = 'fillcolor="#90EE90"'
                elif node.usage_count >= 5:
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    style = 'fillcolor="#FFE4B5"'
                else:
                    count_text = "use" if node.usage_count == 1 else "uses"
                    label = f"{node.variable_name}\\n{node.usage_count} {count_text}"
                    style = 'fillcolor="#E0E0E0"'

                # Define node
                node_def = f'    {self._quote_dot_id(node.variable_name)} [label="{label}", {style}];'
                lines.append(node_def)

                # Add edges to files
                if not node.is_dead:
                    for file_path in node.unique_files:
                        lines.append(
                            f"    {self._quote_dot_id(node.variable_name)} -> " f"{self._quote_dot_id(file_path.name)};"
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
