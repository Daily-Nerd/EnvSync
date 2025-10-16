"""Test suite for schema merge bug fixes (v0.12.3).

Tests for 3 critical bugs:
1. Custom validator prefix stripping (lines 643-648)
2. Code comment deletion (lines 824-902)
3. Phantom field injection (line 214)
"""

from pathlib import Path
from typing import Any

import pytest

from tripwire.schema import (
    CUSTOM_VALIDATOR_PREFIX,
    TripWireSchema,
    VariableSchema,
    _extract_toml_comments,
    _inject_toml_comments,
    _normalize_format,
    _preserve_custom_format_prefix,
    envvarinfo_to_variableschema,
    merge_variable_schemas,
    write_schema_to_toml,
)


class TestBug1CustomPrefixPreservation:
    """Test Bug #1: Custom validator prefix stripping during merge."""

    def test_normalize_format_strips_custom_prefix(self) -> None:
        """Test that _normalize_format strips custom: prefix correctly."""
        assert _normalize_format("custom:username") == "username"
        assert _normalize_format("email") == "email"
        assert _normalize_format(None) is None
        assert _normalize_format("") is None

    def test_preserve_custom_format_prefix_when_formats_match(self) -> None:
        """Test that custom: prefix is preserved when base formats match."""
        # Case 1: existing has custom:, new doesn't -> preserve custom:
        result = _preserve_custom_format_prefix("custom:username", "username")
        assert result == "custom:username"

        # Case 2: both have same format without prefix -> keep existing
        result = _preserve_custom_format_prefix("email", "email")
        assert result == "email"

        # Case 3: existing has custom:, new has custom: -> preserve existing
        result = _preserve_custom_format_prefix("custom:username", "custom:username")
        assert result == "custom:username"

    def test_preserve_custom_format_prefix_when_formats_differ(self) -> None:
        """Test that new format is used when base formats differ."""
        # Case 1: different formats -> use new
        result = _preserve_custom_format_prefix("custom:username", "email")
        assert result == "email"

        # Case 2: builtin to builtin change -> use new
        result = _preserve_custom_format_prefix("email", "postgresql")
        assert result == "postgresql"

    def test_merge_variable_preserves_custom_prefix(self) -> None:
        """Test that merge_variable_schemas preserves custom: prefix."""
        existing = VariableSchema(
            name="ADMIN_USERNAME",
            type="string",
            required=True,
            format="custom:username",  # Has custom: prefix
        )

        from_code = VariableSchema(
            name="ADMIN_USERNAME",
            type="string",
            required=True,
            format="username",  # Code scanner doesn't emit custom:
        )

        merged, changes = merge_variable_schemas(existing, from_code)

        # CRITICAL: custom: prefix must be preserved
        assert merged.format == "custom:username"
        # No change should be reported since formats match semantically
        assert not any("format" in change for change in changes)

    def test_merge_variable_updates_when_format_actually_changes(self) -> None:
        """Test that format is updated when it actually changes."""
        existing = VariableSchema(
            name="EMAIL",
            type="string",
            required=True,
            format="custom:username",
        )

        from_code = VariableSchema(
            name="EMAIL",
            type="string",
            required=True,
            format="email",  # Different format
        )

        merged, changes = merge_variable_schemas(existing, from_code)

        # Format should change to new value
        assert merged.format == "email"
        # Change should be reported
        assert any("format" in change for change in changes)

    def test_envvarinfo_adds_custom_prefix_for_non_builtin(self) -> None:
        """Test that envvarinfo_to_variableschema adds custom: prefix."""
        from dataclasses import dataclass
        from pathlib import Path

        # Mock EnvVarInfo with all required fields
        @dataclass
        class MockEnvVarInfo:
            name: str
            required: bool
            var_type: str
            default: Any
            description: str
            format: str
            pattern: str
            choices: list
            min_val: float
            max_val: float
            secret: bool
            file_path: Path
            line_number: int

        # Custom validator (not in _BUILTIN_VALIDATORS)
        env_var = MockEnvVarInfo(
            name="USERNAME",
            required=True,
            var_type="str",
            default=None,
            description="",
            format="username",  # Custom validator
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
            secret=False,
            file_path=Path("/test.py"),
            line_number=1,
        )

        schema = envvarinfo_to_variableschema(env_var)

        # Should have custom: prefix added automatically
        assert schema.format == "custom:username"

    def test_envvarinfo_no_prefix_for_builtin(self) -> None:
        """Test that builtin validators don't get custom: prefix."""
        from dataclasses import dataclass
        from pathlib import Path

        # Mock EnvVarInfo with all required fields
        @dataclass
        class MockEnvVarInfo:
            name: str
            required: bool
            var_type: str
            default: Any
            description: str
            format: str
            pattern: str
            choices: list
            min_val: float
            max_val: float
            secret: bool
            file_path: Path
            line_number: int

        # Builtin validator
        env_var = MockEnvVarInfo(
            name="EMAIL",
            required=True,
            var_type="str",
            default=None,
            description="",
            format="email",  # Builtin validator
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
            secret=False,
            file_path=Path("/test.py"),
            line_number=1,
        )

        schema = envvarinfo_to_variableschema(env_var)

        # Should NOT have custom: prefix
        assert schema.format == "email"


class TestBug2CommentPreservation:
    """Test Bug #2: Code comment deletion during TOML serialization."""

    def test_extract_toml_comments(self, tmp_path: Path) -> None:
        """Test that _extract_toml_comments extracts variable comments."""
        toml_content = """
[variables.ADMIN_USERNAME]
type = "string"
required = true
format = "custom:username"
# Found in: /path/to/file.py:149

[variables.APP_VERSION]
type = "string"
required = true
format = "custom:semantic_version"
# Found in: /path/to/file.py:150
# Additional comment
"""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text(toml_content)

        comments_map = _extract_toml_comments(toml_file)

        # Should extract comments for both variables
        assert "ADMIN_USERNAME" in comments_map
        assert len(comments_map["ADMIN_USERNAME"]) == 1
        assert "Found in: /path/to/file.py:149" in comments_map["ADMIN_USERNAME"][0]

        assert "APP_VERSION" in comments_map
        assert len(comments_map["APP_VERSION"]) == 2
        assert any("file.py:150" in c for c in comments_map["APP_VERSION"])

    def test_extract_toml_comments_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that _extract_toml_comments returns empty dict for missing file."""
        missing_file = tmp_path / "nonexistent.toml"
        comments_map = _extract_toml_comments(missing_file)
        assert comments_map == {}

    def test_inject_toml_comments(self) -> None:
        """Test that _inject_toml_comments re-injects comments correctly."""
        toml_content = """[variables.USERNAME]
type = "string"
required = true

[variables.EMAIL]
type = "string"
required = true
format = "email"
"""

        comments_map = {
            "USERNAME": ["# Found in: /app/config.py:10"],
            "EMAIL": ["# Found in: /app/config.py:11", "# Validated with email format"],
        }

        result = _inject_toml_comments(toml_content, comments_map)

        # Comments should be injected after variable definitions
        assert "# Found in: /app/config.py:10" in result
        assert "# Found in: /app/config.py:11" in result
        assert "# Validated with email format" in result

        # Check positioning: comments should be after fields
        lines = result.split("\n")
        username_idx = next(i for i, line in enumerate(lines) if "[variables.USERNAME]" in line)
        comment_idx = next(i for i, line in enumerate(lines) if "/app/config.py:10" in line)
        assert comment_idx > username_idx

    def test_write_schema_preserves_comments(self, tmp_path: Path) -> None:
        """Test that write_schema_to_toml preserves existing comments."""
        # Create initial schema with comments
        initial_content = """[project]
name = "test-project"

[validation]
strict = true
allow_missing_optional = true

[security]
entropy_threshold = 4.5
scan_git_history = true

[variables.USERNAME]
type = "string"
required = true
format = "custom:username"
# Found in: /app/config.py:10

[variables.EMAIL]
type = "string"
required = true
format = "email"
# Found in: /app/config.py:15
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(initial_content)

        # Load schema, modify it, and write back
        schema = TripWireSchema.from_toml(schema_file)

        # Add a new variable
        schema.variables["NEW_VAR"] = VariableSchema(
            name="NEW_VAR",
            type="string",
            required=False,
        )

        # Write schema (should preserve existing comments)
        write_schema_to_toml(schema, schema_file)

        # Read back and verify comments are preserved
        final_content = schema_file.read_text()

        assert "# Found in: /app/config.py:10" in final_content
        assert "# Found in: /app/config.py:15" in final_content


class TestBug3PhantomFieldInjection:
    """Test Bug #3: Phantom field injection for warn_unused."""

    def test_schema_warn_unused_default_is_none(self) -> None:
        """Test that TripWireSchema.warn_unused defaults to None."""
        schema = TripWireSchema()
        assert schema.warn_unused is None

    def test_schema_from_toml_preserves_absent_warn_unused(self, tmp_path: Path) -> None:
        """Test that loading TOML without warn_unused leaves it as None."""
        toml_content = """[project]
name = "test"

[validation]
strict = true
allow_missing_optional = true
# NO warn_unused field

[security]
entropy_threshold = 4.5
scan_git_history = true
"""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text(toml_content)

        schema = TripWireSchema.from_toml(toml_file)

        # warn_unused should be None (not injected)
        assert schema.warn_unused is None

    def test_schema_from_toml_reads_explicit_warn_unused(self, tmp_path: Path) -> None:
        """Test that explicit warn_unused value is read correctly."""
        toml_content = """[project]
name = "test"

[validation]
strict = true
allow_missing_optional = true
warn_unused = true

[security]
entropy_threshold = 4.5
scan_git_history = true
"""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text(toml_content)

        schema = TripWireSchema.from_toml(toml_file)

        # warn_unused should be True (explicitly set)
        assert schema.warn_unused is True

    def test_write_schema_skips_none_warn_unused(self, tmp_path: Path) -> None:
        """Test that write_schema_to_toml skips warn_unused when None."""
        schema = TripWireSchema(
            project_name="test",
            strict=True,
            allow_missing_optional=True,
            warn_unused=None,  # Explicitly None
        )

        schema_file = tmp_path / "test.toml"
        write_schema_to_toml(schema, schema_file)

        content = schema_file.read_text()

        # warn_unused should NOT appear in output
        assert "warn_unused" not in content

    def test_write_schema_includes_explicit_warn_unused(self, tmp_path: Path) -> None:
        """Test that write_schema_to_toml includes warn_unused when set."""
        schema = TripWireSchema(
            project_name="test",
            strict=True,
            allow_missing_optional=True,
            warn_unused=True,  # Explicitly set
        )

        schema_file = tmp_path / "test.toml"
        write_schema_to_toml(schema, schema_file)

        content = schema_file.read_text()

        # warn_unused SHOULD appear in output
        assert "warn_unused = true" in content


class TestIntegrationAllBugsFixed:
    """Integration tests verifying all 3 bugs are fixed together."""

    def test_full_merge_workflow_preserves_everything(self, tmp_path: Path) -> None:
        """Test complete merge workflow with all 3 bug scenarios."""
        # Create initial schema with all 3 bug conditions
        initial_content = """[project]
name = "production-app"
version = "2.1.0"
description = "Production application"

[validation]
strict = true
allow_missing_optional = true
# NO warn_unused - should stay absent

[security]
entropy_threshold = 4.5
scan_git_history = true

[variables.ADMIN_USERNAME]
type = "string"
required = true
format = "custom:username"
description = "Admin username"
# Found in: /app/validators.py:149

[variables.APP_VERSION]
type = "string"
required = true
format = "custom:semantic_version"
description = "App version"
# Found in: /app/validators.py:150

[variables.EMAIL]
type = "string"
required = true
format = "email"
# Found in: /app/config.py:10
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(initial_content)

        # Load schema
        schema = TripWireSchema.from_toml(schema_file)

        # Verify Bug #3 fix: warn_unused is None
        assert schema.warn_unused is None

        # Simulate merge: update existing variable and add new one
        schema.variables["EMAIL"] = VariableSchema(
            name="EMAIL",
            type="string",
            required=False,  # Changed
            format="email",
        )

        schema.variables["NEW_FIELD"] = VariableSchema(
            name="NEW_FIELD",
            type="int",
            required=True,
        )

        # Write back
        write_schema_to_toml(schema, schema_file)

        # Read final content
        final_content = schema_file.read_text()

        # Verify Bug #1 fix: custom: prefix preserved
        assert 'format = "custom:username"' in final_content
        assert 'format = "custom:semantic_version"' in final_content

        # Verify Bug #2 fix: comments preserved
        assert "# Found in: /app/validators.py:149" in final_content
        assert "# Found in: /app/validators.py:150" in final_content
        assert "# Found in: /app/config.py:10" in final_content

        # Verify Bug #3 fix: warn_unused NOT injected
        assert "warn_unused" not in final_content

        # Verify other fields preserved
        assert 'name = "production-app"' in final_content
        assert 'version = "2.1.0"' in final_content
