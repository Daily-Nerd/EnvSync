"""Example: Choices/enum validation

This example demonstrates using the choices parameter to restrict
values to a predefined set of options.

README Reference: Advanced Usage section

Expected behavior:
- Only accepts values from the specified choices list
- Raises ValidationError for invalid choices

Run this example:
    export LOG_LEVEL="INFO"
    export ENVIRONMENT="production"
    python examples/advanced/02_choices_enum.py

Or use demo mode:
    python examples/advanced/02_choices_enum.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate choices/enum validation."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["LOG_LEVEL"] = "INFO"
        os.environ["ENVIRONMENT"] = "production"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Choices validation - must be one of the specified values
        LOG_LEVEL: str = env.require("LOG_LEVEL", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

        ENVIRONMENT: str = env.require("ENVIRONMENT", choices=["development", "staging", "production"])

        print("✅ Choices validation successful!")
        print(f"   LOG_LEVEL: {LOG_LEVEL}")
        print(f"      └─ Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        print(f"   ENVIRONMENT: {ENVIRONMENT}")
        print(f"      └─ Must be one of: development, staging, production")
        print("\n💡 Try setting LOG_LEVEL=TRACE to see validation fail!")

        return LOG_LEVEL, ENVIRONMENT

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/advanced/02_choices_enum.py --demo")
            print("   • Set variables: export LOG_LEVEL=INFO ENVIRONMENT=production")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
