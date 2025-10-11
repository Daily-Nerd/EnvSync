"""Unit tests for _infer_type_and_default function (v0.7.1 boolean fix)."""

import pytest

from tripwire.cli.commands.generate import _infer_type_and_default


class TestInferTypeAndDefault:
    """Test type inference from string values."""

    def test_boolean_true_patterns(self):
        """Test all boolean true patterns are recognized."""
        true_patterns = [
            "true",
            "True",
            "TRUE",
            "yes",
            "Yes",
            "YES",
            "on",
            "On",
            "ON",
            "enabled",
            "Enabled",
            "ENABLED",
            "1",
        ]

        for pattern in true_patterns:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "bool", f"'{pattern}' should be detected as bool"
            assert value is True, f"'{pattern}' should have value True"

    def test_boolean_false_patterns(self):
        """Test all boolean false patterns are recognized."""
        false_patterns = [
            "false",
            "False",
            "FALSE",
            "no",
            "No",
            "NO",
            "off",
            "Off",
            "OFF",
            "disabled",
            "Disabled",
            "DISABLED",
            "0",
        ]

        for pattern in false_patterns:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "bool", f"'{pattern}' should be detected as bool"
            assert value is False, f"'{pattern}' should have value False"

    def test_boolean_with_whitespace(self):
        """Test boolean patterns with surrounding whitespace."""
        patterns_with_whitespace = [
            ("  true  ", True),
            ("  false  ", False),
            ("\tyes\t", True),
            ("\nno\n", False),
            ("  ON  ", True),
            ("  OFF  ", False),
        ]

        for pattern, expected_value in patterns_with_whitespace:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "bool", f"'{pattern}' should be detected as bool"
            assert value is expected_value, f"'{pattern}' should have value {expected_value}"

    def test_integer_detection(self):
        """Test integer values are correctly detected (but not 0 or 1)."""
        integer_patterns = [
            ("42", 42),
            ("-10", -10),
            ("1000", 1000),
            ("2", 2),
            ("99", 99),
        ]

        for pattern, expected_value in integer_patterns:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "int", f"'{pattern}' should be detected as int"
            assert value == expected_value, f"'{pattern}' should have value {expected_value}"

    def test_zero_and_one_are_booleans(self):
        """Test that 0 and 1 are detected as booleans, not integers (v0.7.1 fix)."""
        # This is the key fix - "0" and "1" should be bool, not int
        type_name, value = _infer_type_and_default("1")
        assert type_name == "bool", "'1' should be detected as bool (not int)"
        assert value is True

        type_name, value = _infer_type_and_default("0")
        assert type_name == "bool", "'0' should be detected as bool (not int)"
        assert value is False

    def test_float_detection(self):
        """Test float values are correctly detected."""
        float_patterns = [
            ("3.14", 3.14),
            ("-2.5", -2.5),
            ("0.001", 0.001),
            ("100.99", 100.99),
        ]

        for pattern, expected_value in float_patterns:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "float", f"'{pattern}' should be detected as float"
            assert value == expected_value, f"'{pattern}' should have value {expected_value}"

    def test_string_detection(self):
        """Test string values are correctly detected."""
        string_patterns = [
            "hello",
            "world",
            "postgresql://localhost:5432/db",
            "https://example.com",
            "user@example.com",
            "sk-1234567890",
            "some_random_text",
            "",  # Empty string
        ]

        for pattern in string_patterns:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "string", f"'{pattern}' should be detected as string"
            assert value == pattern, f"'{pattern}' should retain original value"

    def test_edge_cases(self):
        """Test edge cases and potential ambiguities."""
        # Test that "10" is int, not bool (only 0/1 are booleans)
        type_name, value = _infer_type_and_default("10")
        assert type_name == "int"
        assert value == 10

        # Test that "2.0" is float, not bool
        type_name, value = _infer_type_and_default("2.0")
        assert type_name == "float"
        assert value == 2.0

        # Test that "yes!" is string (not exact match)
        type_name, value = _infer_type_and_default("yes!")
        assert type_name == "string"
        assert value == "yes!"

        # Test that "on-premise" is string (not exact match)
        type_name, value = _infer_type_and_default("on-premise")
        assert type_name == "string"
        assert value == "on-premise"

    def test_case_sensitivity(self):
        """Test that boolean detection is case insensitive."""
        # All these should be detected as bool
        case_variations = [
            ("TrUe", True),
            ("FaLsE", False),
            ("YeS", True),
            ("nO", False),
            ("eNaBlEd", True),
            ("dIsAbLeD", False),
        ]

        for pattern, expected_value in case_variations:
            type_name, value = _infer_type_and_default(pattern)
            assert type_name == "bool", f"'{pattern}' should be case-insensitive bool"
            assert value is expected_value

    def test_comprehensive_examples(self):
        """Test the exact examples from the bug report."""
        # From the bug report - these should all work now
        test_cases = [
            ("on", "bool", True),
            ("0", "bool", False),
            ("OFF", "bool", False),
            ("true", "bool", True),
            ("42", "int", 42),
            ("3.14", "float", 3.14),
            ("hello", "string", "hello"),
        ]

        for input_value, expected_type, expected_default in test_cases:
            type_name, default_value = _infer_type_and_default(input_value)
            assert type_name == expected_type, f"'{input_value}' should be {expected_type}, got {type_name}"
            assert (
                default_value == expected_default
            ), f"'{input_value}' should default to {expected_default}, got {default_value}"
