"""Example: Custom Validators Plugin System.

This example demonstrates how to create and register custom format validators
for your specific validation needs.
"""

import re

from tripwire import env
from tripwire.validation import register_validator, register_validator_decorator


# Method 1: Register a validator using register_validator()
def validate_phone_number(value: str) -> bool:
    """Validate US phone number format (XXX-XXX-XXXX)."""
    pattern = r"^\d{3}-\d{3}-\d{4}$"
    return bool(re.match(pattern, value))


register_validator("phone", validate_phone_number)


# Method 2: Use the decorator for inline registration
@register_validator_decorator("zip_code")
def validate_zip_code(value: str) -> bool:
    """Validate US ZIP code (5 digits or 5+4 format)."""
    pattern = r"^\d{5}(-\d{4})?$"
    return bool(re.match(pattern, value))


@register_validator_decorator("hex_color")
def validate_hex_color(value: str) -> bool:
    """Validate hex color code (#RGB or #RRGGBB)."""
    pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
    return bool(re.match(pattern, value))


@register_validator_decorator("username")
def validate_username(value: str) -> bool:
    """Validate username (alphanumeric, underscore, hyphen, 3-20 chars)."""
    pattern = r"^[a-zA-Z0-9_-]{3,20}$"
    return bool(re.match(pattern, value))


@register_validator_decorator("semantic_version")
def validate_semver(value: str) -> bool:
    """Validate semantic version (X.Y.Z format)."""
    pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
    return bool(re.match(pattern, value))


@register_validator_decorator("aws_region")
def validate_aws_region(value: str) -> bool:
    """Validate AWS region code."""
    valid_regions = {
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-central-1",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ca-central-1",
        "sa-east-1",
    }
    return value in valid_regions


@register_validator_decorator("domain")
def validate_domain(value: str) -> bool:
    """Validate domain name format."""
    pattern = r"^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value))


@register_validator_decorator("base64")
def validate_base64(value: str) -> bool:
    """Validate base64 encoded string."""
    pattern = r"^[A-Za-z0-9+/]*={0,2}$"
    if not re.match(pattern, value):
        return False
    # Base64 length must be multiple of 4
    return len(value) % 4 == 0


# Now you can use these custom validators in your environment variables
if __name__ == "__main__":
    # Example usage - these would come from .env file
    import os

    os.environ["SUPPORT_PHONE"] = "555-123-4567"
    os.environ["OFFICE_ZIP"] = "94102"
    os.environ["BRAND_COLOR"] = "#FF5733"
    os.environ["ADMIN_USERNAME"] = "admin_user"
    os.environ["APP_VERSION"] = "1.0.0"
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["COMPANY_DOMAIN"] = "example.com"

    # Use custom validators with format parameter
    phone = env.require("SUPPORT_PHONE", format="phone", description="Support phone number")
    zip_code = env.require("OFFICE_ZIP", format="zip_code", description="Office ZIP code")
    color = env.require("BRAND_COLOR", format="hex_color", description="Brand primary color")
    username = env.require("ADMIN_USERNAME", format="username", description="Admin username")
    version = env.require("APP_VERSION", format="semantic_version", description="App version")
    region = env.require("AWS_REGION", format="aws_region", description="AWS deployment region")
    domain = env.require("COMPANY_DOMAIN", format="domain", description="Company domain")

    print("All custom validators passed!")
    print(f"Phone: {phone}")
    print(f"ZIP: {zip_code}")
    print(f"Color: {color}")
    print(f"Username: {username}")
    print(f"Version: {version}")
    print(f"Region: {region}")
    print(f"Domain: {domain}")
