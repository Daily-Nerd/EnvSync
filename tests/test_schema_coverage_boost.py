"""
Comprehensive test coverage for schema.py module.

This test file targets previously uncovered edge cases and error paths
to bring schema.py coverage from 92% to near-perfect levels.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pytest

from tripwire.schema import (
    CUSTOM_VALIDATOR_PREFIX,
    TripWireSchema,
    VariableSchema,
    _compute_field_diffs,
    _escape_toml_string,
    _extract_toml_comments,
    _inject_toml_comments,
    _normalize_format,
    _preserve_custom_format_prefix,
    _serialize_toml_value,
    _write_toml_section,
    _write_variable_with_comments,
    build_source_comments_from_envvarinfo,
    envvarinfo_to_variableschema,
    load_existing_schema_safe,
    make_path_relative,
    merge_schemas,
    merge_variable_schemas,
    write_schema_to_toml,
)

# ============================================================================
# Test VariableSchema.validate() - Error Paths
# ============================================================================


class TestVariableSchemaValidationErrors:
    """Test validation error paths in VariableSchema.validate()."""

    def test_string_type_with_non_string_value(self):
        """Line 57: Test string validation with non-string value."""
        schema = VariableSchema(name="TEST", type="string")
        is_valid, error = schema.validate(123)
        assert not is_valid
        assert "Expected string, got int" in error

    def test_float_coercion_error(self):
        """Lines 89-90: Test float coercion failure."""
        schema = VariableSchema(name="TEST", type="float")
        # Pass an object that can't be coerced to float
        is_valid, error = schema.validate({"key": "value"})
        assert not is_valid
        assert error  # Should have error message from coerce_float

    def test_bool_coercion_error(self):
        """Lines 101-102: Test bool coercion failure."""
        schema = VariableSchema(name="TEST", type="bool")
        # Pass invalid bool value
        is_valid, error = schema.validate("maybe")
        assert not is_valid
        assert error  # Should have error message from coerce_bool

    def test_dict_coercion_error(self):
        """Lines 113-114: Test dict coercion failure."""
        schema = VariableSchema(name="TEST", type="dict")
        # Pass invalid dict format
        is_valid, error = schema.validate("not:a:valid:dict")
        assert not is_valid
        assert error  # Should have error message from coerce_dict

    def test_unknown_type_error(self):
        """Line 117: Test unknown type validation."""
        schema = VariableSchema(name="TEST", type="custom_type")
        is_valid, error = schema.validate("value")
        assert not is_valid
        assert "Unknown type: custom_type" in error

    def test_validate_format_empty_format(self):
        """Line 147: Test _validate_format with empty format string."""
        schema = VariableSchema(name="TEST", type="string", format="")
        # Empty format should return False in _validate_format
        result = schema._validate_format("test@example.com")
        assert result is False


# ============================================================================
# Test TripWireSchema - Error Paths and Edge Cases
# ============================================================================


class TestTripWireSchemaEdgeCases:
    """Test TripWireSchema edge cases and error paths."""

    def test_from_toml_file_not_found(self, tmp_path):
        """Line 195: Test from_toml with non-existent file."""
        non_existent = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError, match="Schema file not found"):
            TripWireSchema.from_toml(non_existent)

    def test_generate_env_for_environment_with_secret_interactive(self):
        """Lines 389: Test generate_env_for_environment with interactive secret."""
        schema = TripWireSchema()
        schema.variables["SECRET_KEY"] = VariableSchema(
            name="SECRET_KEY", type="string", required=True, secret=True, description="Secret key"
        )

        env_content, needs_input = schema.generate_env_for_environment(environment="production", interactive=True)

        assert "SECRET_KEY=PROMPT_ME" in env_content
        assert ("SECRET_KEY", "Secret key") in needs_input

    def test_generate_env_for_environment_with_required_no_default(self):
        """Line 402-403: Test required variable without default."""
        schema = TripWireSchema()
        schema.variables["REQUIRED_VAR"] = VariableSchema(
            name="REQUIRED_VAR", type="string", required=True, secret=False
        )

        env_content, needs_input = schema.generate_env_for_environment()

        assert "REQUIRED_VAR=" in env_content
        assert ("REQUIRED_VAR", "") in needs_input

    def test_generate_env_for_environment_with_bool_value(self):
        """Line 407: Test boolean value formatting."""
        schema = TripWireSchema()
        schema.variables["DEBUG"] = VariableSchema(name="DEBUG", type="bool", required=True, default=True)

        env_content, _ = schema.generate_env_for_environment()
        assert "DEBUG=true" in env_content

    def test_format_variable_with_default_value(self):
        """Line 436: Test _format_variable with default value."""
        schema = TripWireSchema()
        var = VariableSchema(name="PORT", type="int", default=8080)

        lines = schema._format_variable(var)
        assert any("PORT=8080" in line for line in lines)

    def test_format_variable_with_min_only(self):
        """Lines 476->478: Test _format_variable with min but no max."""
        schema = TripWireSchema()
        var = VariableSchema(name="PORT", type="int", min=1000, max=None)  # Explicitly no max

        lines = schema._format_variable(var)
        # Should include "min: 1000" in range info
        range_line = [l for l in lines if "Range:" in l]
        assert len(range_line) > 0
        assert "min: 1000" in range_line[0]

    def test_format_variable_with_max_only(self):
        """Lines 478->480: Test _format_variable with max but no min."""
        schema = TripWireSchema()
        var = VariableSchema(name="PORT", type="int", min=None, max=9999)  # Explicitly no min

        lines = schema._format_variable(var)
        # Should include "max: 9999" in range info
        range_line = [l for l in lines if "Range:" in l]
        assert len(range_line) > 0
        assert "max: 9999" in range_line[0]


# ============================================================================
# Test Schema Merge Functions - Error Paths
# ============================================================================


class TestSchemaMergeFunctions:
    """Test schema merge function edge cases."""

    def test_load_existing_schema_safe_corrupt_file(self, tmp_path):
        """Lines 585-587: Test load_existing_schema_safe with corrupt TOML."""
        corrupt_toml = tmp_path / "corrupt.toml"
        corrupt_toml.write_text("this is not valid [ TOML")

        result = load_existing_schema_safe(corrupt_toml)
        assert result is None  # Should return None, not raise

    def test_compute_field_diffs_pattern_change(self):
        """Lines 700-701: Test pattern field change detection."""
        existing = VariableSchema(name="EMAIL", type="string", pattern=r"^[a-z]+@[a-z]+\.[a-z]+$")
        from_code = VariableSchema(name="EMAIL", type="string", pattern=r"^[\w.-]+@[\w.-]+\.\w+$")

        field_diffs, changes = _compute_field_diffs(existing, from_code)
        assert "pattern" in field_diffs
        assert "pattern changed" in changes

    def test_compute_field_diffs_choices_change(self):
        """Lines 705-706: Test choices field change detection."""
        existing = VariableSchema(name="ENV", type="string", choices=["dev", "prod"])
        from_code = VariableSchema(name="ENV", type="string", choices=["dev", "staging", "prod"])

        field_diffs, changes = _compute_field_diffs(existing, from_code)
        assert "choices" in field_diffs
        assert "choices changed" in changes

    def test_compute_field_diffs_description_added(self):
        """Lines 725-726: Test description addition detection."""
        existing = VariableSchema(name="API_KEY", type="string", description="")  # No description
        from_code = VariableSchema(name="API_KEY", type="string", description="API key for authentication")

        field_diffs, changes = _compute_field_diffs(existing, from_code)
        assert "description" in field_diffs
        assert "description added from code" in changes

    def test_merge_schemas_preserves_all_sections(self):
        """Lines 814, 815->817, 817->821: Test merge preserves metadata."""
        existing = TripWireSchema(
            project_name="MyProject",
            project_version="1.0.0",
            project_description="Test project",
            strict=True,
            entropy_threshold=4.5,
            environments={"prod": {"DEBUG": "false"}},
        )

        new_vars = {"NEW_VAR": VariableSchema(name="NEW_VAR", type="string")}

        result = merge_schemas(existing, new_vars)

        # Check preserved sections
        assert "[project]" in result.preserved_sections
        assert any("environments" in s for s in result.preserved_sections)
        assert "[validation]" in result.preserved_sections
        assert "[security]" in result.preserved_sections


# ============================================================================
# Test Path and Comment Utilities
# ============================================================================


class TestPathUtilities:
    """Test path manipulation and comment utilities."""

    def test_make_path_relative_with_exception(self):
        """Lines 918-925: Test make_path_relative exception handling."""
        # Test with invalid path that triggers exception
        result = make_path_relative("\x00invalid\x00path")
        # Should fallback to original path on exception
        assert result == "\x00invalid\x00path"

    def test_make_path_relative_already_relative(self):
        """Line 906: Test make_path_relative with already relative path."""
        import os

        result = make_path_relative("src/config.py")
        # Normalize for platform (Windows uses backslash, Unix uses forward slash)
        expected = os.path.join("src", "config.py")
        assert result == expected

    def test_make_path_relative_outside_project(self):
        """Lines 897->900: Test make_path_relative with path outside project."""
        import os

        # Use platform-appropriate paths
        if os.name == "nt":  # Windows
            # Test with Windows-style absolute path
            system_path = r"C:\Python\Lib\site-packages\pkg\mod.py"
            reference = Path(r"C:\Users\project")
        else:  # Unix/Linux/macOS
            system_path = "/usr/lib/python3.11/site-packages/pkg/mod.py"
            reference = Path("/home/user/project")

        result = make_path_relative(system_path, reference)
        # Should return the original path when outside reference (may be normalized)
        # Use Path to normalize for comparison
        assert Path(result) == Path(system_path)

    def test_build_source_comments_from_envvarinfo(self):
        """Test build_source_comments_from_envvarinfo."""

        @dataclass
        class MockEnvVarInfo:
            file_path: str
            line_number: int

        unique_vars = {"API_KEY": MockEnvVarInfo("/abs/path/src/config.py", 42)}

        comments = build_source_comments_from_envvarinfo(unique_vars)
        assert "API_KEY" in comments
        assert len(comments["API_KEY"]) == 1
        assert ":" in comments["API_KEY"][0]  # Should have line number

    def test_envvarinfo_to_variableschema_with_custom_validator(self):
        """Lines 995->998: Test envvarinfo_to_variableschema with custom validator."""

        @dataclass
        class MockEnvVarInfo:
            name: str
            var_type: str
            required: bool
            default: str
            description: str
            secret: bool
            format: str
            pattern: str
            choices: List[str]
            min_val: int
            max_val: int

        env_var = MockEnvVarInfo(
            name="USERNAME",
            var_type="str",
            required=True,
            default=None,
            description="Username",
            secret=False,
            format="custom_username_validator",  # Not in builtins
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
        )

        schema = envvarinfo_to_variableschema(env_var)
        # Should add custom: prefix for non-builtin validators
        assert schema.format.startswith(CUSTOM_VALIDATOR_PREFIX)
        assert "custom_username_validator" in schema.format


# ============================================================================
# Test TOML Comment Extraction and Injection
# ============================================================================


class TestTomlCommentHandling:
    """Test TOML comment extraction and injection."""

    def test_extract_toml_comments_with_no_match(self, tmp_path):
        """Lines 1054->1043: Test comment extraction with regex no match."""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text(
            """
[variables.INVALID[BRACKET]
type = "string"
# This variable has invalid bracket in name
"""
        )

        comments = _extract_toml_comments(toml_file)
        # Should handle gracefully even with invalid variable name
        assert isinstance(comments, dict)

    def test_extract_toml_comments_with_exception(self, tmp_path):
        """Lines 1074-1077: Test comment extraction exception handling."""
        toml_file = tmp_path / "test.toml"
        # Create file with permission issues or encoding issues
        toml_file.write_bytes(b"\xff\xfe Invalid UTF-8")

        comments = _extract_toml_comments(toml_file)
        # Should return empty dict on exception
        assert comments == {}

    def test_inject_toml_comments_empty_map(self):
        """Line 1111: Test _inject_toml_comments with empty comments_map."""
        toml_content = '[variables.TEST]\ntype = "string"\n'
        result = _inject_toml_comments(toml_content, {})
        assert result == toml_content  # Should return unchanged

    def test_inject_toml_comments_no_match(self):
        """Lines 1124->1117: Test _inject_toml_comments with no regex match."""
        toml_content = '[variables.INVALID[BRACKET]\ntype = "string"\n'
        comments_map = {"TEST": ["# Found in: test.py:1"]}

        result = _inject_toml_comments(toml_content, comments_map)
        # Should handle gracefully
        assert isinstance(result, str)


# ============================================================================
# Test TOML Serialization Edge Cases
# ============================================================================


class TestTomlSerialization:
    """Test TOML serialization edge cases."""

    def test_serialize_toml_value_dict(self):
        """Lines 1188-1196: Test _serialize_toml_value with dict."""
        value = {"key1": "value1", "key2": 123, "key3": True}
        result = _serialize_toml_value(value)
        assert 'key1 = "value1"' in result
        assert "key2 = 123" in result
        assert "key3 = true" in result
        assert result.startswith("{ ")
        assert result.endswith(" }")

    def test_serialize_toml_value_fallback(self):
        """Line 1196: Test _serialize_toml_value fallback for unknown type."""

        # Test with custom object
        class CustomObj:
            def __str__(self):
                return "custom_value"

        result = _serialize_toml_value(CustomObj())
        assert "custom_value" in result
        assert result.startswith('"')
        assert result.endswith('"')

    def test_write_toml_section_empty_data(self):
        """Line 1216: Test _write_toml_section with empty data."""
        from io import StringIO

        buffer = StringIO()
        _write_toml_section(buffer, "test", {}, "Test Section")
        # Should write nothing for empty data
        assert buffer.getvalue() == ""

    def test_write_toml_section_with_fallback_type(self):
        """Line 1239: Test _write_toml_section with unknown value type."""
        from io import StringIO

        class CustomType:
            def __str__(self):
                return "custom"

        buffer = StringIO()
        data = {"key": CustomType()}
        _write_toml_section(buffer, "test", data)

        result = buffer.getvalue()
        assert "[test]" in result
        assert "key = custom" in result

    def test_write_schema_to_toml_without_project_section(self, tmp_path):
        """Lines 1356->1358: Test write_schema_to_toml without project metadata."""
        schema = TripWireSchema()
        # Add a variable but no project metadata
        schema.variables["TEST"] = VariableSchema(name="TEST", type="string")

        output_file = tmp_path / "test.toml"
        write_schema_to_toml(schema, output_file)

        content = output_file.read_text()
        # Should not have [project] section
        assert "[project]" not in content
        assert "[variables.TEST]" in content


# ============================================================================
# Run Coverage Report
# ============================================================================


class TestRemainingEdgeCases:
    """Additional edge case tests for remaining uncovered lines."""

    def test_envvarinfo_to_variableschema_unknown_type(self):
        """Lines 922-925: Test TYPE_MAPPING fallback."""

        @dataclass
        class MockEnvVarInfo:
            name: str
            var_type: str
            required: bool
            default: None
            description: str
            secret: bool
            format: None
            pattern: None
            choices: None
            min_val: None
            max_val: None

        env_var = MockEnvVarInfo(
            name="TEST",
            var_type="unknown_type",  # Not in TYPE_MAPPING
            required=False,
            default=None,
            description="",
            secret=False,
            format=None,
            pattern=None,
            choices=None,
            min_val=None,
            max_val=None,
        )

        schema = envvarinfo_to_variableschema(env_var)
        # Should fallback to "string" for unknown types
        assert schema.type == "string"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=tripwire.schema", "--cov-report=term-missing"])
