"""Console utilities for TripWire CLI.

Provides a shared Rich Console instance for formatted terminal output.
"""

from rich.console import Console

# On Windows, force UTF-8 encoding for Rich console to support Unicode characters
# Use legacy_windows=False to avoid the cp1252 encoding issue
console = Console(legacy_windows=False)

__all__ = ["console"]
