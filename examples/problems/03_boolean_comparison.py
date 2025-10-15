"""Anti-pattern: Boolean string comparison pitfall

This example demonstrates the common mistake of comparing environment
variable strings directly as booleans.

README Reference: Type coercion section

Expected behavior:
- Shows how string "false" is truthy in Python
- Demonstrates why proper boolean parsing is needed

Run this example:
    export DEBUG="false"
    python examples/problems/03_boolean_comparison.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Demonstrate boolean string comparison pitfall."""
    # Set DEBUG to "false" string
    os.environ["DEBUG"] = "false"

    print("Environment: DEBUG='false' (string)")
    print("\nTrying naive boolean check...\n")

    # Common mistake - this is always True!
    DEBUG = os.getenv("DEBUG")
    if DEBUG:
        print(f"❌ WRONG: if DEBUG is True!")
        print(f"   DEBUG value: '{DEBUG}'")
        print(f"   Type: {type(DEBUG).__name__}")
        print(f"   bool(DEBUG): {bool(DEBUG)}")
        print("\n⚠️  Any non-empty string is truthy in Python!")
        print("   Even 'false' evaluates to True")

    # Better but still verbose
    print("\n--- Manual fix (verbose) ---")
    DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    print(f"DEBUG = {DEBUG} (type: {type(DEBUG).__name__})")
    print("This works but requires boilerplate everywhere")

    # TripWire solution
    print("\n--- TripWire solution (clean) ---")
    from tripwire import TripWire

    env = TripWire(collect_errors=False)
    DEBUG_TRIPWIRE: bool = env.require("DEBUG")
    print(f"DEBUG: bool = env.require('DEBUG')")
    print(f"Result: {DEBUG_TRIPWIRE} (type: {type(DEBUG_TRIPWIRE).__name__})")
    print("\n✅ TripWire handles boolean parsing correctly!")
    print("   'false', 'False', '0', 'no' → False")
    print("   'true', 'True', '1', 'yes' → True")


if __name__ == "__main__":
    main()
