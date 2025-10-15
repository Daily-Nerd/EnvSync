"""Example: Basic env.require() usage

This example demonstrates TripWire's basic env.require() method for
required environment variables with import-time validation.

README Reference: Basic Usage section

Expected behavior:
- If DATABASE_URL is set: Returns the value
- If DATABASE_URL is not set: Raises ValidationError at import time

Run this example:
    export DATABASE_URL="postgresql://localhost/mydb"
    python examples/basic/01_simple_require.py

Or use demo mode:
    python examples/basic/01_simple_require.py --demo
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate basic env.require() usage."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["DATABASE_URL"] = "postgresql://localhost/demo_db"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Require DATABASE_URL - fails immediately if not set
        DATABASE_URL: str = env.require("DATABASE_URL")

        print("✅ DATABASE_URL is set")
        print(f"   Value: {DATABASE_URL}")
        print("\n✅ This only prints if validation passed at import time")
        print("   TripWire ensures your app won't start with invalid config!")

        return DATABASE_URL

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/basic/01_simple_require.py --demo")
            print("   • Set variable: export DATABASE_URL='postgresql://localhost/mydb'")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
