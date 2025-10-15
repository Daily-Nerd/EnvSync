"""Example: env.optional() with default values

This example demonstrates using env.optional() for optional environment
variables with sensible defaults.

README Reference: Basic Usage section

Expected behavior:
- If DEBUG is set: Uses provided value
- If DEBUG is not set: Uses default value (False)

Run this example:
    export DEBUG="true"
    python examples/basic/02_optional_with_default.py

Or use demo mode:
    python examples/basic/02_optional_with_default.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate env.optional() with defaults."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        # Set some env vars, leave others to use defaults
        os.environ["DEBUG"] = "true"
        # PORT will use default
        os.environ["LOG_LEVEL"] = "DEBUG"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Optional variables with defaults - never fails
        DEBUG: bool = env.optional("DEBUG", default=False)
        PORT: int = env.optional("PORT", default=8000, min_val=1, max_val=65535)
        LOG_LEVEL: str = env.optional("LOG_LEVEL", default="INFO")

        print("✅ Optional variables loaded (with defaults if not set)")
        print(f"   DEBUG: {DEBUG} (type: {type(DEBUG).__name__})")
        print(f"   PORT: {PORT} (type: {type(PORT).__name__})")
        print(f"   LOG_LEVEL: {LOG_LEVEL}")
        print("\n💡 Try setting these in your environment to override defaults!")

        return DEBUG, PORT, LOG_LEVEL

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/basic/02_optional_with_default.py --demo")
            print("   • Set variables: export DEBUG=true PORT=8000 LOG_LEVEL=INFO")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
