"""Tests for schema migration functionality."""

from pathlib import Path

import pytest

from tripwire.schema_diff import create_migration_plan


@pytest.fixture
def schema_v1(tmp_path: Path) -> Path:
    """Create schema version 1."""
    content = """
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

[variables.OLD_VAR]
type = "string"
required = false
default = "deprecated"
"""
    schema_file = tmp_path / "schema-v1.toml"
    schema_file.write_text(content)
    return schema_file


@pytest.fixture
def schema_v2(tmp_path: Path) -> Path:
    """Create schema version 2."""
    content = """
[project]
name = "test-app"
version = "2.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
description = "Database connection"

[variables.PORT]
type = "int"
required = false
default = 8000

[variables.NEW_VAR]
type = "string"
required = true
default = "new_value"
"""
    schema_file = tmp_path / "schema-v2.toml"
    schema_file.write_text(content)
    return schema_file


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    """Create .env file."""
    content = """DATABASE_URL=postgresql://localhost:5432/db
PORT=8000
OLD_VAR=some_value
"""
    env_file = tmp_path / ".env"
    env_file.write_text(content)
    return env_file


class TestMigrationPlan:
    """Tests for creating migration plans."""

    def test_create_migration_plan(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test creating a migration plan."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        assert plan.old_schema is not None
        assert plan.new_schema is not None
        assert plan.diff is not None
        assert plan.env_file == env_file

    def test_migration_plan_detects_changes(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration plan detects all changes."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        # Should detect added, removed, and modified variables
        assert len(plan.diff.added_variables) > 0
        assert len(plan.diff.removed_variables) > 0
        assert len(plan.diff.modified_variables) > 0


class TestMigrationExecution:
    """Tests for executing migrations."""

    def test_dry_run_migration(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test dry run mode doesn't modify files."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        original_content = env_file.read_text()

        success, messages = plan.execute(dry_run=True, interactive=False)

        # File should not be modified in dry run
        assert env_file.read_text() == original_content
        assert success is True

    def test_migration_adds_new_variables(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration adds new variables."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # Check new variable was added
        updated_content = env_file.read_text()
        assert "NEW_VAR" in updated_content

    def test_migration_removes_deprecated_variables(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration removes deprecated variables."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # Check old variable was removed
        updated_content = env_file.read_text()
        assert "OLD_VAR" not in updated_content

    def test_migration_converts_types(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration converts types."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # PORT should be converted from string to int (value stays same)
        updated_content = env_file.read_text()
        assert "PORT=8000" in updated_content

    def test_migration_creates_backup(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration creates backup file."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        original_content = env_file.read_text()

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True
        assert plan.backup_file is not None
        assert plan.backup_file.exists()

        # Backup should have original content
        backup_content = plan.backup_file.read_text()
        assert backup_content == original_content

    def test_migration_with_defaults(self, tmp_path: Path) -> None:
        """Test migration adds variables with defaults."""
        # Schema with default values
        schema_v1_content = """
[project]
name = "test"

[variables.VAR1]
type = "string"
required = false
"""
        schema_v1 = tmp_path / "schema1.toml"
        schema_v1.write_text(schema_v1_content)

        schema_v2_content = """
[project]
name = "test"

[variables.VAR1]
type = "string"
required = false

[variables.VAR2]
type = "string"
required = false
default = "default_value"
"""
        schema_v2 = tmp_path / "schema2.toml"
        schema_v2.write_text(schema_v2_content)

        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\n")

        plan = create_migration_plan(schema_v1, schema_v2, env_file)
        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # VAR2 should be added with default
        updated_content = env_file.read_text()
        assert "VAR2=default_value" in updated_content

    def test_migration_required_without_default(self, tmp_path: Path) -> None:
        """Test migration adds placeholder for required variables without defaults."""
        schema_v1_content = """
[project]
name = "test"

[variables.VAR1]
type = "string"
required = false
"""
        schema_v1 = tmp_path / "schema1.toml"
        schema_v1.write_text(schema_v1_content)

        schema_v2_content = """
[project]
name = "test"

[variables.VAR1]
type = "string"
required = false

[variables.VAR2]
type = "string"
required = true
"""
        schema_v2 = tmp_path / "schema2.toml"
        schema_v2.write_text(schema_v2_content)

        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\n")

        plan = create_migration_plan(schema_v1, schema_v2, env_file)
        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # VAR2 should be added with CHANGE_ME placeholder
        updated_content = env_file.read_text()
        assert "VAR2=CHANGE_ME" in updated_content

    def test_migration_messages(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration returns descriptive messages."""
        plan = create_migration_plan(schema_v1, schema_v2, env_file)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True
        assert len(messages) > 0

        # Check for expected message patterns
        messages_text = " ".join(messages)
        assert "backup" in messages_text.lower() or "Migrated" in messages_text

    def test_migration_preserves_existing_values(self, schema_v1: Path, schema_v2: Path, env_file: Path) -> None:
        """Test that migration preserves existing variable values."""
        original_db_url = "postgresql://localhost:5432/db"

        plan = create_migration_plan(schema_v1, schema_v2, env_file)
        plan.execute(dry_run=False, interactive=False)

        updated_content = env_file.read_text()
        assert original_db_url in updated_content


class TestMigrationEdgeCases:
    """Tests for edge cases in migration."""

    def test_migration_missing_env_file(self, schema_v1: Path, schema_v2: Path, tmp_path: Path) -> None:
        """Test migration with missing .env file."""
        missing_env = tmp_path / "missing.env"

        plan = create_migration_plan(schema_v1, schema_v2, missing_env)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert not success
        assert any("not found" in msg for msg in messages)

    def test_migration_empty_env_file(self, schema_v1: Path, schema_v2: Path, tmp_path: Path) -> None:
        """Test migration with empty .env file."""
        empty_env = tmp_path / ".env"
        empty_env.write_text("")

        plan = create_migration_plan(schema_v1, schema_v2, empty_env)

        success, messages = plan.execute(dry_run=False, interactive=False)

        assert success is True

        # Should add new variables
        updated_content = empty_env.read_text()
        assert "NEW_VAR" in updated_content

    def test_migration_with_comments(self, schema_v1: Path, schema_v2: Path, tmp_path: Path) -> None:
        """Test migration preserves comments behavior."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """# Comment
DATABASE_URL=postgresql://localhost:5432/db
# Another comment
PORT=8000
OLD_VAR=value
"""
        )

        plan = create_migration_plan(schema_v1, schema_v2, env_file)
        plan.execute(dry_run=False, interactive=False)

        # Migration creates new file format (comments not preserved by default)
        updated_content = env_file.read_text()
        # Check that variables are still there
        assert "DATABASE_URL" in updated_content
        assert "PORT" in updated_content

    def test_type_conversion_failures(self, tmp_path: Path) -> None:
        """Test handling of type conversion failures."""
        schema_v1_content = """
[project]
name = "test"

[variables.VAR1]
type = "string"
required = false
"""
        schema_v1 = tmp_path / "schema1.toml"
        schema_v1.write_text(schema_v1_content)

        schema_v2_content = """
[project]
name = "test"

[variables.VAR1]
type = "int"
required = false
"""
        schema_v2 = tmp_path / "schema2.toml"
        schema_v2.write_text(schema_v2_content)

        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=not_a_number\n")

        plan = create_migration_plan(schema_v1, schema_v2, env_file)
        success, messages = plan.execute(dry_run=False, interactive=False)

        # Should succeed but warn about conversion failure
        assert success is True
        assert any("Could not convert" in msg for msg in messages)
