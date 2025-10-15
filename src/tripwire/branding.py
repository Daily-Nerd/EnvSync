"""Branding and visual identity for TripWire.

This module provides ASCII art logos, color codes, and status indicators
for consistent branding across CLI, documentation, and terminal output.

Usage Examples:
    >>> from tripwire.branding import get_status_icon, print_status
    >>>
    >>> # Get status icons with Rich markup (for use with rich.console)
    >>> icon = get_status_icon("valid", rich_markup=True)
    >>> print(icon)  # Output: ━━[green](✓)[/green]━━
    >>>
    >>> # Get status icons with ANSI codes (for direct print())
    >>> icon = get_status_icon("invalid", rich_markup=False)
    >>> print(icon)  # Output: ━━\033[31m(✗)\033[0m━━
    >>>
    >>> # Print status messages
    >>> print_status("DATABASE_URL is valid", "valid")
    >>>
    >>> # Monochrome output (no colors)
    >>> icon = get_status_icon("warning", colored=False)
    >>> print(icon)  # Output: ━━(!)━━

Color Systems:
    COLORS: ANSI terminal escape codes for CLI output (e.g., "\\033[32m" for green)
    BRAND_COLORS: Hex color codes for web/documentation (e.g., "#2E7D32" for green)
"""

from typing import Final, Literal

# Type alias for valid status states
StatusState = Literal["valid", "invalid", "warning", "neutral", "info"]

# ANSI color codes for terminal output
# These are escape sequences interpreted by terminal emulators to display colors
COLORS: Final[dict[str, str]] = {
    "valid": "\033[32m",  # Green
    "invalid": "\033[31m",  # Red
    "warning": "\033[33m",  # Yellow/Amber
    "neutral": "\033[90m",  # Grey
    "info": "\033[36m",  # Cyan
    "reset": "\033[0m",  # Reset
    "bold": "\033[1m",  # Bold
}

# Brand colors (hex codes for web/documentation)
# These are hex color codes used in documentation, web interfaces, and design assets
BRAND_COLORS: Final[dict[str, str]] = {
    "valid_green": "#2E7D32",
    "error_red": "#C62828",
    "warning_amber": "#FFC107",
    "neutral_grey": "#455A64",
    "info_cyan": "#00ACC1",
    "bg_light": "#FAFAFA",
    "bg_dark": "#121212",
    "text_light": "#212121",
    "text_dark": "#E0E0E0",
}

# Symbol mapping for status icons
# Module-level constant for performance and type safety
_SYMBOLS: Final[dict[StatusState, str]] = {
    "valid": "✓",
    "invalid": "✗",
    "warning": "!",
    "neutral": "○",
    "info": "ℹ",
}

# Rich color names for Rich library markup
# Module-level constant for performance and type safety
_RICH_COLORS: Final[dict[StatusState, str]] = {
    "valid": "green",
    "invalid": "red",
    "warning": "yellow",
    "neutral": "bright_black",
    "info": "cyan",
}


def get_status_icon(state: str = "neutral", colored: bool = True, rich_markup: bool = True) -> str:
    """Get status icon for terminal output.

    Args:
        state: One of "valid", "invalid", "warning", "neutral", "info"
        colored: If True, use colors; if False, monochrome
        rich_markup: If True, use Rich markup format; if False, use ANSI codes

    Returns:
        Formatted status icon string

    Raises:
        ValueError: If state is not a valid status state

    Examples:
        >>> get_status_icon("valid", rich_markup=True)
        '━━[green](✓)[/green]━━'
        >>> get_status_icon("invalid", colored=False)
        '━━(✗)━━'
        >>> get_status_icon("info", rich_markup=False)
        '━━\033[36m(ℹ)\033[0m━━'
    """
    # Validate state parameter
    if state not in _SYMBOLS:
        valid_states = ", ".join(f'"{s}"' for s in _SYMBOLS.keys())
        raise ValueError(f"Invalid state: '{state}'. Must be one of: {valid_states}")

    symbol = _SYMBOLS[state]  # type: ignore[index]  # We validated state above

    if not colored:
        return f"━━({symbol})━━"

    if rich_markup:
        # Use Rich markup format for console.print()
        color = _RICH_COLORS[state]  # type: ignore[index]  # We validated state above
        return f"━━[{color}]({symbol})[/{color}]━━"
    else:
        # Use ANSI codes for direct print()
        color = COLORS[state]
        reset = COLORS["reset"]
        return f"━━{color}({symbol}){reset}━━"


# ASCII art logo banner
LOGO_BANNER = """
╔═════════════════════════╗
║      ━━━━━(○)━━━━━      ║
║                         ║
║     T R I P W I R E     ║
║                         ║
║    Config validation    ║
║     that fails fast     ║
╚═════════════════════════╝
"""

LOGO_SIMPLE = "━━(○)━━ tripwire"


def print_banner() -> None:
    """Print the TripWire ASCII art banner."""
    print(LOGO_BANNER)


def print_status(message: str, state: str = "neutral", colored: bool = True) -> None:
    """Print a status message with icon.

    Args:
        message: The message to print
        state: Status state (valid/invalid/warning/neutral/info)
        colored: Whether to use colors

    Raises:
        ValueError: If state is not a valid status state

    Example:
        >>> print_status("DATABASE_URL is valid", "valid")
        ━━(✓)━━ DATABASE_URL is valid
    """
    icon = get_status_icon(state, colored, rich_markup=False)
    print(f"{icon} {message}")
