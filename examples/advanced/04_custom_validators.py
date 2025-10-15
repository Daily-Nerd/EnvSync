"""Example: Custom validator registration

This example demonstrates how to create and register custom validators
for application-specific validation logic.

README Reference: Custom Validators section

Expected behavior:
- Custom validators extend built-in validation
- Validators are reusable across the application

Run this example:
    export USERNAME="john_doe"
    export WEBHOOK_URL="https://hooks.example.com/webhook"
    python examples/advanced/04_custom_validators.py

Or use demo mode:
    python examples/advanced/04_custom_validators.py --demo
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tripwire import TripWire
from tripwire.validation import register_validator


# Define custom validator function
def validate_username(value: str) -> tuple[bool, str]:
    """Validate username format.

    Rules:
    - 3-20 characters
    - Alphanumeric and underscores only
    - Must start with a letter
    """
    if len(value) < 3 or len(value) > 20:
        return False, "Username must be 3-20 characters"

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", value):
        return False, "Username must start with letter, contain only alphanumeric and underscores"

    return True, ""


def validate_webhook_url(value: str) -> tuple[bool, str]:
    """Validate webhook URL is HTTPS and contains 'webhook' in path."""
    if not value.startswith("https://"):
        return False, "Webhook URL must use HTTPS"

    if "webhook" not in value.lower():
        return False, "Webhook URL must contain 'webhook' in path"

    return True, ""


# Register custom validators
register_validator("username", validate_username)
register_validator("webhook_url", validate_webhook_url)


def main():
    """Demonstrate custom validators."""
    import os

    # Check if demo mode is enabled
    demo_mode = "--demo" in sys.argv

    # Set demo variables if requested
    if demo_mode:
        print("Running in DEMO mode with mock environment variables\n")
        os.environ["USERNAME"] = "john_doe"
        os.environ["WEBHOOK_URL"] = "https://hooks.example.com/webhook"

    # Use fail-fast mode to catch errors immediately
    env = TripWire(collect_errors=False)

    try:
        # Use custom validators just like built-in ones
        USERNAME: str = env.require("USERNAME", format="username")
        WEBHOOK_URL: str = env.require("WEBHOOK_URL", format="webhook_url")

        print("✅ Custom validation successful!")
        print(f"   USERNAME: {USERNAME}")
        print(f"      └─ Custom validator: 3-20 chars, alphanumeric, starts with letter")
        print(f"   WEBHOOK_URL: {WEBHOOK_URL}")
        print(f"      └─ Custom validator: HTTPS, contains 'webhook'")
        print("\n💡 Custom validators are reusable throughout your application!")

        return USERNAME, WEBHOOK_URL

    except Exception as e:
        # Only show helpful guidance if not in demo mode
        if not demo_mode:
            print("\n❌ Environment variable validation failed!")
            print(f"   Error: {e}")
            print("\n💡 To run this example, choose one:")
            print("   • Demo mode: python examples/advanced/04_custom_validators.py --demo")
            print("   • Set variables: export USERNAME='john_doe' WEBHOOK_URL='https://hooks.example.com/webhook'")
            print("   • Use .env file: Copy examples/.env.template to .env")
            sys.exit(1)
        raise  # Re-raise in demo mode (shouldn't happen)


if __name__ == "__main__":
    main()
