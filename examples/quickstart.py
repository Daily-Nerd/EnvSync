"""EnvSync Quickstart - Your first EnvSync script.

This minimal example shows EnvSync's core value: fail-fast validation.
Perfect for learning the basics before diving into advanced features!

QUICK START:
1. Copy .env.example to .env:
   cp examples/.env.example examples/.env

2. Edit examples/.env and add this line:
   DATABASE_URL=postgresql://localhost:5432/mydb

3. Run this script:
   python examples/quickstart.py

WHAT YOU'LL LEARN:
- How to use env.require() for required variables
- How to use env.optional() with defaults
- How EnvSync validates at import time (fail-fast)

TIP: Want to see the helpful error messages? Remove .env and run again!
"""

import sys
from pathlib import Path

# Demo mode support - run with --demo flag to use example values
DEMO_MODE = "--demo" in sys.argv

if DEMO_MODE:
    print("🎭 Running in DEMO MODE with example values\n")
    import os

    os.environ.update(
        {
            "DATABASE_URL": "postgresql://localhost:5432/demo_db",
            "DEBUG": "true",
            "PORT": "8000",
        }
    )

# Now import EnvSync - this is where validation happens!
from envsync import env

# Example 1: Required variable
# This MUST be set in .env or the script will fail immediately with a helpful error
DATABASE_URL: str = env.require(
    "DATABASE_URL",
    description="PostgreSQL connection string",
    format="postgresql",
)

# Example 2: Optional boolean with default (always works!)
# Accepts: true/false, 1/0, yes/no, on/off
DEBUG: bool = env.optional(
    "DEBUG",
    default=False,
    type=bool,
    description="Enable debug mode",
)

# Example 3: Optional integer with default (always works!)
# Provides a sensible default if not specified
PORT: int = env.optional(
    "PORT",
    default=8000,
    type=int,
    min_val=1,
    max_val=65535,
    description="Server port",
)


def main() -> None:
    """Main function demonstrating the loaded configuration."""
    print("✅ EnvSync Quickstart Success!")
    print("=" * 60)
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"DEBUG:        {DEBUG}")
    print(f"PORT:         {PORT}")
    print("=" * 60)
    print("\n🎉 All environment variables validated successfully!")
    print("\nNext steps:")
    print("  1. Try changing DEBUG in .env to 'true' and run again")
    print("  2. Try removing .env to see the helpful error message")
    print("  3. Explore examples/basic_usage.py for advanced features")
    print("  4. Run with --demo flag to skip .env requirement:")
    print("     python examples/quickstart.py --demo")


if __name__ == "__main__":
    # Check if running in demo mode
    if not DEMO_MODE and not Path(".env").exists() and not Path("examples/.env").exists():
        print("\n💡 TIP: No .env file found.")
        print("   You can either:")
        print("   1. Create .env file (recommended for real usage)")
        print("   2. Run with --demo flag to use example values")
        print("\n   Try: python examples/quickstart.py --demo\n")

    main()
