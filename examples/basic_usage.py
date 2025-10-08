"""TripWire Basic Usage - Complete Feature Tour

⚠️  IMPORTANT: This example demonstrates ALL features and requires many environment variables.
    If this is your first time, try quickstart.py instead!

SETUP INSTRUCTIONS:
1. Copy the example environment file:
   cp examples/.env.example examples/.env

2. Edit examples/.env and fill in ALL variable values (see .env.example for details)

3. Run this example:
   python examples/basic_usage.py

4. Or run in demo mode (no .env required):
   python examples/basic_usage.py --demo

For a simpler introduction with just 3 variables, see:
   python examples/quickstart.py

This comprehensive example demonstrates:
- Required vs optional variables
- Type coercion (int, bool, float, list)
- Format validators (email, URL, postgresql, etc.)
- Pattern validation (custom regex)
- Choices validation (enum-like behavior)
- Custom validators
- Range validation for numbers
- Secret marking
- And more!
"""

import sys

# Demo mode support - run with --demo flag to use example values
DEMO_MODE = "--demo" in sys.argv

if DEMO_MODE:
    print("🎭 Running in DEMO MODE with example values\n")
    import os

    os.environ.update(
        {
            "API_KEY": "demo-api-key-1234567890",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/demo_db",
            "DEBUG": "true",
            "PORT": "8000",
            "MAX_RETRIES": "3",
            "ADMIN_EMAIL": "admin@example.com",
            "ALLOWED_HOSTS": "localhost,127.0.0.1,example.com",
            "ENVIRONMENT": "development",
            "API_TOKEN": "sk-abcd1234efgh5678ijkl9012mnop3456",
            "S3_BUCKET": "demo-bucket",
            "SECRET_KEY": "demo-secret-key-for-testing-purposes-only",
            "TIMEOUT": "30.0",
        }
    )

from tripwire import env

# Example 1: Required string variable
# This will raise MissingVariableError if API_KEY is not set
API_KEY: str = env.require("API_KEY", description="API key for external service")

# Example 2: Required variable with format validation
# Validates that DATABASE_URL starts with postgresql://
DATABASE_URL: str = env.require(
    "DATABASE_URL",
    description="PostgreSQL connection string",
    format="postgresql",
)

# Example 3: Optional boolean with default
# Handles various boolean representations: true/false, 1/0, yes/no, on/off
DEBUG: bool = env.optional(
    "DEBUG",
    default=False,
    type=bool,
    description="Enable debug mode",
)

# Example 4: Integer with range validation
# Ensures PORT is between 1 and 65535
PORT: int = env.require(
    "PORT",
    type=int,
    min_val=1,
    max_val=65535,
    description="Server port number",
)

# Example 5: Optional integer with default
MAX_RETRIES: int = env.optional(
    "MAX_RETRIES",
    default=3,
    type=int,
    min_val=1,
    description="Maximum retry attempts",
)

# Example 6: Email validation
ADMIN_EMAIL: str = env.require(
    "ADMIN_EMAIL",
    format="email",
    description="Administrator email address",
)

# Example 7: List from comma-separated values
# Input: ALLOWED_HOSTS=localhost,example.com,api.example.com
# Output: ["localhost", "example.com", "api.example.com"]
ALLOWED_HOSTS: list[str] = env.require(
    "ALLOWED_HOSTS",
    type=list,
    description="Comma-separated list of allowed hosts",
)

# Example 8: Choices validation (enum-like behavior)
ENVIRONMENT: str = env.require(
    "ENVIRONMENT",
    choices=["development", "staging", "production"],
    description="Application environment",
)

# Example 9: Pattern validation (custom regex)
# Validates API key format: must start with "sk-" followed by 32 characters
API_TOKEN: str = env.require(
    "API_TOKEN",
    pattern=r"^sk-[a-zA-Z0-9]{32}$",
    description="Service API token",
    error_message="API token must be in format: sk-<32 alphanumeric characters>",
)

# Example 10: Custom validator
from tripwire import validator


@validator
def validate_s3_bucket(value: str) -> bool:
    """Validate S3 bucket name rules."""
    # S3 bucket names: 3-63 chars, lowercase, no underscores
    if not 3 <= len(value) <= 63:
        return False
    if not value.islower():
        return False
    if "_" in value:
        return False
    return True


S3_BUCKET: str = env.require(
    "S3_BUCKET",
    validator=validate_s3_bucket,
    description="S3 bucket name",
    error_message="S3 bucket must be 3-63 lowercase chars without underscores",
)

# Example 11: Secret variables
# Mark sensitive data as secret for secret detection
SECRET_KEY: str = env.require(
    "SECRET_KEY",
    secret=True,
    description="Application secret key",
)

# Example 12: Optional with type and validation
TIMEOUT: float = env.optional(
    "TIMEOUT",
    default=30.0,
    type=float,
    min_val=0.1,
    description="Request timeout in seconds",
)


def main() -> None:
    """Main function demonstrating the loaded configuration."""
    print("TripWire Basic Usage Example")
    print("=" * 50)
    print(f"API_KEY: {API_KEY[:10]}... (truncated)")
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"DEBUG: {DEBUG}")
    print(f"PORT: {PORT}")
    print(f"MAX_RETRIES: {MAX_RETRIES}")
    print(f"ADMIN_EMAIL: {ADMIN_EMAIL}")
    print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
    print(f"ENVIRONMENT: {ENVIRONMENT}")
    print(f"API_TOKEN: {API_TOKEN[:10]}... (truncated)")
    print(f"S3_BUCKET: {S3_BUCKET}")
    print(f"SECRET_KEY: ****** (hidden)")
    print(f"TIMEOUT: {TIMEOUT}s")
    print("=" * 50)
    print("All environment variables loaded and validated successfully!")


if __name__ == "__main__":
    # Note: This will fail if required variables are not set
    # Create a .env file or set environment variables before running
    main()
