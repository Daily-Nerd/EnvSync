"""Branding and visual identity for TripWire.

This module provides ASCII art logos, color codes, and status indicators
for consistent branding across CLI, documentation, and terminal output.
"""

# ANSI color codes for terminal output
COLORS = {
    "valid": "\033[32m",  # Green
    "invalid": "\033[31m",  # Red
    "warning": "\033[33m",  # Yellow/Amber
    "neutral": "\033[90m",  # Grey
    "reset": "\033[0m",  # Reset
    "bold": "\033[1m",  # Bold
}

# Brand colors (hex codes for web/documentation)
BRAND_COLORS = {
    "valid_green": "#2E7D32",
    "error_red": "#C62828",
    "warning_amber": "#FFC107",
    "neutral_grey": "#455A64",
    "bg_light": "#FAFAFA",
    "bg_dark": "#121212",
    "text_light": "#212121",
    "text_dark": "#E0E0E0",
}


def get_status_icon(state: str = "neutral", colored: bool = True, rich_markup: bool = True) -> str:
    """Get status icon for terminal output.

    Args:
        state: One of "valid", "invalid", "warning", "neutral"
        colored: If True, use colors; if False, monochrome
        rich_markup: If True, use Rich markup format; if False, use ANSI codes

    Returns:
        Formatted status icon string

    Examples:
        >>> get_status_icon("valid", rich_markup=True)
        '━━[green](✓)[/green]━━'
        >>> get_status_icon("invalid", colored=False)
        '━━(✗)━━'
    """
    symbols = {
        "valid": "✓",
        "invalid": "✗",
        "warning": "!",
        "neutral": "○",
    }

    # Rich color names
    rich_colors = {
        "valid": "green",
        "invalid": "red",
        "warning": "yellow",
        "neutral": "bright_black",
    }

    symbol = symbols.get(state, symbols["neutral"])

    if not colored:
        return f"━━({symbol})━━"

    if rich_markup:
        # Use Rich markup format for console.print()
        color = rich_colors.get(state, rich_colors["neutral"])
        return f"━━[{color}]({symbol})[/{color}]━━"
    else:
        # Use ANSI codes for direct print()
        color = COLORS.get(state, COLORS["neutral"])
        reset = COLORS["reset"]
        return f"━━{color}({symbol}){reset}━━"


# ASCII art logo banner
LOGO_BANNER = """
╔══════════════════════════╗
║      ━━━━━(○)━━━━━       ║
║                          ║
║     T R I P W I R E      ║
║                          ║
║    Config validation     ║
║     that fails fast      ║
╚══════════════════════════╝
"""

LOGO_SIMPLE = "━━(○)━━ tripwire"


def print_banner() -> None:
    """Print the TripWire ASCII art banner."""
    print(LOGO_BANNER)


def print_status(message: str, state: str = "neutral", colored: bool = True) -> None:
    """Print a status message with icon.

    Args:
        message: The message to print
        state: Status state (valid/invalid/warning/neutral)
        colored: Whether to use colors

    Example:
        >>> print_status("DATABASE_URL is valid", "valid")
        ━━(✓)━━ DATABASE_URL is valid
    """
    icon = get_status_icon(state, colored)
    print(f"{icon} {message}")
