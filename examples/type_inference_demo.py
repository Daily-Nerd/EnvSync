"""Demo of TripWire v0.4.0 Type Inference Feature.

This script demonstrates the new type inference capability and typed convenience methods.
"""

import tempfile
from pathlib import Path

from tripwire import TripWire

# Create a temporary .env file for demo
demo_env = """
# Server configuration
APP_PORT=8080
APP_HOST=0.0.0.0
ENABLE_DEBUG=true
APP_WORKERS=4

# Database
APP_DATABASE_URL=postgresql://localhost:5432/myapp
APP_DB_POOL_SIZE=10
APP_DB_TIMEOUT=30.5

# API Keys
APP_API_KEY=sk-1234567890abcdef1234567890abcdef12
APP_API_RATE_LIMIT=100.0

# Feature flags
APP_ALLOWED_HOSTS=localhost,127.0.0.1,example.com
APP_FEATURE_FLAGS={"new_ui": true, "beta_features": false}
"""

with tempfile.TemporaryDirectory() as tmp_dir:
    env_file = Path(tmp_dir) / ".env"
    env_file.write_text(demo_env)

    # Initialize TripWire
    env = TripWire(env_file=str(env_file))

    print("=" * 70)
    print("TripWire v0.4.0 - Type Inference Demo")
    print("=" * 70)
    print()

    # ========================================================================
    # Method 1: Type Inference (RECOMMENDED - New in v0.4.0)
    # ========================================================================
    print("1. Type Inference from Annotations (NEW!)")
    print("-" * 70)
    print("No need to specify type= parameter - it's inferred from annotation!")
    print()

    # Integer - type inferred from annotation
    APP_PORT: int = env.require("APP_PORT", min_val=1024, max_val=65535)
    print(f"APP_PORT: {APP_PORT} (type: {type(APP_PORT).__name__})")

    # Boolean - type inferred from annotation
    ENABLE_DEBUG: bool = env.optional("ENABLE_DEBUG", default=False)
    print(f"ENABLE_DEBUG: {ENABLE_DEBUG} (type: {type(ENABLE_DEBUG).__name__})")

    # Float - type inferred from annotation
    APP_DB_TIMEOUT: float = env.require("APP_DB_TIMEOUT")
    print(f"APP_DB_TIMEOUT: {APP_DB_TIMEOUT} (type: {type(APP_DB_TIMEOUT).__name__})")

    # String - type inferred from annotation
    APP_HOST: str = env.require("APP_HOST")
    print(f"APP_HOST: {APP_HOST} (type: {type(APP_HOST).__name__})")

    # List - type inferred from annotation
    APP_ALLOWED_HOSTS: list = env.require("APP_ALLOWED_HOSTS")
    print(f"APP_ALLOWED_HOSTS: {APP_ALLOWED_HOSTS} (type: {type(APP_ALLOWED_HOSTS).__name__})")

    # Dict - type inferred from annotation
    APP_FEATURE_FLAGS: dict = env.require("APP_FEATURE_FLAGS")
    print(f"APP_FEATURE_FLAGS: {APP_FEATURE_FLAGS} (type: {type(APP_FEATURE_FLAGS).__name__})")

    print()

    # ========================================================================
    # Method 2: Typed Convenience Methods
    # ========================================================================
    print("2. Typed Convenience Methods (for dictionaries, comprehensions)")
    print("-" * 70)
    print("Use when you can't use type annotations (e.g., in dictionaries)")
    print()

    config = {
        "port": env.require_int("APP_PORT", min_val=1024, max_val=65535),
        "workers": env.optional_int("APP_WORKERS", default=1),
        "debug": env.optional_bool("ENABLE_DEBUG", default=False),
        "db_timeout": env.require_float("APP_DB_TIMEOUT"),
        "api_rate_limit": env.optional_float("APP_API_RATE_LIMIT", default=60.0),
        "host": env.require_str("APP_HOST"),
        "api_key": env.require_str("APP_API_KEY", min_length=32),
    }

    for key, value in config.items():
        print(f"{key}: {value} (type: {type(value).__name__})")

    print()

    # ========================================================================
    # Method 3: Explicit Type (Backward Compatible)
    # ========================================================================
    print("3. Explicit Type Parameter (OLD API - still works)")
    print("-" * 70)
    print("Old code with type= parameter continues to work")
    print()

    APP_DB_POOL_SIZE: int = env.require("APP_DB_POOL_SIZE", type=int, min_val=1)
    API_RATE_LIMIT_OLD: float = env.optional("APP_API_RATE_LIMIT", type=float, default=60.0)
    APP_DATABASE_URL: str = env.require("APP_DATABASE_URL", type=str, format="postgresql")

    print(f"APP_DB_POOL_SIZE: {APP_DB_POOL_SIZE} (type: {type(APP_DB_POOL_SIZE).__name__})")
    print(f"APP_API_RATE_LIMIT: {API_RATE_LIMIT_OLD} (type: {type(API_RATE_LIMIT_OLD).__name__})")
    print(f"APP_DATABASE_URL: {APP_DATABASE_URL[:30]}... (type: {type(APP_DATABASE_URL).__name__})")

    print()
    print("=" * 70)
    print("Key Takeaway: Type inference eliminates redundancy while maintaining")
    print("full backward compatibility!")
    print("=" * 70)
