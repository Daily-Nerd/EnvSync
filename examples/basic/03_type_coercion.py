"""Example: Automatic type coercion

This example demonstrates TripWire's automatic type coercion from
environment variable strings to Python types (int, bool, float).

README Reference: Type Inference section

Expected behavior:
- Strings in env vars are automatically converted to target types
- Type annotations guide the conversion
- Invalid values raise ValidationError at import time

Run this example:
    export PORT="8080"
    export DEBUG="true"
    export RATE_LIMIT="100.5"
    python examples/basic/03_type_coercion.py

Or use demo mode:
    python examples/basic/03_type_coercion.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate automatic type coercion."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["PORT"] = "8080"
        os.environ["DEBUG"] = "true"
        os.environ["RATE_LIMIT"] = "100.5"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Type coercion from environment variable strings
        PORT: int = env.require("PORT")  # "8080" -> 8080
        DEBUG: bool = env.require("DEBUG")  # "true" -> True
        RATE_LIMIT: float = env.require("RATE_LIMIT")  # "100.5" -> 100.5

        print("✅ Type coercion successful!")
        print(f"   PORT: {PORT} (type: {type(PORT).__name__})")
        print(f"   DEBUG: {DEBUG} (type: {type(DEBUG).__name__})")
        print(f"   RATE_LIMIT: {RATE_LIMIT} (type: {type(RATE_LIMIT).__name__})")
        print("\n💡 TripWire automatically converts strings to target types")
        print("   No more int(os.getenv()) or manual parsing!")

        return PORT, DEBUG, RATE_LIMIT

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/basic/03_type_coercion.py --demo")
            print("   • Set variables: export PORT=8080 DEBUG=true RATE_LIMIT=100.5")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
