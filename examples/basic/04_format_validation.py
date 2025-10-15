"""Example: Format validators

This example demonstrates TripWire's built-in format validators
for common patterns (URLs, emails, database URLs, etc.).

README Reference: Format Validators section

Expected behavior:
- Format validators ensure values match expected patterns
- Validation happens at import time
- Invalid formats raise ValidationError with helpful messages

Run this example:
    export DATABASE_URL="postgresql://localhost:5432/mydb"
    export API_URL="https://api.example.com"
    export ADMIN_EMAIL="admin@example.com"
    python examples/basic/04_format_validation.py

Or use demo mode:
    python examples/basic/04_format_validation.py --demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire


def main():
    """Demonstrate built-in format validators."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["DATABASE_URL"] = "postgresql://localhost:5432/demo_db"
        os.environ["API_URL"] = "https://api.example.com"
        os.environ["ADMIN_EMAIL"] = "admin@example.com"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Format validators ensure correct patterns
        DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
        API_URL: str = env.require("API_URL", format="url")
        ADMIN_EMAIL: str = env.require("ADMIN_EMAIL", format="email")

        print("✅ Format validation successful!")
        print(f"   DATABASE_URL: {DATABASE_URL}")
        print(f"      └─ Validated as PostgreSQL URL")
        print(f"   API_URL: {API_URL}")
        print(f"      └─ Validated as valid URL")
        print(f"   ADMIN_EMAIL: {ADMIN_EMAIL}")
        print(f"      └─ Validated as email address")
        print("\n💡 Available formats: postgresql, mysql, url, email, uuid, ipv4")

        return DATABASE_URL, API_URL, ADMIN_EMAIL

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/basic/04_format_validation.py --demo")
            print(
                "   • Set variables: export DATABASE_URL='postgresql://localhost:5432/mydb' API_URL='https://api.example.com' ADMIN_EMAIL='admin@example.com'"
            )
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
