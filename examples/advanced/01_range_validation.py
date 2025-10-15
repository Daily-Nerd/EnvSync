"""Example: Range validation for numbers

This example demonstrates min_val and max_val validation for numeric
environment variables.

README Reference: Advanced Usage section

Expected behavior:
- Validates numeric values are within specified range
- Raises ValidationError if value is out of range

Run this example:
    export PORT="8080"
    export MAX_CONNECTIONS="100"
    export TIMEOUT="30"
    python examples/advanced/01_range_validation.py

Or use demo mode:
    python examples/advanced/01_range_validation.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate range validation."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["PORT"] = "8080"
        os.environ["MAX_CONNECTIONS"] = "100"
        os.environ["TIMEOUT"] = "30.0"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Range validation for numbers
        PORT: int = env.require("PORT", min_val=1, max_val=65535)
        MAX_CONNECTIONS: int = env.require("MAX_CONNECTIONS", min_val=1, max_val=10000)
        TIMEOUT: float = env.require("TIMEOUT", min_val=0.1, max_val=300.0)

        print("✅ Range validation successful!")
        print(f"   PORT: {PORT} (valid range: 1-65535)")
        print(f"   MAX_CONNECTIONS: {MAX_CONNECTIONS} (valid range: 1-10000)")
        print(f"   TIMEOUT: {TIMEOUT} (valid range: 0.1-300.0)")
        print("\n💡 Try setting PORT=99999 to see validation fail!")

        return PORT, MAX_CONNECTIONS, TIMEOUT

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/advanced/01_range_validation.py --demo")
            print("   • Set variables: export PORT=8080 MAX_CONNECTIONS=100 TIMEOUT=30.0")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
