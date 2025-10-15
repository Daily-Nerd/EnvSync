"""Example: Django settings integration

This example demonstrates how to use TripWire in Django's settings.py
for robust configuration management.

README Reference: Framework Integration section

Expected behavior:
- Configuration validated when Django loads settings
- Django won't start if configuration is invalid
- Type-safe settings with validation

Usage:
    1. Copy this pattern to your Django project's settings.py
    2. Set required environment variables
    3. Run Django: python manage.py runserver

Run this example (standalone):
    export DJANGO_SECRET_KEY="your-secret-key-here"
    export DATABASE_URL="postgresql://localhost/mydb"
    export DEBUG="false"
    export ALLOWED_HOSTS="localhost,127.0.0.1"
    python examples/frameworks/django_settings.py

Or use demo mode:
    python examples/frameworks/django_settings.py --demo
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set demo mode BEFORE importing TripWire if --demo flag is present
if "--demo" in sys.argv:
    os.environ["DJANGO_SECRET_KEY"] = "demo-django-secret-key-1234567890abcdef"  # nosec B105 - Demo value only
    os.environ["DATABASE_URL"] = "postgresql://localhost/demo_db"
    os.environ["DEBUG"] = "true"
    os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,example.com"
    print("Running in DEMO mode with mock environment variables\n")

from tripwire import TripWire

# Load and validate configuration
# Use fail-fast mode to prevent Django from starting with invalid config
env = TripWire(collect_errors=False)

# Django-specific configuration with validation
DJANGO_SECRET_KEY: str = env.require("DJANGO_SECRET_KEY", min_length=32)
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
DEBUG: bool = env.optional("DEBUG", default=False)
ALLOWED_HOSTS_STR: str = env.optional("ALLOWED_HOSTS", default="localhost")

# Parse comma-separated ALLOWED_HOSTS
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(",")]

# Additional Django settings
TIME_ZONE: str = env.optional("TIME_ZONE", default="UTC")
LANGUAGE_CODE: str = env.optional("LANGUAGE_CODE", default="en-us")

# Security settings
SECURE_SSL_REDIRECT: bool = env.optional("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE: bool = env.optional("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE: bool = env.optional("CSRF_COOKIE_SECURE", default=not DEBUG)


def get_database_config():
    """Parse DATABASE_URL into Django DATABASES format.

    This is a simplified example. In production, use dj-database-url.
    """
    # Example: postgresql://user:pass@host:port/dbname
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            # In production, parse DATABASE_URL properly
            "NAME": "mydatabase",
            "USER": "myuser",
            "PASSWORD": "mypassword",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }


def main():
    """Display validated Django configuration."""
    print("✅ Django configuration validated successfully!")
    print(f"\n   DJANGO_SECRET_KEY: {DJANGO_SECRET_KEY[:10]}...")
    print(f"   DATABASE_URL: {DATABASE_URL[:30]}...")
    print(f"   DEBUG: {DEBUG}")
    print(f"   ALLOWED_HOSTS: {ALLOWED_HOSTS}")
    print(f"   TIME_ZONE: {TIME_ZONE}")
    print(f"   LANGUAGE_CODE: {LANGUAGE_CODE}")
    print(f"\n   Security Settings:")
    print(f"      SECURE_SSL_REDIRECT: {SECURE_SSL_REDIRECT}")
    print(f"      SESSION_COOKIE_SECURE: {SESSION_COOKIE_SECURE}")
    print(f"      CSRF_COOKIE_SECURE: {CSRF_COOKIE_SECURE}")

    print("\n💡 To use in Django:")
    print("   1. Add this pattern to your settings.py")
    print("   2. Set environment variables")
    print("   3. Run: python manage.py runserver")
    print("\n💡 Best Practice:")
    print("   - Put TripWire config at TOP of settings.py")
    print("   - Django won't start if config is invalid")
    print("   - Use pip install dj-database-url for DATABASE_URL parsing")


if __name__ == "__main__":
    main()
