"""Example: Pattern validation with regex

This example demonstrates using regex patterns to validate
environment variable formats.

README Reference: Advanced Usage section

Expected behavior:
- Validates value matches the specified regex pattern
- Raises ValidationError if pattern doesn't match

Run this example:
    export API_KEY="sk_live_abc123xyz"
    export VERSION="1.2.3"
    python examples/advanced/03_pattern_matching.py

Or use demo mode:
    python examples/advanced/03_pattern_matching.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate pattern validation."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["API_KEY"] = "sk_live_abc123xyz789"
        os.environ["VERSION"] = "1.2.3"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Pattern validation with regex
        API_KEY: str = env.require("API_KEY", pattern=r"^sk_(test|live)_[a-zA-Z0-9]{12,}$")

        VERSION: str = env.require("VERSION", pattern=r"^\d+\.\d+\.\d+$")  # Semantic versioning: X.Y.Z

        print("✅ Pattern validation successful!")
        print(f"   API_KEY: {API_KEY}")
        print(f"      └─ Matches pattern: sk_(test|live)_[a-zA-Z0-9]{{12,}}")
        print(f"   VERSION: {VERSION}")
        print(f"      └─ Matches pattern: X.Y.Z (semantic versioning)")
        print("\n💡 Try setting VERSION=1.2 to see validation fail!")

        return API_KEY, VERSION

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/advanced/03_pattern_matching.py --demo")
            print("   • Set variables: export API_KEY='sk_live_abc123xyz789' VERSION='1.2.3'")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
