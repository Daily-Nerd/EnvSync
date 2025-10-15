"""Anti-pattern: os.getenv() returns None for missing variables

This example demonstrates the classic problem with os.getenv(): it returns
None for missing variables, which causes runtime errors later in your code.

README Reference: "The Problem" section

Expected behavior:
- Runs successfully even though PORT is missing
- Causes AttributeError when trying to use the value
- Error happens at runtime, not at startup

Run this example:
    # Make sure PORT is NOT set
    unset PORT
    python examples/problems/01_os_getenv_none.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Demonstrate os.getenv() None problem."""
    print("Attempting to use os.getenv() for PORT configuration...")
    print("(PORT is not set in environment)\n")

    # This silently returns None - no error yet!
    PORT = os.getenv("PORT")
    print(f"✅ PORT = os.getenv('PORT') succeeded")
    print(f"   PORT value: {PORT}")
    print(f"   Type: {type(PORT).__name__}")
    print("\n⚠️  No error yet, but PORT is None!")

    # Now try to use it - this is where the error happens
    print("\nTrying to convert to int...")
    try:
        port_int = int(PORT)
        print(f"Port: {port_int}")
    except TypeError as e:
        print(f"❌ TypeError: {e}")
        print("\n💥 This error happens at RUNTIME, not at startup!")
        print("   Your app started successfully with invalid config")
        print("   The error only shows up when this code path executes")
        print("\n✅ TripWire solves this by validating at IMPORT TIME:")
        print("   PORT: int = env.require('PORT')")
        print("   Your app won't even start if PORT is missing!")
        return False

    return True


if __name__ == "__main__":
    # Ensure PORT is not set for demonstration
    os.environ.pop("PORT", None)
    main()
