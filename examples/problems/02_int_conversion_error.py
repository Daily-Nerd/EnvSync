"""Anti-pattern: int(os.getenv()) raises TypeError

This example demonstrates the TypeError that occurs when trying to
convert None to int directly.

README Reference: "The Problem" section

Expected behavior:
- Raises TypeError: int() argument must be... not 'NoneType'
- This is the exact error type shown in the README

Run this example:
    # Ensure PORT is NOT set
    unset PORT
    python examples/problems/02_int_conversion_error.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Demonstrate int(os.getenv()) TypeError."""
    print("Attempting: PORT = int(os.getenv('PORT'))")
    print("(PORT is not set in environment)\n")
    print("Expected: TypeError because PORT is not set (returns None)\n")

    try:
        # This is what many developers try - it fails immediately
        PORT = int(os.getenv("PORT"))
        print(f"PORT = {PORT}")
    except TypeError as e:
        print(f"❌ TypeError: {e}")
        print("\n✅ This is the exact error type from the README!")
        print("   TypeError: int() argument must be a string, a bytes-like object")
        print("              or a real number, not 'NoneType'")
        print("\n💡 Why TripWire exists:")
        print("   Instead of this runtime error, TripWire validates at import time")
        print("   PORT: int = env.require('PORT')")
        print("   Your app won't start if PORT is missing - fail fast!")
        return False

    return True


if __name__ == "__main__":
    # Ensure PORT is not set for demonstration
    os.environ.pop("PORT", None)
    main()
