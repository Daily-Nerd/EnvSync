"""Tests for dependency graph construction and export functionality."""

import json
from pathlib import Path

import pytest

from tripwire.analysis.dependency_graph import DependencyGraph, DependencyNode
from tripwire.analysis.models import (
    UsageAnalysisResult,
    VariableDeclaration,
    VariableUsage,
)


@pytest.fixture
def sample_declarations():
    """Sample variable declarations for testing."""
    return {
        "DATABASE_URL": VariableDeclaration(
            name="DATABASE_URL",
            env_var="DATABASE_URL",
            file_path=Path("src/config.py"),
            line_number=10,
            is_required=True,
            type_annotation="str",
            validator="postgresql",
        ),
        "API_KEY": VariableDeclaration(
            name="API_KEY",
            env_var="API_KEY",
            file_path=Path("src/config.py"),
            line_number=15,
            is_required=True,
            type_annotation="str",
            validator=None,
        ),
        "DEBUG_MODE": VariableDeclaration(
            name="DEBUG_MODE",
            env_var="DEBUG",
            file_path=Path("src/config.py"),
            line_number=20,
            is_required=False,
            type_annotation="bool",
            validator=None,
        ),
        "UNUSED_VAR": VariableDeclaration(
            name="UNUSED_VAR",
            env_var="UNUSED",
            file_path=Path("src/config.py"),
            line_number=25,
            is_required=False,
            type_annotation="str",
            validator=None,
        ),
    }


@pytest.fixture
def sample_usages():
    """Sample variable usages for testing."""
    return {
        "DATABASE_URL": [
            VariableUsage(
                variable_name="DATABASE_URL",
                file_path=Path("src/models.py"),
                line_number=5,
                context="reference",
                scope="module",
            ),
            VariableUsage(
                variable_name="DATABASE_URL",
                file_path=Path("src/api.py"),
                line_number=12,
                context="reference",
                scope="function:connect",
            ),
            VariableUsage(
                variable_name="DATABASE_URL",
                file_path=Path("src/models.py"),
                line_number=15,
                context="reference",
                scope="class:Model",
            ),
        ],
        "API_KEY": [
            VariableUsage(
                variable_name="API_KEY",
                file_path=Path("src/client.py"),
                line_number=8,
                context="reference",
                scope="function:authenticate",
            ),
            VariableUsage(
                variable_name="API_KEY",
                file_path=Path("src/auth.py"),
                line_number=20,
                context="reference",
                scope="module",
            ),
        ],
        "DEBUG_MODE": [
            VariableUsage(
                variable_name="DEBUG_MODE",
                file_path=Path("src/main.py"),
                line_number=30,
                context="reference",
                scope="function:main",
            ),
        ],
        # UNUSED_VAR intentionally has no usages
    }


@pytest.fixture
def sample_analysis_result(sample_declarations, sample_usages):
    """Complete analysis result for testing."""
    result = UsageAnalysisResult()
    result.declarations = sample_declarations
    result.usages = sample_usages
    return result


@pytest.fixture
def empty_analysis_result():
    """Empty analysis result for edge case testing."""
    return UsageAnalysisResult()


@pytest.fixture
def single_variable_result():
    """Analysis result with single variable."""
    result = UsageAnalysisResult()
    result.declarations = {
        "SINGLE_VAR": VariableDeclaration(
            name="SINGLE_VAR",
            env_var="SINGLE",
            file_path=Path("config.py"),
            line_number=1,
            is_required=True,
            type_annotation="str",
            validator=None,
        )
    }
    result.usages = {
        "SINGLE_VAR": [
            VariableUsage(
                variable_name="SINGLE_VAR",
                file_path=Path("app.py"),
                line_number=10,
                context="reference",
                scope="module",
            )
        ]
    }
    return result


class TestDependencyNode:
    """Tests for DependencyNode dataclass."""

    def test_node_creation(self, sample_declarations, sample_usages):
        """Node should store declaration and usages correctly."""
        declaration = sample_declarations["DATABASE_URL"]
        usages = sample_usages["DATABASE_URL"]

        node = DependencyNode(
            variable_name="DATABASE_URL",
            env_var="DATABASE_URL",
            declaration=declaration,
            usages=usages,
        )

        assert node.variable_name == "DATABASE_URL"
        assert node.env_var == "DATABASE_URL"
        assert node.declaration == declaration
        assert node.usages == usages

    def test_is_dead_with_usages(self, sample_declarations, sample_usages):
        """Node with usages should not be dead."""
        node = DependencyNode(
            variable_name="DATABASE_URL",
            env_var="DATABASE_URL",
            declaration=sample_declarations["DATABASE_URL"],
            usages=sample_usages["DATABASE_URL"],
        )

        assert not node.is_dead
        assert node.usage_count > 0

    def test_is_dead_without_usages(self, sample_declarations):
        """Node with no usages should be dead."""
        node = DependencyNode(
            variable_name="UNUSED_VAR",
            env_var="UNUSED",
            declaration=sample_declarations["UNUSED_VAR"],
            usages=[],
        )

        assert node.is_dead
        assert node.usage_count == 0

    def test_usage_count(self, sample_declarations, sample_usages):
        """Usage count should match number of usages."""
        node = DependencyNode(
            variable_name="DATABASE_URL",
            env_var="DATABASE_URL",
            declaration=sample_declarations["DATABASE_URL"],
            usages=sample_usages["DATABASE_URL"],
        )

        assert node.usage_count == 3

    def test_unique_files(self, sample_declarations, sample_usages):
        """Should return unique files where variable is used."""
        node = DependencyNode(
            variable_name="DATABASE_URL",
            env_var="DATABASE_URL",
            declaration=sample_declarations["DATABASE_URL"],
            usages=sample_usages["DATABASE_URL"],
        )

        unique_files = node.unique_files
        assert len(unique_files) == 2  # models.py and api.py
        assert Path("src/models.py") in unique_files
        assert Path("src/api.py") in unique_files


class TestDependencyGraphConstruction:
    """Tests for dependency graph construction."""

    def test_graph_builds_nodes(self, sample_analysis_result):
        """Graph should create nodes from analysis result."""
        graph = DependencyGraph(sample_analysis_result)

        assert len(graph.nodes) == 4
        assert "DATABASE_URL" in graph.nodes
        assert "API_KEY" in graph.nodes
        assert "DEBUG_MODE" in graph.nodes
        assert "UNUSED_VAR" in graph.nodes

    def test_nodes_have_correct_data(self, sample_analysis_result):
        """Each node should have correct declaration and usages."""
        graph = DependencyGraph(sample_analysis_result)
        node = graph.nodes["DATABASE_URL"]

        assert node.variable_name == "DATABASE_URL"
        assert node.env_var == "DATABASE_URL"
        assert node.declaration.file_path == Path("src/config.py")
        assert len(node.usages) == 3

    def test_empty_graph(self, empty_analysis_result):
        """Empty analysis should create empty graph."""
        graph = DependencyGraph(empty_analysis_result)

        assert len(graph.nodes) == 0
        assert graph.get_dead_nodes() == []
        assert graph.get_top_used() == []

    def test_single_variable_graph(self, single_variable_result):
        """Graph with single variable should work correctly."""
        graph = DependencyGraph(single_variable_result)

        assert len(graph.nodes) == 1
        assert "SINGLE_VAR" in graph.nodes
        assert not graph.nodes["SINGLE_VAR"].is_dead

    def test_repr(self, sample_analysis_result):
        """String representation should be informative."""
        graph = DependencyGraph(sample_analysis_result)
        repr_str = repr(graph)

        assert "DependencyGraph" in repr_str
        assert "nodes=4" in repr_str
        assert "dead=1" in repr_str
        assert "used=3" in repr_str


class TestGraphQueries:
    """Tests for graph query methods."""

    def test_get_dead_nodes(self, sample_analysis_result):
        """Should identify nodes with no usages."""
        graph = DependencyGraph(sample_analysis_result)
        dead_nodes = graph.get_dead_nodes()

        assert len(dead_nodes) == 1
        assert dead_nodes[0].variable_name == "UNUSED_VAR"
        assert dead_nodes[0].is_dead
        assert dead_nodes[0].usage_count == 0

    def test_get_dead_nodes_sorted(self, sample_analysis_result):
        """Dead nodes should be sorted by variable name."""
        # Add another dead variable
        sample_analysis_result.declarations["ANOTHER_UNUSED"] = VariableDeclaration(
            name="ANOTHER_UNUSED",
            env_var="ANOTHER",
            file_path=Path("config.py"),
            line_number=30,
            is_required=False,
            type_annotation="str",
            validator=None,
        )

        graph = DependencyGraph(sample_analysis_result)
        dead_nodes = graph.get_dead_nodes()

        assert len(dead_nodes) == 2
        assert dead_nodes[0].variable_name == "ANOTHER_UNUSED"
        assert dead_nodes[1].variable_name == "UNUSED_VAR"

    def test_get_top_used(self, sample_analysis_result):
        """Should return most-used variables."""
        graph = DependencyGraph(sample_analysis_result)
        top_used = graph.get_top_used(2)

        assert len(top_used) == 2
        assert top_used[0].variable_name == "DATABASE_URL"  # 3 uses
        assert top_used[1].variable_name == "API_KEY"  # 2 uses

    def test_get_top_used_with_limit(self, sample_analysis_result):
        """Should respect limit parameter."""
        graph = DependencyGraph(sample_analysis_result)

        top_1 = graph.get_top_used(1)
        assert len(top_1) == 1
        assert top_1[0].variable_name == "DATABASE_URL"

        top_10 = graph.get_top_used(10)
        assert len(top_10) == 4  # All 4 variables (3 used + 1 dead)

    def test_get_node(self, sample_analysis_result):
        """Should retrieve node by variable name."""
        graph = DependencyGraph(sample_analysis_result)

        node = graph.get_node("DATABASE_URL")
        assert node is not None
        assert node.variable_name == "DATABASE_URL"

    def test_get_node_missing(self, sample_analysis_result):
        """Should return None for missing variable."""
        graph = DependencyGraph(sample_analysis_result)

        node = graph.get_node("NONEXISTENT")
        assert node is None


class TestJSONExport:
    """Tests for JSON export functionality."""

    def test_json_export_structure(self, sample_analysis_result):
        """JSON export should have correct structure."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        assert "nodes" in json_data
        assert "summary" in json_data
        assert isinstance(json_data["nodes"], list)
        assert isinstance(json_data["summary"], dict)

    def test_json_summary_fields(self, sample_analysis_result):
        """Summary should contain all expected fields."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()
        summary = json_data["summary"]

        assert "total_variables" in summary
        assert "dead_variables" in summary
        assert "used_variables" in summary
        assert "coverage_percentage" in summary

        assert summary["total_variables"] == 4
        assert summary["dead_variables"] == 1
        assert summary["used_variables"] == 3
        assert summary["coverage_percentage"] == 75.0

    def test_json_node_fields(self, sample_analysis_result):
        """Each node should have all required fields."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        for node in json_data["nodes"]:
            assert "variable" in node
            assert "env_var" in node
            assert "is_dead" in node
            assert "usage_count" in node
            assert "declaration" in node
            assert "usages" in node

            # Check declaration fields
            decl = node["declaration"]
            assert "file" in decl
            assert "line" in decl
            assert "is_required" in decl

            # Check usage fields
            for usage in node["usages"]:
                assert "file" in usage
                assert "line" in usage
                assert "scope" in usage
                assert "context" in usage

    def test_json_serializable(self, sample_analysis_result):
        """JSON export should be fully serializable."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        # Should not raise exception
        json_str = json.dumps(json_data, indent=2)
        assert len(json_str) > 0

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed == json_data

    def test_json_nodes_sorted(self, sample_analysis_result):
        """Nodes should be sorted by variable name."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        node_names = [node["variable"] for node in json_data["nodes"]]
        assert node_names == sorted(node_names)

    def test_json_dead_node(self, sample_analysis_result):
        """Dead nodes should be marked correctly in JSON."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        unused_node = next(n for n in json_data["nodes"] if n["variable"] == "UNUSED_VAR")
        assert unused_node["is_dead"] is True
        assert unused_node["usage_count"] == 0
        assert len(unused_node["usages"]) == 0

    def test_json_used_node(self, sample_analysis_result):
        """Used nodes should show correct usage data."""
        graph = DependencyGraph(sample_analysis_result)
        json_data = graph.export_json()

        db_node = next(n for n in json_data["nodes"] if n["variable"] == "DATABASE_URL")
        assert db_node["is_dead"] is False
        assert db_node["usage_count"] == 3
        assert len(db_node["usages"]) == 3


class TestMermaidExport:
    """Tests for Mermaid diagram export functionality."""

    def test_mermaid_starts_with_graph_td(self, sample_analysis_result):
        """Mermaid diagram should start with graph TD."""
        graph = DependencyGraph(sample_analysis_result)
        mermaid = graph.export_mermaid()

        assert mermaid.startswith("graph TD")

    def test_mermaid_contains_nodes(self, sample_analysis_result):
        """Mermaid diagram should define all nodes."""
        graph = DependencyGraph(sample_analysis_result)
        mermaid = graph.export_mermaid()

        assert "DATABASE_URL" in mermaid
        assert "API_KEY" in mermaid
        assert "DEBUG_MODE" in mermaid
        assert "UNUSED_VAR" in mermaid

    def test_mermaid_shows_usage_counts(self, sample_analysis_result):
        """Used nodes should show usage counts."""
        graph = DependencyGraph(sample_analysis_result)
        mermaid = graph.export_mermaid()

        assert "3 uses" in mermaid  # DATABASE_URL
        assert "2 uses" in mermaid  # API_KEY
        assert "1 use" in mermaid  # DEBUG_MODE (singular)

    def test_mermaid_marks_dead_nodes(self, sample_analysis_result):
        """Dead nodes should be marked as DEAD CODE."""
        graph = DependencyGraph(sample_analysis_result)
        mermaid = graph.export_mermaid()

        assert "DEAD CODE" in mermaid
        # Check for red styling (updated to use better color scheme)
        assert "fill:#FFB6C1" in mermaid or "fill:#f99" in mermaid

    def test_mermaid_includes_edges(self, sample_analysis_result):
        """Diagram should show connections to files."""
        graph = DependencyGraph(sample_analysis_result)
        mermaid = graph.export_mermaid()

        # Should have arrows to usage files
        assert "-->" in mermaid
        # Should reference files
        assert "models.py" in mermaid or "models_py" in mermaid
        assert "api.py" in mermaid or "api_py" in mermaid

    def test_mermaid_empty_graph(self, empty_analysis_result):
        """Empty graph should produce minimal diagram."""
        graph = DependencyGraph(empty_analysis_result)
        mermaid = graph.export_mermaid()

        assert mermaid.startswith("graph TD")
        assert len(mermaid.splitlines()) == 1  # Just the header

    def test_mermaid_single_dead_variable(self, empty_analysis_result):
        """Single dead variable should be styled red."""
        empty_analysis_result.declarations["DEAD"] = VariableDeclaration(
            name="DEAD",
            env_var="DEAD",
            file_path=Path("config.py"),
            line_number=1,
            is_required=False,
            type_annotation="str",
            validator=None,
        )

        graph = DependencyGraph(empty_analysis_result)
        mermaid = graph.export_mermaid()

        assert "DEAD CODE" in mermaid
        # Check for red styling (updated to use better color scheme)
        assert "fill:#FFB6C1" in mermaid or "fill:#f99" in mermaid


class TestDOTExport:
    """Tests for Graphviz DOT export functionality."""

    def test_dot_starts_with_digraph(self, sample_analysis_result):
        """DOT export should start with digraph declaration."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        assert dot.startswith("digraph dependencies {")
        assert dot.endswith("}")

    def test_dot_has_layout_settings(self, sample_analysis_result):
        """DOT should configure layout settings."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        # Updated to use TB (Top-Bottom) for better hierarchy
        assert "rankdir=TB" in dot
        assert "node [shape=box" in dot

    def test_dot_contains_all_nodes(self, sample_analysis_result):
        """DOT should define all variable nodes."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        assert "DATABASE_URL" in dot
        assert "API_KEY" in dot
        assert "DEBUG_MODE" in dot
        assert "UNUSED_VAR" in dot

    def test_dot_shows_usage_counts(self, sample_analysis_result):
        """Used nodes should display usage counts."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        assert "3 uses" in dot  # DATABASE_URL
        assert "2 uses" in dot  # API_KEY
        assert "1 use" in dot  # DEBUG_MODE

    def test_dot_styles_dead_nodes(self, sample_analysis_result):
        """Dead nodes should be styled red."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        assert "DEAD CODE" in dot
        assert "color=red" in dot or "fillcolor" in dot

    def test_dot_includes_edges(self, sample_analysis_result):
        """DOT should show connections to usage files."""
        graph = DependencyGraph(sample_analysis_result)
        dot = graph.export_dot()

        assert "->" in dot  # Edge operator
        assert "models.py" in dot
        assert "api.py" in dot

    def test_dot_empty_graph(self, empty_analysis_result):
        """Empty graph should produce valid minimal DOT."""
        graph = DependencyGraph(empty_analysis_result)
        dot = graph.export_dot()

        assert dot.startswith("digraph dependencies {")
        assert dot.endswith("}")
        assert "rankdir=TB" in dot

    def test_dot_handles_special_characters(self):
        """DOT should quote identifiers with special characters."""
        result = UsageAnalysisResult()
        result.declarations["VAR_WITH_DOTS"] = VariableDeclaration(
            name="VAR_WITH_DOTS",
            env_var="VAR",
            file_path=Path("config.py"),
            line_number=1,
            is_required=True,
            type_annotation="str",
            validator=None,
        )
        result.usages["VAR_WITH_DOTS"] = [
            VariableUsage(
                variable_name="VAR_WITH_DOTS",
                file_path=Path("file.name.py"),
                line_number=10,
                context="reference",
                scope="module",
            )
        ]

        graph = DependencyGraph(result)
        dot = graph.export_dot()

        # Should handle file names with dots
        assert '"file.name.py"' in dot or "file.name.py" in dot


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_variable_with_no_env_var_match(self):
        """Should handle when Python variable name differs from env var."""
        result = UsageAnalysisResult()
        result.declarations["db_url"] = VariableDeclaration(
            name="db_url",
            env_var="DATABASE_URL",
            file_path=Path("config.py"),
            line_number=5,
            is_required=True,
            type_annotation="str",
            validator=None,
        )

        graph = DependencyGraph(result)
        node = graph.nodes["db_url"]

        assert node.variable_name == "db_url"
        assert node.env_var == "DATABASE_URL"

    def test_variable_used_many_times_same_file(self):
        """Should count all usages even in same file."""
        result = UsageAnalysisResult()
        result.declarations["VAR"] = VariableDeclaration(
            name="VAR",
            env_var="VAR",
            file_path=Path("config.py"),
            line_number=1,
            is_required=True,
            type_annotation="str",
            validator=None,
        )
        result.usages["VAR"] = [
            VariableUsage(
                variable_name="VAR",
                file_path=Path("app.py"),
                line_number=i,
                context="reference",
                scope="module",
            )
            for i in range(1, 101)  # 100 usages in same file
        ]

        graph = DependencyGraph(result)
        node = graph.nodes["VAR"]

        assert node.usage_count == 100
        assert len(node.unique_files) == 1

    def test_all_variables_dead(self):
        """Should handle case where all variables are unused."""
        result = UsageAnalysisResult()
        result.declarations["VAR1"] = VariableDeclaration(
            name="VAR1",
            env_var="VAR1",
            file_path=Path("config.py"),
            line_number=1,
            is_required=True,
            type_annotation="str",
            validator=None,
        )
        result.declarations["VAR2"] = VariableDeclaration(
            name="VAR2",
            env_var="VAR2",
            file_path=Path("config.py"),
            line_number=2,
            is_required=True,
            type_annotation="str",
            validator=None,
        )

        graph = DependencyGraph(result)

        assert len(graph.get_dead_nodes()) == 2
        # get_top_used returns all nodes sorted by usage (dead nodes have 0 usages)
        top_used = graph.get_top_used()
        assert len(top_used) == 2
        assert all(node.is_dead for node in top_used)

    def test_all_variables_used(self):
        """Should handle case where no variables are dead."""
        result = UsageAnalysisResult()
        for i in range(3):
            var_name = f"VAR{i}"
            result.declarations[var_name] = VariableDeclaration(
                name=var_name,
                env_var=var_name,
                file_path=Path("config.py"),
                line_number=i + 1,
                is_required=True,
                type_annotation="str",
                validator=None,
            )
            result.usages[var_name] = [
                VariableUsage(
                    variable_name=var_name,
                    file_path=Path("app.py"),
                    line_number=i + 10,
                    context="reference",
                    scope="module",
                )
            ]

        graph = DependencyGraph(result)

        assert len(graph.get_dead_nodes()) == 0
        assert len(graph.get_top_used()) == 3
