"""Tests for schema diff functionality."""

from pathlib import Path

import pytest

from tripwire.schema import TripWireSchema, VariableSchema
from tripwire.schema_diff import BreakingChangeType, ChangeType, compare_schemas


@pytest.fixture
def basic_schema_v1(tmp_path: Path) -> Path:
    """Create a basic schema version 1."""
    schema_content = """
[project]
name = "test-app"
version = "1.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
description = "Database connection"

[variables.PORT]
type = "string"
required = false
default = "8000"
description = "Server port"

[variables.DEBUG]
type = "bool"
required = false
default = false
description = "Debug mode"
"""
    schema_file = tmp_path / "schema-v1.toml"
    schema_file.write_text(schema_content)
    return schema_file


@pytest.fixture
def basic_schema_v2(tmp_path: Path) -> Path:
    """Create a basic schema version 2 with changes."""
    schema_content = """
[project]
name = "test-app"
version = "2.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
description = "PostgreSQL database connection"

[variables.PORT]
type = "int"
required = false
default = 8000
min = 1024
max = 65535
description = "Server port"

[variables.DEBUG]
type = "bool"
required = false
default = false
description = "Debug mode"

[variables.API_KEY]
type = "string"
required = true
secret = true
description = "API authentication key"
"""
    schema_file = tmp_path / "schema-v2.toml"
    schema_file.write_text(schema_content)
    return schema_file


class TestSchemaComparison:
    """Tests for comparing schemas."""

    def test_identical_schemas(self, basic_schema_v1: Path, tmp_path: Path) -> None:
        """Test comparing identical schemas."""
        # Load same schema twice
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v1)

        diff = compare_schemas(schema1, schema2)

        assert len(diff.added_variables) == 0
        assert len(diff.removed_variables) == 0
        assert len(diff.modified_variables) == 0
        assert not diff.has_breaking_changes

    def test_added_variable_detection(self, basic_schema_v1: Path, basic_schema_v2: Path) -> None:
        """Test detecting added variables."""
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v2)

        diff = compare_schemas(schema1, schema2)

        assert len(diff.added_variables) == 1
        assert diff.added_variables[0].variable_name == "API_KEY"
        assert diff.added_variables[0].change_type == ChangeType.ADDED

    def test_added_required_variable_is_breaking(self, basic_schema_v1: Path, basic_schema_v2: Path) -> None:
        """Test that adding required variable is breaking."""
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v2)

        diff = compare_schemas(schema1, schema2)

        added_var = diff.added_variables[0]
        assert added_var.breaking is True
        assert BreakingChangeType.NEW_REQUIRED_VAR in added_var.breaking_reasons

    def test_removed_variable_detection(self, tmp_path: Path) -> None:
        """Test detecting removed variables."""
        # Schema with extra variable
        schema1_content = """
[project]
name = "test"

[variables.OLD_VAR]
type = "string"
required = true

[variables.KEEP_VAR]
type = "string"
required = false
"""
        schema1_file = tmp_path / "schema1.toml"
        schema1_file.write_text(schema1_content)

        # Schema without OLD_VAR
        schema2_content = """
[project]
name = "test"

[variables.KEEP_VAR]
type = "string"
required = false
"""
        schema2_file = tmp_path / "schema2.toml"
        schema2_file.write_text(schema2_content)

        schema1 = TripWireSchema.from_toml(schema1_file)
        schema2 = TripWireSchema.from_toml(schema2_file)

        diff = compare_schemas(schema1, schema2)

        assert len(diff.removed_variables) == 1
        assert diff.removed_variables[0].variable_name == "OLD_VAR"
        assert diff.removed_variables[0].breaking is True

    def test_type_change_detection(self, basic_schema_v1: Path, basic_schema_v2: Path) -> None:
        """Test detecting type changes."""
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v2)

        diff = compare_schemas(schema1, schema2)

        # PORT changed from string to int
        port_change = next((c for c in diff.modified_variables if c.variable_name == "PORT"), None)
        assert port_change is not None
        assert any("Type:" in change for change in port_change.changes)
        assert port_change.breaking is True

    def test_format_validation_added(self, basic_schema_v1: Path, basic_schema_v2: Path) -> None:
        """Test detecting format validation addition."""
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v2)

        diff = compare_schemas(schema1, schema2)

        # DATABASE_URL had format validation added
        db_change = next((c for c in diff.modified_variables if c.variable_name == "DATABASE_URL"), None)
        assert db_change is not None
        assert any("Format validation added" in change for change in db_change.changes)
        assert db_change.breaking is True

    def test_range_validation_stricter(self, tmp_path: Path) -> None:
        """Test detecting stricter range validation."""
        schema1_content = """
[project]
name = "test"

[variables.AGE]
type = "int"
required = false
"""
        schema1_file = tmp_path / "schema1.toml"
        schema1_file.write_text(schema1_content)

        schema2_content = """
[project]
name = "test"

[variables.AGE]
type = "int"
required = false
min = 18
max = 100
"""
        schema2_file = tmp_path / "schema2.toml"
        schema2_file.write_text(schema2_content)

        schema1 = TripWireSchema.from_toml(schema1_file)
        schema2 = TripWireSchema.from_toml(schema2_file)

        diff = compare_schemas(schema1, schema2)

        age_change = next((c for c in diff.modified_variables if c.variable_name == "AGE"), None)
        assert age_change is not None
        assert age_change.breaking is True
        assert BreakingChangeType.STRICTER_VALIDATION in age_change.breaking_reasons


class TestBreakingChanges:
    """Tests for breaking change detection."""

    def test_new_required_variable_is_breaking(self) -> None:
        """Test that new required variable is classified as breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
            "VAR2": VariableSchema(name="VAR2", type="string", required=True),
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_breaking_changes
        assert len(diff.breaking_changes) == 1

    def test_removed_required_variable_is_breaking(self) -> None:
        """Test that removing required variable is breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=True),
            "VAR2": VariableSchema(name="VAR2", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR2": VariableSchema(name="VAR2", type="string", required=False),
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_breaking_changes
        removed_var = diff.removed_variables[0]
        assert removed_var.breaking is True
        assert BreakingChangeType.REMOVED_REQUIRED_VAR in removed_var.breaking_reasons

    def test_type_change_is_breaking(self) -> None:
        """Test that type changes are breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="int", required=False),
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_breaking_changes
        assert BreakingChangeType.TYPE_CHANGE in diff.modified_variables[0].breaking_reasons

    def test_optional_to_required_is_breaking(self) -> None:
        """Test that changing optional to required is breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=True),
        }

        diff = compare_schemas(old_schema, new_schema)

        assert diff.has_breaking_changes


class TestNonBreakingChanges:
    """Tests for non-breaking changes."""

    def test_adding_optional_variable_not_breaking(self) -> None:
        """Test that adding optional variable is not breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
            "VAR2": VariableSchema(name="VAR2", type="string", required=False),
        }

        diff = compare_schemas(old_schema, new_schema)

        added_var = diff.added_variables[0]
        assert not added_var.breaking

    def test_removing_optional_variable_not_breaking(self) -> None:
        """Test that removing optional variable is not breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
            "VAR2": VariableSchema(name="VAR2", type="string", required=False),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        diff = compare_schemas(old_schema, new_schema)

        removed_var = diff.removed_variables[0]
        assert not removed_var.breaking

    def test_description_change_not_breaking(self) -> None:
        """Test that description changes are not breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False, description="Old description"),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False, description="New description"),
        }

        diff = compare_schemas(old_schema, new_schema)

        modified_var = diff.modified_variables[0]
        assert not modified_var.breaking

    def test_required_to_optional_not_breaking(self) -> None:
        """Test that changing required to optional is not breaking."""
        old_schema = TripWireSchema()
        old_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=True),
        }

        new_schema = TripWireSchema()
        new_schema.variables = {
            "VAR1": VariableSchema(name="VAR1", type="string", required=False),
        }

        diff = compare_schemas(old_schema, new_schema)

        modified_var = diff.modified_variables[0]
        assert not modified_var.breaking


class TestDiffSummary:
    """Tests for diff summary statistics."""

    def test_diff_summary_counts(self, basic_schema_v1: Path, basic_schema_v2: Path) -> None:
        """Test that diff summary has correct counts."""
        schema1 = TripWireSchema.from_toml(basic_schema_v1)
        schema2 = TripWireSchema.from_toml(basic_schema_v2)

        diff = compare_schemas(schema1, schema2)
        summary = diff.summary()

        assert summary["added"] == 1  # API_KEY added
        assert summary["removed"] == 0
        assert summary["modified"] == 2  # DATABASE_URL, PORT modified
        assert summary["unchanged"] == 1  # DEBUG unchanged
        assert summary["breaking"] > 0  # Has breaking changes
