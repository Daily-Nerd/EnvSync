"""Advanced TripWire Usage Examples.

This module demonstrates advanced features of TripWire including:
- Complete CLI workflow
- Code scanning and generation
- Drift detection and synchronization
- Secret scanning
- Documentation generation
"""

from tripwire import env

# Example 1: Required variables with validation
API_KEY = env.require(
    "API_KEY",
    description="API key for external service",
    pattern=r"^[A-Za-z0-9_-]{32,}$",
    secret=True,
)

DATABASE_URL = env.require(
    "DATABASE_URL",
    format="postgresql",
    description="PostgreSQL connection string",
)

# Example 2: Optional variables with defaults
DEBUG = env.optional(
    "DEBUG",
    default=False,
    type=bool,
    description="Enable debug mode (affects logging and error details)",
)

LOG_LEVEL = env.optional(
    "LOG_LEVEL",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    description="Application log level",
)

PORT = env.optional(
    "PORT",
    default=8000,
    type=int,
    min_val=1024,
    max_val=65535,
    description="Server port (must be in range 1024-65535)",
)

# Example 3: Email and URL validation
ADMIN_EMAIL = env.require(
    "ADMIN_EMAIL",
    format="email",
    description="Administrator email address for notifications",
)

WEBHOOK_URL = env.optional(
    "WEBHOOK_URL",
    default=None,
    format="url",
    description="Optional webhook URL for event notifications",
)

# Example 4: List and dict type variables
ALLOWED_HOSTS = env.optional(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
    type=list,
    description="Comma-separated list of allowed host names",
)

# Example 5: Environment-specific configuration
ENVIRONMENT = env.require(
    "ENVIRONMENT",
    choices=["development", "staging", "production"],
    description="Deployment environment",
)


def main() -> None:
    """Demonstrate usage of environment variables."""
    print("TripWire Advanced Usage Example")
    print("=" * 50)

    print(f"\nAPI Key: {'*' * 8} (secret, not shown)")
    print(f"Database: {DATABASE_URL}")
    print(f"Debug Mode: {DEBUG}")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"Server Port: {PORT}")
    print(f"Admin Email: {ADMIN_EMAIL}")
    print(f"Webhook URL: {WEBHOOK_URL or 'Not configured'}")
    print(f"Allowed Hosts: {', '.join(ALLOWED_HOSTS)}")
    print(f"Environment: {ENVIRONMENT}")

    print("\n" + "=" * 50)
    print("All environment variables loaded successfully!")

    # Example of using the values
    if DEBUG:
        print("\nDEBUG MODE ENABLED")
        print(f"  - Enhanced logging at {LOG_LEVEL} level")
        print(f"  - Running on port {PORT}")


if __name__ == "__main__":
    main()
