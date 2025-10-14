"""
TripWire Secret Protection Example
===================================

This example demonstrates:
1. How TripWire protects secrets automatically
2. Best practices for debugging with secrets
3. When to use get_secret_value() (and when not to)
4. Logging integration for production safety

Type Annotation Best Practices:
================================

When secret=True is used, TripWire returns Secret[T], not T.

CORRECT:
  token: Secret[str] = env.require("TOKEN", secret=True)

INCORRECT (but works at runtime):
  token: str = env.require("TOKEN", secret=True)

Why use Secret[T] annotation?
  1. Type checker compliance (mypy, pyright)
  2. IDE autocomplete for .get_secret_value()
  3. Code clarity for other developers
  4. Self-documenting code

Note: Python doesn't enforce type hints at runtime, so both work,
but only Secret[str] is correct for type safety and tooling support.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from tripwire import TripWire, env
from tripwire.core.loader import DotenvFileSource
from tripwire.plugins.sources import VaultEnvSource
from tripwire.security import Secret
from tripwire.security.logging import auto_install

# ============================================================================
# SETUP: Configure logging with secret protection
# ============================================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Auto-install secret redaction filters on all loggers
auto_install()


# ============================================================================
# STEP 1: Bootstrap - Load credentials from .env
# ============================================================================

# Load .env first to get Vault token
bootstrap_dotenv = DotenvFileSource(Path(".env"))
bootstrap_dotenv.load()

# Get Vault token (secret=True returns Secret[str])
vault_token: Secret[str] = env.require("VAULT_TOKEN", secret=True)

# Get Vault URL (also a secret - should use Secret[str])
vault_url: Secret[str] = env.require("VAULT_URL", secret=True)

print("\n" + "=" * 70)
print("STEP 1: Bootstrap Credentials")
print("=" * 70)

# ✅ GOOD: Print masked secret for debugging
print(f"✅ Masked token: {vault_token}")
# Output: ✅ Masked token: **********

# ✅ GOOD: Log masked secret (safe for production)
logger.info(f"✅ Loaded Vault token: {vault_token}")
# Log file: "Loaded Vault token: **********"

# ✅ GOOD: Check secret properties without exposing value
print(f"✅ Token length: {len(vault_token)}")
print(f"✅ Token is set: {bool(vault_token)}")


# ❌ BAD: Don't print unwrapped secrets to console (for debugging)
# Uncomment to see what NOT to do:
# print(f"❌ EXPOSED: {vault_token.get_secret_value()}")
# This exposes the secret in console output!

print("\n💡 TIP: Use print(secret) for debugging - it shows masked version")


# ============================================================================
# BONUS: Type Annotation Demonstration
# ============================================================================

print("\n" + "=" * 70)
print("BONUS: Type Annotation Comparison")
print("=" * 70)

print(
    """
When secret=True, TripWire returns Secret[T], not T.

COMPARISON:
-----------

✅ CORRECT ANNOTATION:
   token: Secret[str] = env.require("TOKEN", secret=True)
   - Type checker: PASS (mypy, pyright)
   - IDE autocomplete: Shows .get_secret_value()
   - Runtime: WORKS (returns Secret[str])

⚠️ WRONG ANNOTATION (but works at runtime):
   token: str = env.require("TOKEN", secret=True)
   - Type checker: FAIL (Incompatible types: Secret[str] vs str)
   - IDE autocomplete: Shows string methods only
   - Runtime: WORKS (Python ignores type hints)

WHY BOTH WORK AT RUNTIME:
--------------------------
Python type hints are NOT enforced at runtime. They're purely for:
  1. Static analysis tools (mypy, pyright, pylance)
  2. IDE features (autocomplete, error detection)
  3. Code documentation (clarity for developers)

The actual return value is Secret[str] regardless of annotation.

RECOMMENDATION:
---------------
ALWAYS use Secret[T] annotation when secret=True for:
  ✓ Type safety (mypy compliance)
  ✓ IDE support (proper autocomplete)
  ✓ Code clarity (self-documenting)
"""
)

# Demonstration with both annotations (both work at runtime)
print("\n--- Runtime Demonstration ---")

# ✅ Correct annotation
correct_token: Secret[str] = vault_token
print(f"✅ With Secret[str] annotation: {correct_token}")  # **********

# ⚠️ Wrong annotation (but runtime still works)
# This is intentionally wrong to demonstrate that Python doesn't enforce types
wrong_annotation: str = vault_token
print(f"⚠️ With str annotation: {wrong_annotation}")  # Also **********

print("\nNOTE: Both print ********** because the actual object is Secret[str]")
print("      Python doesn't enforce type hints at runtime!")

print("\n--- Type Checker Behavior ---")
print("✅ Secret[str] = env.require(..., secret=True)  → mypy: PASS")
print("❌ str = env.require(..., secret=True)         → mypy: FAIL")
print("   error: Incompatible types (Secret[str] vs str)")


# ============================================================================
# STEP 2: Initialize Vault with correct source ordering
# ============================================================================

print("\n" + "=" * 70)
print("STEP 2: Initialize Cloud Secret Manager")
print("=" * 70)

# ✅ GOOD: Unwrap secret ONLY when passing to authenticated service
vault = VaultEnvSource(
    url=vault_url.get_secret_value(),
    token=vault_token.get_secret_value(),  # ✅ Legitimate use
    mount_point="secret",
    path="homelab-config/gh",
)

dotenv = DotenvFileSource(Path(".env"))

# ✅ CORRECT: dotenv FIRST, vault SECOND (Vault overrides .env)
env_tripwire = TripWire(sources=[dotenv, vault], collect_errors=False)

print("✅ TripWire initialized with sources: .env → Vault")
print("   (Vault secrets override .env values)")


# ============================================================================
# STEP 3: Load application secrets
# ============================================================================

print("\n" + "=" * 70)
print("STEP 3: Load Application Secrets")
print("=" * 70)

# Load secrets from Vault (with proper type annotations - Secret[str] for all secrets)
github_token: Secret[str] = env_tripwire.require("github_token", secret=True)
database_url: Secret[str] = env_tripwire.require("DATABASE_URL", secret=True)

# ✅ GOOD: Print masked secrets for verification
print(f"✅ GitHub Token: {github_token}")
print(f"✅ Database URL: {database_url}")
# Output shows: ********** for both

# ✅ GOOD: Log secret usage (automatically redacted)
logger.info(f"✅ Loaded GitHub token: {github_token}")
logger.info(f"✅ Loaded database URL: {database_url}")


# ============================================================================
# STEP 4: Debugging Examples (What to do vs what NOT to do)
# ============================================================================

print("\n" + "=" * 70)
print("STEP 4: Debugging Best Practices")
print("=" * 70)

print("\n--- ✅ GOOD PRACTICES ---")

# ✅ GOOD: Use masked secret in f-strings
print(f"✅ Token: {github_token} (safe for debugging)")

# ✅ GOOD: Use masked secret in string formatting
print(f"✅ Auth header: Bearer {github_token}")

# ✅ GOOD: Check if secret is set
if github_token:
    print("✅ GitHub token is configured")

# ✅ GOOD: Compare secrets safely (constant-time comparison)
test_token: Secret[str] = Secret("test_value")
if github_token == test_token:
    print("Tokens match")  # Won't print (different values)


print("\n--- ❌ BAD PRACTICES (Commented Out) ---")

# ❌ BAD: Don't unwrap for debugging
# print(f"❌ Token: {github_token.get_secret_value()}")
print("❌ DON'T: print(f'Token: {token.get_secret_value()}')")
print("   → Exposes secret in console output!")

# ❌ BAD: Don't log unwrapped secrets to analytics
# analytics.track("token", github_token.get_secret_value())
print("❌ DON'T: analytics.track('token', token.get_secret_value())")
print("   → Sends secret to third-party service!")

# ❌ BAD: Don't write unwrapped secrets to files
# with open("debug.txt", "w") as f:
#     f.write(github_token.get_secret_value())
print("❌ DON'T: Write unwrapped secrets to files")
print("   → Persists secrets on disk!")


# ============================================================================
# STEP 5: Legitimate Uses of get_secret_value()
# ============================================================================

print("\n" + "=" * 70)
print("STEP 5: Legitimate Uses of get_secret_value()")
print("=" * 70)

# ✅ GOOD: Pass to authenticated API client
print("✅ GOOD: Pass to API client")
# github_client = GitHubClient(token=github_token.get_secret_value())
print("   github_client = GitHubClient(token=token.get_secret_value())")

# ✅ GOOD: Use in authentication headers
print("\n✅ GOOD: Use in auth headers")
# headers = {"Authorization": f"Bearer {github_token.get_secret_value()}"}
print("   headers = {'Authorization': f'Bearer {token.get_secret_value()}'}")

# ✅ GOOD: Pass to database connection
print("\n✅ GOOD: Pass to database")
# connection = psycopg2.connect(database_url.get_secret_value())
print("   connection = psycopg2.connect(url.get_secret_value())")

print("\n💡 TIP: Only unwrap secrets when passing to authenticated services")


# ============================================================================
# STEP 6: Logging Integration (Defense-in-Depth)
# ============================================================================

print("\n" + "=" * 70)
print("STEP 6: Logging Protection (Defense-in-Depth)")
print("=" * 70)

# ✅ EVEN IF you accidentally unwrap in logging, it's STILL protected!
logger.info(f"✅ Token (wrapped): {github_token}")
# Log shows: "Token (wrapped): **********"

logger.info(f"✅ Token (unwrapped): {github_token.get_secret_value()}")
# Log STILL shows: "Token (unwrapped): **********"
# This is DEFENSE-IN-DEPTH! Even mistakes are caught.

print("✅ Logging is protected even with get_secret_value()")
print("   Check your log files - secrets are redacted!")


# ============================================================================
# STEP 7: Exception Handling
# ============================================================================

print("\n" + "=" * 70)
print("STEP 7: Exception Handling")
print("=" * 70)

try:
    # Simulate error with secret in message
    raise ValueError(f"Authentication failed with token: {github_token.get_secret_value()}")
except ValueError as e:
    # ✅ GOOD: Exception is logged with redaction
    logger.exception("✅ Error occurred (secrets in traceback are redacted)")
    print("✅ Exception logged - check logs to verify redaction")


# ============================================================================
# STEP 8: FastAPI Integration Example
# ============================================================================

print("\n" + "=" * 70)
print("STEP 8: FastAPI Integration")
print("=" * 70)


# Modern FastAPI lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan - startup and shutdown.

    Args:
        _app: FastAPI app instance (unused, required by FastAPI lifespan signature)
    """
    # Startup
    logger.info("✅ Application starting with validated secrets")
    logger.info(f"✅ GitHub token configured: {bool(github_token)}")
    logger.info(f"✅ Database configured: {bool(database_url)}")

    yield  # Application runs

    # Shutdown (optional cleanup)
    logger.info("✅ Application shutting down")


app = FastAPI(title="TripWire Secret Protection Demo", lifespan=lifespan)  # Use modern lifespan handler


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "secrets_configured": {
            "github": bool(github_token),
            "database": bool(database_url),
            "vault": bool(vault_token),
        },
    }


@app.get("/api/github")
async def github_api():
    """Example API endpoint using secrets correctly."""
    # ✅ GOOD: Unwrap only when calling authenticated service
    # github_client = GitHubClient(token=github_token.get_secret_value())
    # data = github_client.get_user()

    logger.info("✅ GitHub API called with authenticated token")
    return {"message": "GitHub API integration example"}


print("✅ FastAPI app configured with modern lifespan handler")
print("\n💡 Run with: uvicorn main:app --reload")


# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY: TripWire Secret Protection")
print("=" * 70)

print(
    """
✅ PROTECTION LAYERS ACTIVE:

1. Secret Wrapper: print(secret) → **********
2. Logging Filter: logger.info(secret.get_secret_value()) → **********
3. Exception Redaction: Tracebacks show **********
4. JSON Serialization: json.dumps() → **********

⚠️ USER RESPONSIBILITY:

- Console output from print(secret.get_secret_value())
- Only unwrap for legitimate API calls

📚 BEST PRACTICES:

TYPE ANNOTATIONS:
  ✅ token: Secret[str] = env.require("TOKEN", secret=True)
  ❌ token: str = env.require("TOKEN", secret=True)  # Wrong type!

DEBUGGING:
  ✅ print(secret) for debugging (shows *********)
  ✅ logger.info(secret) or logger.info(secret.get_secret_value())
  ✅ Check len(secret), bool(secret)

LEGITIMATE USE:
  ✅ api_client.auth(secret.get_secret_value())
  ✅ database.connect(secret.get_secret_value())

NEVER DO:
  ❌ print(secret.get_secret_value()) for debugging
  ❌ analytics.track(secret.get_secret_value())
  ❌ Write unwrapped secrets to files

🔒 DEFENSE-IN-DEPTH:
Even if you make a mistake and unwrap in logging,
TripWire's filter will STILL redact it!
"""
)

print("=" * 70)
print("✅ All secrets protected - ready for production!")
print("=" * 70 + "\n")
