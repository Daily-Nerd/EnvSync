"""Custom Validator Definitions for TripWire.

This module defines custom format validators that can be used with TripWire's
environment variable validation system.

IMPORTANT - Validator Registration Timing:
------------------------------------------
Custom validators are registered at IMPORT-TIME when this module is imported.
This creates a timing mismatch with the `schema from-code` command:

1. `schema from-code` uses AST parsing (doesn't execute code)
2. AST scanning finds `format="username"` in your env.require() calls
3. However, `register_validator("username", ...)` never executes during scanning
4. Auto-validation fails because validators aren't in the registry yet

Correct Workflow for Custom Validators:
----------------------------------------

Method 1: Skip auto-validation (RECOMMENDED - Default as of v0.11.1)
  $ tripwire schema from-code               # Generates schema WITHOUT validation
  $ tripwire schema check                   # Run validation after validators are registered

  This is the default behavior. Auto-validation is skipped unless explicitly
  requested with --validate flag.

Method 2: Use --validate flag (ADVANCED)
  $ python -c "import examples.custom_validators_demo.custom_validators"  # Register validators first
  $ tripwire schema from-code --validate    # Then generate WITH validation

  Only use this if you need immediate validation feedback and have already
  imported validator registration code.

Method 3: Manual schema editing
  - Create schema with `tripwire schema new`
  - Manually add variable definitions with your custom formats
  - Run `tripwire schema check` to validate

Why Two Registration Methods:
------------------------------
1. register_validator(): Explicit function call
2. @register_validator_decorator: Decorator syntax (cleaner)

Both are equivalent - use whichever you prefer!

Key Insights:
-------------
- AST scanning (static analysis) ≠ Code execution (runtime registration)
- Custom validators register at IMPORT-TIME, not SCAN-TIME
- `schema from-code` cannot see validators that haven't been imported yet
- Default behavior (no --validate) prevents false errors
- Use `schema check` separately after schema generation for validation
"""

import re

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
