"""Tests for branding module."""

import re

import pytest

from tripwire.branding import (
    BRAND_COLORS,
    COLORS,
    LOGO_BANNER,
    LOGO_SIMPLE,
    get_status_icon,
    print_banner,
    print_status,
)


class TestColorConstants:
    """Tests for color constant dictionaries."""

    def test_colors_dict_completeness(self) -> None:
        """Test COLORS dict contains all required states plus control codes."""
        expected_keys = {"valid", "invalid", "warning", "neutral", "info", "reset", "bold"}
        assert set(COLORS.keys()) == expected_keys

    def test_colors_dict_values_are_ansi_codes(self) -> None:
        """Test all COLORS values are valid ANSI escape sequences."""
        for key, value in COLORS.items():
            assert value.startswith("\033["), f"COLORS[{key}] is not ANSI code: {value!r}"
            assert value.endswith("m"), f"COLORS[{key}] is not valid ANSI code: {value!r}"

    def test_brand_colors_dict_completeness(self) -> None:
        """Test BRAND_COLORS dict contains all required keys."""
        expected_keys = {
            "valid_green",
            "error_red",
            "warning_amber",
            "neutral_grey",
            "info_cyan",
            "bg_light",
            "bg_dark",
            "text_light",
            "text_dark",
        }
        assert set(BRAND_COLORS.keys()) == expected_keys

    def test_brand_colors_dict_values_are_hex_codes(self) -> None:
        """Test all BRAND_COLORS values are valid hex color codes."""
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for key, value in BRAND_COLORS.items():
            assert hex_pattern.match(value), f"BRAND_COLORS[{key}] is not hex: {value!r}"


class TestGetStatusIcon:
    """Tests for get_status_icon function."""

    # Valid states tests
    @pytest.mark.parametrize(
        "state,expected_symbol",
        [
            ("valid", "✓"),
            ("invalid", "✗"),
            ("warning", "!"),
            ("neutral", "○"),
            ("info", "ℹ"),
        ],
    )
    def test_get_status_icon_with_rich_markup(self, state: str, expected_symbol: str) -> None:
        """Test status icon with Rich markup for all states."""
        icon = get_status_icon(state, colored=True, rich_markup=True)
        assert f"({expected_symbol})" in icon
        assert icon.startswith("━━[")
        assert icon.endswith("]━━")

    @pytest.mark.parametrize(
        "state,expected_symbol",
        [
            ("valid", "✓"),
            ("invalid", "✗"),
            ("warning", "!"),
            ("neutral", "○"),
            ("info", "ℹ"),
        ],
    )
    def test_get_status_icon_with_ansi_codes(self, state: str, expected_symbol: str) -> None:
        """Test status icon with ANSI codes for all states."""
        icon = get_status_icon(state, colored=True, rich_markup=False)
        assert f"({expected_symbol})" in icon
        assert "\033[" in icon  # Has ANSI code
        assert icon.endswith("\033[0m━━")  # Ends with reset code

    @pytest.mark.parametrize(
        "state,expected_symbol",
        [
            ("valid", "✓"),
            ("invalid", "✗"),
            ("warning", "!"),
            ("neutral", "○"),
            ("info", "ℹ"),
        ],
    )
    def test_get_status_icon_monochrome(self, state: str, expected_symbol: str) -> None:
        """Test monochrome status icon (no colors)."""
        icon = get_status_icon(state, colored=False)
        assert icon == f"━━({expected_symbol})━━"
        assert "\033[" not in icon  # No ANSI codes
        assert "[" not in icon or "]" not in icon  # No Rich markup

    def test_get_status_icon_default_is_neutral(self) -> None:
        """Test default state is neutral."""
        icon = get_status_icon()
        assert "(○)" in icon

    def test_get_status_icon_rich_markup_colors(self) -> None:
        """Test Rich markup uses correct color names."""
        expected_colors = {
            "valid": "green",
            "invalid": "red",
            "warning": "yellow",
            "neutral": "bright_black",
            "info": "cyan",
        }
        for state, expected_color in expected_colors.items():
            icon = get_status_icon(state, rich_markup=True)
            assert f"[{expected_color}]" in icon
            assert f"[/{expected_color}]" in icon

    def test_get_status_icon_ansi_colors(self) -> None:
        """Test ANSI codes use correct color codes."""
        expected_ansi = {
            "valid": "\033[32m",
            "invalid": "\033[31m",
            "warning": "\033[33m",
            "neutral": "\033[90m",
            "info": "\033[36m",
        }
        for state, expected_code in expected_ansi.items():
            icon = get_status_icon(state, rich_markup=False)
            assert expected_code in icon

    # Invalid state tests
    def test_get_status_icon_invalid_state_raises_error(self) -> None:
        """Test invalid state raises ValueError."""
        with pytest.raises(ValueError, match="Invalid state: 'invalid_state'"):
            get_status_icon("invalid_state")

    def test_get_status_icon_invalid_state_error_message(self) -> None:
        """Test error message includes valid states."""
        with pytest.raises(
            ValueError,
            match=r"Must be one of: .*valid.*invalid.*warning.*neutral.*info",
        ) as exc_info:
            get_status_icon("bad_state")

        error_msg = str(exc_info.value)
        assert "valid" in error_msg
        assert "invalid" in error_msg
        assert "warning" in error_msg
        assert "neutral" in error_msg
        assert "info" in error_msg

    @pytest.mark.parametrize(
        "invalid_state",
        ["", "VALID", "Valid", "success", "error", "fail", "ok", "nope", "   ", "123"],
    )
    def test_get_status_icon_various_invalid_states(self, invalid_state: str) -> None:
        """Test various invalid state values raise ValueError."""
        with pytest.raises(ValueError):
            get_status_icon(invalid_state)

    # Edge cases
    def test_get_status_icon_colored_false_ignores_rich_markup(self) -> None:
        """Test colored=False produces same output regardless of rich_markup."""
        icon_rich = get_status_icon("valid", colored=False, rich_markup=True)
        icon_ansi = get_status_icon("valid", colored=False, rich_markup=False)
        assert icon_rich == icon_ansi
        assert icon_rich == "━━(✓)━━"

    def test_get_status_icon_info_state(self) -> None:
        """Test info state (production bug fix verification)."""
        # Test with ANSI codes
        icon_ansi = get_status_icon("info", rich_markup=False)
        assert "\033[36m" in icon_ansi  # Cyan ANSI code
        assert "(ℹ)" in icon_ansi

        # Test with Rich markup
        icon_rich = get_status_icon("info", rich_markup=True)
        assert "[cyan]" in icon_rich
        assert "(ℹ)" in icon_rich


class TestPrintBanner:
    """Tests for print_banner function."""

    def test_print_banner_output(self, capsys) -> None:
        """Test print_banner outputs LOGO_BANNER."""
        print_banner()
        captured = capsys.readouterr()
        assert LOGO_BANNER in captured.out

    def test_print_banner_contains_ascii_art(self, capsys) -> None:
        """Test banner contains expected ASCII art elements."""
        print_banner()
        captured = capsys.readouterr()
        assert "╔══" in captured.out
        assert "╚══" in captured.out
        assert "T R I P W I R E" in captured.out
        assert "(○)" in captured.out
        assert "Config validation" in captured.out
        assert "that fails fast" in captured.out


class TestPrintStatus:
    """Tests for print_status function."""

    @pytest.mark.parametrize(
        "state,expected_symbol",
        [
            ("valid", "✓"),
            ("invalid", "✗"),
            ("warning", "!"),
            ("neutral", "○"),
            ("info", "ℹ"),
        ],
    )
    def test_print_status_with_all_states(self, capsys, state: str, expected_symbol: str) -> None:
        """Test print_status with all valid states."""
        message = "Test message"
        print_status(message, state)
        captured = capsys.readouterr()
        assert expected_symbol in captured.out
        assert message in captured.out

    def test_print_status_default_state(self, capsys) -> None:
        """Test print_status defaults to neutral state."""
        print_status("Test")
        captured = capsys.readouterr()
        assert "(○)" in captured.out

    def test_print_status_colored_true(self, capsys) -> None:
        """Test print_status with colors enabled."""
        print_status("Test", "valid", colored=True)
        captured = capsys.readouterr()
        assert "\033[" in captured.out  # Has ANSI codes

    def test_print_status_colored_false(self, capsys) -> None:
        """Test print_status with colors disabled."""
        print_status("Test", "valid", colored=False)
        captured = capsys.readouterr()
        assert "\033[" not in captured.out  # No ANSI codes

    def test_print_status_invalid_state_raises_error(self) -> None:
        """Test print_status with invalid state raises ValueError."""
        with pytest.raises(ValueError, match="Invalid state"):
            print_status("Test", "invalid_state")

    def test_print_status_message_content(self, capsys) -> None:
        """Test print_status includes full message."""
        message = "DATABASE_URL is valid and properly formatted"
        print_status(message, "valid")
        captured = capsys.readouterr()
        assert message in captured.out

    def test_print_status_uses_ansi_codes_not_rich(self, capsys) -> None:
        """Test print_status uses ANSI codes (not Rich markup)."""
        print_status("Test", "valid", colored=True)
        captured = capsys.readouterr()
        # Should use ANSI codes
        assert "\033[" in captured.out
        # Should NOT use Rich markup
        assert "[green]" not in captured.out
        assert "[/green]" not in captured.out


class TestLogoConstants:
    """Tests for logo constants."""

    def test_logo_banner_is_multiline(self) -> None:
        """Test LOGO_BANNER is a multiline string."""
        assert "\n" in LOGO_BANNER
        assert LOGO_BANNER.count("\n") >= 7  # At least 7 lines

    def test_logo_banner_has_box_drawing(self) -> None:
        """Test LOGO_BANNER uses box-drawing characters."""
        assert "╔" in LOGO_BANNER
        assert "╚" in LOGO_BANNER
        assert "║" in LOGO_BANNER
        assert "═" in LOGO_BANNER

    def test_logo_simple_format(self) -> None:
        """Test LOGO_SIMPLE has expected format."""
        assert LOGO_SIMPLE == "━━(○)━━ tripwire"
        assert "(○)" in LOGO_SIMPLE
        assert "tripwire" in LOGO_SIMPLE


class TestColorConsistency:
    """Tests for consistency across color mappings."""

    def test_all_states_have_ansi_color(self) -> None:
        """Test all status states have corresponding ANSI color."""
        states = ["valid", "invalid", "warning", "neutral", "info"]
        for state in states:
            assert state in COLORS, f"Missing ANSI color for state: {state}"

    def test_colors_dict_type_safety(self) -> None:
        """Test COLORS dict values are strings."""
        for key, value in COLORS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_brand_colors_dict_type_safety(self) -> None:
        """Test BRAND_COLORS dict values are strings."""
        for key, value in BRAND_COLORS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestCoverage:
    """Tests to ensure high code coverage."""

    def test_get_status_icon_all_branches(self) -> None:
        """Test all code branches in get_status_icon."""
        # Branch: colored=True, rich_markup=True
        icon1 = get_status_icon("valid", colored=True, rich_markup=True)
        assert "[green]" in icon1

        # Branch: colored=True, rich_markup=False
        icon2 = get_status_icon("valid", colored=True, rich_markup=False)
        assert "\033[32m" in icon2

        # Branch: colored=False
        icon3 = get_status_icon("valid", colored=False)
        assert icon3 == "━━(✓)━━"

        # Branch: invalid state
        with pytest.raises(ValueError):
            get_status_icon("bad")

    def test_all_exported_functions(self) -> None:
        """Test all exported functions are callable."""
        assert callable(get_status_icon)
        assert callable(print_banner)
        assert callable(print_status)

    def test_all_constants_accessible(self) -> None:
        """Test all constants are accessible and have expected types."""
        assert isinstance(COLORS, dict)
        assert isinstance(BRAND_COLORS, dict)
        assert isinstance(LOGO_BANNER, str)
        assert isinstance(LOGO_SIMPLE, str)


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def test_get_status_icon_accepts_positional_args(self) -> None:
        """Test get_status_icon works with positional arguments."""
        icon = get_status_icon("valid", True, True)
        assert "[green]" in icon

    def test_print_status_accepts_positional_args(self, capsys) -> None:
        """Test print_status works with positional arguments."""
        print_status("Test", "valid", True)
        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_colors_dict_has_reset_and_bold(self) -> None:
        """Test COLORS includes control codes (reset, bold)."""
        assert "reset" in COLORS
        assert "bold" in COLORS
        assert COLORS["reset"] == "\033[0m"
        assert COLORS["bold"] == "\033[1m"
