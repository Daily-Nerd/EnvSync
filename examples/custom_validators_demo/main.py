"""Custom Validators Demo - Example Usage.

This module demonstrates the correct workflow for using custom validators:

1. Import custom validators (registers them at import-time)
2. Use them in env.require() calls with format= parameter

The validators are registered when custom_validators.py is imported,
so they're available for use in this module.

Usage:
------
  $ python examples/custom_validators_demo/main.py

This will validate example environment variables using custom format validators.
"""

import os

# Import custom validators - this registers them at import-time
from custom_validators import (
    validate_aws_region,
    validate_base64,
    validate_domain,
    validate_hex_color,
    validate_phone_number,
    validate_semver,
    validate_username,
    validate_zip_code,
)

from tripwire import env

if __name__ == "__main__":
    # Example usage - these would normally come from .env file
    # Setting them here for demonstration purposes
    os.environ["SUPPORT_PHONE"] = "555-123-4567"
    os.environ["OFFICE_ZIP"] = "94102"
    os.environ["BRAND_COLOR"] = "#FF5733"
    os.environ["ADMIN_USERNAME"] = "admin_user"
    os.environ["APP_VERSION"] = "1.0.0"
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["COMPANY_DOMAIN"] = "example.com"
    os.environ["API_TOKEN"] = "SGVsbG8gV29ybGQ="  # "Hello World" in base64  # nosec B105

    # Use custom validators with format parameter
    # These will pass validation because we imported the validators above
    phone = env.require("SUPPORT_PHONE", format="phone", description="Support phone number")
    zip_code = env.require("OFFICE_ZIP", format="zip_code", description="Office ZIP code")
    color = env.require("BRAND_COLOR", format="hex_color", description="Brand primary color")
    username = env.require("ADMIN_USERNAME", format="username", description="Admin username")
    version = env.require("APP_VERSION", format="semantic_version", description="App version")
    region = env.require("AWS_REGION", format="aws_region", description="AWS deployment region")
    domain = env.require("COMPANY_DOMAIN", format="domain", description="Company domain")
    token = env.require("API_TOKEN", format="base64", description="API authentication token")

    # Print results
    print("All custom validators passed!")
    print(f"Phone: {phone}")
    print(f"ZIP: {zip_code}")
    print(f"Color: {color}")
    print(f"Username: {username}")
    print(f"Version: {version}")
    print(f"Region: {region}")
    print(f"Domain: {domain}")
    print(f"Token: {token}")
