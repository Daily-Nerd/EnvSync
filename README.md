<div align="center">

```
╔══════════════════════════╗
║      ━━━━━(○)━━━━━       ║
║                          ║
║     T R I P W I R E      ║
║                          ║
║    Config validation     ║
║     that fails fast      ║
╚══════════════════════════╝
```

**Smart Environment Variable Management for Python**

> Catch missing/invalid environment variables at import time (not runtime) with type validation, secret detection, and git history auditing.

[![CI](https://github.com/Daily-Nerd/TripWire/actions/workflows/ci.yml/badge.svg)](https://github.com/Daily-Nerd/TripWire/actions/workflows/ci.yml)
[![Security](https://github.com/Daily-Nerd/TripWire/actions/workflows/security.yml/badge.svg)](https://github.com/Daily-Nerd/TripWire/actions/workflows/security.yml)
[![codecov](https://codecov.io/gh/Daily-Nerd/TripWire/graph/badge.svg?token=QEWI3WS989)](https://codecov.io/gh/Daily-Nerd/TripWire)
[![PyPI version](https://badge.fury.io/py/tripwire-py.svg)](https://badge.fury.io/py/tripwire-py)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## The Problem

Every Python developer has experienced this:

```python
# Your code
import os
API_KEY = os.getenv("API_KEY")  # Returns None - no error yet

# 2 hours later in production...
response = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
# 💥 TypeError: can only concatenate str (not "NoneType") to str

# Production is down. Users are angry. You're debugging at 2 AM.
```

**The pain:**
- Environment variables fail at **runtime**, not at startup
- No validation (wrong types, missing values, invalid formats)
- `.env` files drift across team members
- Secrets accidentally committed to git
- No type safety for configuration

---

## The Solution: TripWire

TripWire validates environment variables **at import time** and keeps your team in sync.

### Before TripWire
```python
import os

# Runtime crash waiting to happen
DATABASE_URL = os.getenv("DATABASE_URL")  # Could be None
PORT = int(os.getenv("PORT"))  # ValueError if PORT not set
DEBUG = os.getenv("DEBUG") == "true"  # Wrong! Returns False for "True", "1", etc.
```

### After TripWire
```python
from tripwire import env

# Import fails immediately if vars missing/invalid
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

# Your app won't even start with bad config!
```

**Key Benefits:**
- ✅ **Import-time validation** - Fail fast, not in production
- ✅ **Type safety** - Automatic type coercion with validation
- ✅ **Team sync** - Keep `.env` files consistent across team
- ✅ **Auto-documentation** - Generate `.env.example` from code
- ✅ **Secret detection** - 45+ platform-specific patterns (AWS, GitHub, Stripe, etc.)
- ✅ **Git history auditing** - Find when secrets were leaked and generate remediation steps
- ✅ **Great error messages** - Know exactly what's wrong and how to fix it

---

## Visual Examples

### Secret Detection in Action

**Auto-detect all secrets:**
```bash
$ tripwire audit --all

🔍 Auto-detecting secrets in .env file...

⚠️  Found 3 potential secret(s) in .env file

Detected Secrets
┌──────────────────────┬─────────────────┬──────────┐
│ Variable             │ Type            │ Severity │
├──────────────────────┼─────────────────┼──────────┤
│ AWS_SECRET_ACCESS_KEY│ AWS Secret Key  │ CRITICAL │
│ STRIPE_SECRET_KEY    │ Stripe API Key  │ CRITICAL │
│ DATABASE_PASSWORD    │ Generic Password│ CRITICAL │
└──────────────────────┴─────────────────┴──────────┘

📊 Secret Leak Blast Radius
═════════════════════════════════════════════

🔍 Repository Secret Exposure
├─ 🔴 🚨 AWS_SECRET_ACCESS_KEY (47 occurrence(s))
│  ├─ Branches affected:
│  │  ├─ origin/main (47 total commits)
│  │  └─ origin/develop (47 total commits)
│  └─ Files affected:
│     └─ .env
├─ 🟡 ⚠️ STRIPE_SECRET_KEY (12 occurrence(s))
│  ├─ Branches affected:
│  │  └─ origin/main (12 total commits)
│  └─ Files affected:
│     └─ .env
└─ 🟢 DATABASE_PASSWORD (0 occurrence(s))

📈 Summary
╭────────────────────────────────────────╮
│ Leaked: 2                              │
│ Clean: 1                               │
│ Total commits affected: 59             │
╰────────────────────────────────────────╯
```

**Detailed secret audit timeline:**
```bash
$ tripwire audit AWS_SECRET_ACCESS_KEY

Secret Leak Timeline for: AWS_SECRET_ACCESS_KEY
══════════════════════════════════════════════════════════════════════

Timeline:

📅 2024-09-15
   Commit: abc123de - Initial setup
   Author: @alice <alice@company.com>
   📁 .env:15

⚠️  Still in git history (as of HEAD)
   Affects 47 commit(s)
   Found in 1 file(s)
   Branches: origin/main, origin/develop

╭──────────────── 🚨 Security Impact ────────────────╮
│ Severity: CRITICAL                                 │
│ Exposure: PUBLIC repository                        │
│ Duration: 16 days                                  │
│ Commits affected: 47                               │
│ Files affected: 1                                  │
╰────────────────────────────────────────────────────╯

🔧 Remediation Steps:

1. Rotate the secret IMMEDIATELY
   Urgency: CRITICAL

   aws iam create-access-key --user-name <username>

   ⚠️  Do not skip this step - the secret is exposed!

2. Remove from git history (using git-filter-repo)
   Urgency: HIGH

   git filter-repo --path .env --invert-paths --force

   ⚠️  This will rewrite git history. Coordinate with your team!
```

**Import-time validation:**
```python
from tripwire import env

# ✅ This validates IMMEDIATELY when Python imports the module
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

# Your app won't even start if config is invalid!
```

**Drift detection:**
```bash
$ tripwire check

Comparing .env against .env.example

Missing Variables
┌─────────────┬───────────────────┐
│ Variable    │ Status            │
├─────────────┼───────────────────┤
│ NEW_VAR     │ Not set in .env   │
└─────────────┴───────────────────┘

Found 1 missing and 0 extra variable(s)

To add missing variables:
  tripwire sync
```

---

## Quick Start

### Installation

```bash
pip install tripwire-py
```

> **Note:** The package name on PyPI is `tripwire-py`, but you import and use it as `tripwire`:
> ```python
> from tripwire import env  # Import name is 'tripwire'
> ```

### Initialize Your Project

```bash
$ tripwire init

Welcome to TripWire! 🎯

✅ Created .env
✅ Created .env.example
✅ Updated .gitignore

Setup complete! ✅

Next steps:
  1. Edit .env with your configuration values
  2. Import in your code: from tripwire import env
  3. Use variables: API_KEY = env.require('API_KEY')
```

### Basic Usage

```python
# app.py
from tripwire import env

# Required variables (fail if missing)
API_KEY: str = env.require("API_KEY")
DATABASE_URL: str = env.require("DATABASE_URL")

# Optional with defaults
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)
MAX_RETRIES: int = env.optional("MAX_RETRIES", default=3, type=int)

# Validated formats
EMAIL: str = env.require("ADMIN_EMAIL", format="email")
REDIS_URL: str = env.require("REDIS_URL", format="url")

# Now use them safely - guaranteed to be valid!
print(f"Connecting to {DATABASE_URL}")
```

---

## Core Features

### 1. Import-Time Validation

**The killer feature** - Your app won't start with bad config.

```python
from tripwire import env

# This line MUST succeed or ImportError is raised
API_KEY = env.require("API_KEY")

# No more runtime surprises!
```

### 2. Type Coercion & Validation

Automatic type conversion with validation and **type inference from annotations** (New in v0.4.0).

#### Type Inference (Recommended)

TripWire automatically infers types from your variable annotations - **no need to specify `type=` twice!**

```python
from tripwire import env

# Strings (default)
API_KEY: str = env.require("API_KEY")

# Integers with range validation (type inferred from annotation!)
PORT: int = env.require("PORT", min_val=1, max_val=65535)
MAX_CONNECTIONS: int = env.optional("MAX_CONNECTIONS", default=100, min_val=1)

# Booleans (handles "true", "True", "1", "yes", "on", etc.)
DEBUG: bool = env.optional("DEBUG", default=False)

# Floats
TIMEOUT: float = env.optional("TIMEOUT", default=30.0)

# Lists (comma-separated or JSON)
ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS")
# .env: ALLOWED_HOSTS=localhost,example.com,api.example.com
# Or: ALLOWED_HOSTS=["localhost", "example.com"]

# Dictionaries (JSON or key=value pairs)
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={})
# .env: FEATURE_FLAGS={"new_ui": true, "beta": false}
# Or: FEATURE_FLAGS=new_ui=true,beta=false

# Choices/Enums
ENVIRONMENT: str = env.require(
    "ENVIRONMENT",
    choices=["development", "staging", "production"]
)
```

####  Typed Convenience Methods

For cases without annotations (e.g., in dictionaries, comprehensions):

```python
# Use typed methods when you can't use annotations
config = {
    "port": env.require_int("PORT", min_val=1, max_val=65535),
    "debug": env.optional_bool("DEBUG", default=False),
    "timeout": env.optional_float("TIMEOUT", default=30.0),
    "api_key": env.require_str("API_KEY", min_length=32),
}
```

#### Explicit Type (Backward Compatible)

The old API with explicit `type=` parameter still works:

```python
# Old API still works (backward compatible)
PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)
```

**How it works:**
- Type inference uses Python's type annotations at runtime
- Works with module-level and function-level variables
- Supports `int`, `float`, `bool`, `str`, `list`, `dict`
- Handles `Optional[T]` annotations (extracts `T`)
- Falls back to `str` if type cannot be inferred

### 3. Format Validators

Built-in validators for common formats.

```python
from tripwire import env

# Email validation
ADMIN_EMAIL: str = env.require("ADMIN_EMAIL", format="email")

# URL validation
API_BASE_URL: str = env.require("API_BASE_URL", format="url")

# Database URL validation
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

# UUID validation
SERVICE_ID: str = env.require("SERVICE_ID", format="uuid")

# IP address
SERVER_IP: str = env.require("SERVER_IP", format="ipv4")

# Custom regex
API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")
```

### 4. Custom Validators

Write your own validation logic.

```python
from tripwire import env, validator

@validator
def validate_s3_bucket(value: str) -> bool:
    """S3 bucket names must be 3-63 chars, lowercase, no underscores."""
    if not 3 <= len(value) <= 63:
        return False
    if not value.islower():
        return False
    if "_" in value:
        return False
    return True

# Use custom validator
S3_BUCKET: str = env.require("S3_BUCKET", validator=validate_s3_bucket)

# Or inline lambda
PORT: int = env.require(
    "PORT",
    type=int,
    validator=lambda x: 1024 <= x <= 65535,
    error_message="Port must be between 1024 and 65535"
)
```

---

## CLI Commands

### `tripwire init` - Initialize Project

Create .env files and update .gitignore.

```bash
$ tripwire init --project-type web

Options:
  --project-type [web|cli|data|other]  Type of project (affects starter variables)

Examples:
  tripwire init                    # Initialize with default template
  tripwire init --project-type web # Web application with DATABASE_URL, etc.
```

### `tripwire generate` - Generate .env.example

Scans your code and generates .env.example automatically.

```bash
$ tripwire generate

Scanning Python files for environment variables...
Found 5 unique environment variable(s)
✓ Generated .env.example with 5 variable(s)
  - 3 required
  - 2 optional

Options:
  --output FILE    Output file (default: .env.example)
  --check          Check if .env.example is up to date (CI mode)
  --force          Overwrite existing file

Examples:
  tripwire generate                    # Create .env.example
  tripwire generate --check            # Validate in CI
  tripwire generate --output .env.dev  # Custom output
```

### `tripwire check` - Check for Drift

Compare your .env against .env.example.

```bash
$ tripwire check

Comparing .env against .env.example

Missing Variables
┌─────────────┬───────────────────┐
│ Variable    │ Status            │
├─────────────┼───────────────────┤
│ NEW_VAR     │ Not set in .env   │
└─────────────┴───────────────────┘

Found 1 missing and 0 extra variable(s)

To add missing variables:
  tripwire sync

Options:
  --env-file FILE   .env file to check (default: .env)
  --example FILE    .env.example to compare against
  --strict          Exit 1 if differences found
  --json            Output as JSON

Examples:
  tripwire check                       # Check .env vs .env.example
  tripwire check --strict              # Exit 1 if differences
  tripwire check --env-file .env.prod  # Check production env
```

### `tripwire sync` - Synchronize .env

Update your .env to match .env.example.

```bash
$ tripwire sync

Synchronizing .env with .env.example

Will add 1 missing variable(s):
  + NEW_VAR

✓ Synchronized .env
  Added 1 variable(s)

Note: Fill in values for new variables in .env

Options:
  --env-file FILE   .env file to sync (default: .env)
  --example FILE    .env.example to sync from
  --dry-run         Show changes without applying
  --interactive     Confirm each change

Examples:
  tripwire sync                        # Sync .env
  tripwire sync --dry-run              # Preview changes
  tripwire sync --interactive          # Confirm each change
```

### `tripwire scan` - Scan for Secrets

Detect potential secrets in .env file and git history.

```bash
$ tripwire scan

Scanning for secrets...

Scanning .env file...
✓ No secrets found in .env

Scanning last 100 commits in git history...
✓ No secrets found in git history

✓ No secrets detected
Your environment files appear secure

Options:
  --strict    Exit 1 if secrets found
  --depth N   Number of git commits to scan (default: 100)

Examples:
  tripwire scan               # Scan for secrets
  tripwire scan --strict      # Fail on secrets (CI)
  tripwire scan --depth 500   # Scan more commits
```

**Detects 45+ types of secrets:**
- Cloud: AWS, Azure, Google Cloud, DigitalOcean, Heroku, Alibaba, IBM
- CI/CD: GitHub, GitLab, CircleCI, Travis, Jenkins, Bitbucket, Docker Hub, Terraform
- Communication: Slack, Discord, Twilio, SendGrid
- Payments: Stripe, PayPal, Square, Shopify, Coinbase
- Email/SMS: Mailgun, Mailchimp, Postmark
- Databases: MongoDB, Redis, Firebase
- Services: Datadog, New Relic, PagerDuty, Sentry, Algolia, Cloudflare
- Package Managers: NPM, PyPI
- Generic: PASSWORD, TOKEN, SECRET, ENCRYPTION_KEY patterns

### `tripwire audit` - Audit Git History for Secret Leaks

**FLAGSHIP FEATURE** - Find when and where secrets were leaked in git history.

```bash
# Audit a specific secret
$ tripwire audit AWS_SECRET_ACCESS_KEY

Analyzing git history for: AWS_SECRET_ACCESS_KEY

Secret Leak Timeline for: AWS_SECRET_ACCESS_KEY
══════════════════════════════════════════════════════════════════════

Timeline:

📅 2024-09-15
   Commit: abc123de - Initial setup
   Author: @alice <alice@company.com>
   📁 .env:15

⚠️  Still in git history (as of HEAD)
   Affects 47 commit(s)
   Found in 1 file(s)
   Branches: origin/main, origin/develop

╭──────────────── 🚨 Security Impact ────────────────╮
│ Severity: CRITICAL                                 │
│ Exposure: PUBLIC repository                        │
│ Duration: 16 days                                  │
│ Commits affected: 47                               │
│ Files affected: 1                                  │
╰────────────────────────────────────────────────────╯

🔧 Remediation Steps:

1. Rotate the secret IMMEDIATELY
   Urgency: CRITICAL
   Generate a new secret and update all systems.

   aws iam create-access-key --user-name <username>

   ⚠️  Do not skip this step - the secret is exposed!

2. Remove from git history (using git-filter-repo)
   Urgency: HIGH
   Rewrite git history to remove the secret from 47 commit(s).

   git filter-repo --path .env --invert-paths --force

   ⚠️  This will rewrite git history. Coordinate with your team!

[... additional steps ...]
```

**Auto-detect all secrets in .env:**

```bash
$ tripwire audit --all

🔍 Auto-detecting secrets in .env file...

⚠️  Found 3 potential secret(s) in .env file

Detected Secrets
┌──────────────────────┬─────────────────┬──────────┐
│ Variable             │ Type            │ Severity │
├──────────────────────┼─────────────────┼──────────┤
│ AWS_SECRET_ACCESS_KEY│ AWS Secret Key  │ CRITICAL │
│ STRIPE_SECRET_KEY    │ Stripe API Key  │ CRITICAL │
│ DATABASE_PASSWORD    │ Generic Password│ CRITICAL │
└──────────────────────┴─────────────────┴──────────┘

════════════════════════════════════════════════════════════
Auditing: AWS_SECRET_ACCESS_KEY
════════════════════════════════════════════════════════════

[... full audit for each secret ...]

📊 Secret Leak Blast Radius
═════════════════════════════════════════════

🔍 Repository Secret Exposure
├─ 🔴 🚨 AWS_SECRET_ACCESS_KEY (47 occurrence(s))
│  ├─ Branches affected:
│  │  ├─ origin/main (47 total commits)
│  │  └─ origin/develop (47 total commits)
│  └─ Files affected:
│     └─ .env
├─ 🟡 ⚠️ STRIPE_SECRET_KEY (12 occurrence(s))
│  ├─ Branches affected:
│  │  └─ origin/main (12 total commits)
│  └─ Files affected:
│     └─ .env
└─ 🟢 DATABASE_PASSWORD (0 occurrence(s))

📈 Summary
╭────────────────────────────────────────╮
│ Leaked: 2                              │
│ Clean: 1                               │
│ Total commits affected: 59             │
╰────────────────────────────────────────╯
```

**Command options:**

```bash
# Audit specific secret
tripwire audit SECRET_NAME

# Auto-detect and audit all secrets in .env
tripwire audit --all

# Provide actual secret value for exact matching
tripwire audit API_KEY --value "sk-abc123..."

# Control commit depth
tripwire audit SECRET_KEY --max-commits 5000

# JSON output for CI/CD
tripwire audit --all --json

Options:
  SECRET_NAME         Name of secret to audit (or use --all)
  --all               Auto-detect and audit all secrets in .env
  --value TEXT        Actual secret value (more accurate)
  --max-commits INT   Maximum commits to analyze (default: 1000)
  --json              Output as JSON

Examples:
  tripwire audit AWS_SECRET_ACCESS_KEY       # Audit specific secret
  tripwire audit --all                       # Auto-detect and audit all
  tripwire audit API_KEY --value "sk-..."    # Exact value matching
  tripwire audit DATABASE_URL --json         # JSON output
```

**What it analyzes:**
- 📅 **Timeline** - When the secret first/last appeared
- 📁 **Files** - Which files contained the secret
- 👤 **Authors** - Who committed it
- 🔢 **Commits** - How many commits are affected
- 🌿 **Branches** - Which branches contain the secret
- 🌍 **Public/Private** - Whether repo is public
- 🚨 **Severity** - CRITICAL/HIGH/MEDIUM/LOW
- 🔧 **Remediation** - Step-by-step fix instructions

See [docs/audit.md](/Users/kibukx/Documents/python_projects/project_ideas/docs/audit.md) for complete documentation.

### `tripwire validate` - Validate Without Running App

Check that your .env file has all required variables.

```bash
$ tripwire validate

Validating .env...

Scanning code for environment variable requirements...
Found 5 variable(s): 3 required, 2 optional

✓ All required variables are set
  3 required variable(s) validated
  2 optional variable(s) available

Options:
  --env-file FILE   .env file to validate (default: .env)

Examples:
  tripwire validate                    # Validate current .env
  tripwire validate --env-file .env.prod
```

### `tripwire docs` - Generate Documentation

Create documentation for environment variables.

```bash
$ tripwire docs

Scanning code for environment variables...
Found 5 unique variable(s)

# Environment Variables

This document describes all environment variables used in this project.

## Required Variables

| Variable | Type | Description | Validation |
|----------|------|-------------|------------|
| `API_KEY` | string | OpenAI API key | Pattern: `^sk-[a-zA-Z0-9]{32}$` |
| `DATABASE_URL` | string | PostgreSQL connection | Format: postgresql |
| `REDIS_URL` | string | Redis connection | Format: url |

## Optional Variables

| Variable | Type | Default | Description | Validation |
|----------|------|---------|-------------|------------|
| `DEBUG` | bool | `False` | Enable debug mode | - |
| `MAX_RETRIES` | int | `3` | Max retry attempts | - |

Options:
  --format [markdown|html|json]  Output format (default: markdown)
  --output FILE                  Output file (default: stdout)

Examples:
  tripwire docs                         # Markdown to stdout
  tripwire docs --format html > doc.html
  tripwire docs --output ENV_VARS.md
```

---

## Advanced Usage

### Multi-Environment Support

Load different env files for different environments.

```python
from tripwire import env

# Load base .env
env.load(".env")

# Override with environment-specific settings
env.load(".env.local", override=True)  # Local development

# Or use environment detection
import os
environment = os.getenv("ENVIRONMENT", "development")
env.load(f".env.{environment}", override=True)
```

**File structure:**
```
.env                  # Base settings (committed)
.env.example          # Documentation (committed)
.env.local            # Local overrides (gitignored)
.env.test             # Test environment (committed)
.env.production       # Production (gitignored)
```

### Programmatic Usage

```python
from tripwire import TripWire

# Create custom instance
custom_env = TripWire(
    env_file=".env.custom",
    auto_load=True,
    strict=False,
    detect_secrets=False
)

# Load multiple files
custom_env.load_files([".env", ".env.local"])

# Get variable
api_key = custom_env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")

# Check if variable exists
if custom_env.has("FEATURE_FLAG"):
    feature_enabled = custom_env.get("FEATURE_FLAG", type=bool)

# Get all variables
all_vars = custom_env.all()  # Dict of all env vars
```

### Framework Integration Examples

#### FastAPI

```python
from fastapi import FastAPI
from tripwire import env

# Load env vars at module level (fail-fast)
DATABASE_URL: str = env.require("DATABASE_URL")
REDIS_URL: str = env.require("REDIS_URL")
SECRET_KEY: str = env.require("SECRET_KEY", secret=True)

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Env vars already validated at import time
    print(f"Connecting to {DATABASE_URL}")
```

#### Django

```python
# settings.py
from tripwire import env

# Replace os.getenv with env.require/optional
SECRET_KEY = env.require("DJANGO_SECRET_KEY", secret=True)
DEBUG = env.optional("DEBUG", default=False, type=bool)
ALLOWED_HOSTS = env.require("ALLOWED_HOSTS", type=list)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.require("DB_NAME"),
        'USER': env.require("DB_USER"),
        'PASSWORD': env.require("DB_PASSWORD", secret=True),
        'HOST': env.require("DB_HOST"),
        'PORT': env.require("DB_PORT", type=int, default=5432),
    }
}
```

#### Flask

```python
from flask import Flask
from tripwire import env

# Validate before app creation
DATABASE_URL: str = env.require("DATABASE_URL")
SECRET_KEY: str = env.require("SECRET_KEY", secret=True)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
```

---

## CI/CD Integration

### GitHub Actions - Validate Environment

```yaml
name: Validate Environment

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Validate .env.example is up to date
        run: tripwire generate --check

      - name: Check for secrets in git
        run: tripwire scan --strict
```

### GitHub Actions - Audit for Secret Leaks

```yaml
name: Secret Audit

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Need full history

      - name: Install tripwire
        run: pip install tripwire-py

      - name: Audit all secrets
        run: |
          # Create temporary .env for detection
          cat > .env << EOF
          AWS_SECRET_ACCESS_KEY=placeholder
          DATABASE_URL=placeholder
          API_KEY=placeholder
          EOF

          # Run audit
          tripwire audit --all --json > audit_results.json

          # Check if any secrets leaked
          if jq -e '.secrets[] | select(.status == "LEAKED")' audit_results.json; then
            echo "::error::Secret leak detected in git history!"
            jq . audit_results.json
            exit 1
          fi
```

---

## Comparison with Alternatives

> **Note:** This comparison reflects features as of October 2025. All libraries shown are actively maintained
> and serve different use cases. TripWire builds upon python-dotenv for .env parsing. Choose based on your
> project's specific requirements.

| Feature | TripWire | python-decouple | environs | pydantic-settings | python-dotenv |
|---------|---------|-----------------|----------|-------------------|---------------|
| Import-time validation¹ | ✅ | ❌ | ⚠️² | ⚠️³ | ❌ |
| Type coercion | ✅ | ⚠️ Basic | ✅ | ✅ | ❌ |
| Format validators | ✅ | ❌ | ✅ | ✅ | ❌ |
| .env.example generation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Team sync (drift detection) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Secret detection (45+ patterns) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Git history auditing | ✅ | ❌ | ❌ | ❌ | ❌ |
| CLI tools | ✅ | ❌ | ❌ | ❌ | ⚠️⁴ |
| Helpful error messages | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| Multi-environment | ✅ | ✅ | ✅ | ✅ | ✅ |

**Footnotes:**
1. TripWire validates when `env.require()` is called at module-level
2. environs validates eagerly by default when parsing (can be at import time)
3. pydantic-settings validates at instantiation, which can be import-time if done at module level
4. python-dotenv CLI is for command execution with .env files, not .env management

### What Makes TripWire Different?

While all these libraries handle environment variables, **TripWire focuses on the complete developer workflow**:

- **Prevent production failures** with import-time validation
- **Keep teams in sync** with automated .env.example generation
- **Protect secrets** with detection and git history auditing
- **Streamline onboarding** with CLI tools for env management

TripWire is designed for teams that want comprehensive config management, not just loading .env files.

### When to Choose Each Library

**Choose TripWire When:**
- You need guaranteed import-time validation to prevent production starts with invalid config
- Your team struggles with .env file drift and keeping documentation current
- Security is paramount and you need secret detection/git history auditing
- You want automated .env.example generation from your code
- You prefer comprehensive CLI tools for environment management
- You're on Python 3.11+ and don't mind additional dependencies for rich features

**Choose python-dotenv When:**
- You need a minimal, zero-config .env loader
- You want the de facto standard with maximum compatibility
- You're building a simple script or small project
- You prefer to handle validation separately or don't need it
- You need variable interpolation (references between env vars)
- Minimal dependencies are a priority

**Choose environs When:**
- You need comprehensive type validation powered by marshmallow
- You want extensive built-in validators (email, URL, UUID, etc.)
- You prefer explicit parsing with the option for deferred validation
- You're already using marshmallow in your project
- You want validation errors collected together rather than failing fast

**Choose pydantic-settings When:**
- Your project already uses Pydantic for data validation
- You want type safety with dataclasses/BaseModel
- You need settings to integrate seamlessly with FastAPI
- You want strict vs lax parsing modes
- You need advanced features like model validators and serializers

**Choose python-decouple When:**
- You want strict separation of config from code with minimal overhead
- You need something simple with basic type casting
- You're working on a Django project
- You want zero dependencies
- You need INI file support alongside .env

### Acknowledgments

TripWire builds on the excellent work of the Python community, particularly:
- **python-dotenv** for reliable .env file parsing
- The validation patterns pioneered by **environs** and **pydantic**
- The config separation philosophy of **python-decouple**

Each of these projects has made significant contributions to Python configuration management, and TripWire aims to complement them by focusing on team workflow and security concerns.

---

## Configuration as Code (v0.3.0)

Define your environment variables declaratively using TOML schemas.

### Quick Start

**1. Create schema:**
```bash
tripwire schema init
```

**2. Define variables in `.tripwire.toml`:**
```toml
[project]
name = "my-app"
version = "1.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
description = "PostgreSQL connection"
secret = true

[variables.PORT]
type = "int"
required = false
default = 8000
min = 1024
max = 65535

[environments.development]
DATABASE_URL = "postgresql://localhost:5432/dev"

[environments.production]
strict_secrets = true
```

**3. Validate your .env:**
```bash
tripwire schema validate --environment production
```

**4. Auto-generate .env.example:**
```bash
tripwire schema generate-example
```

### Benefits

- **Single Source of Truth** - All env var contracts in one file
- **Type Safety** - Enforced types, formats, ranges
- **Environment-Specific Defaults** - Different values for dev/staging/prod
- **CI/CD Ready** - Perfect for GitHub Actions validation
- **Auto-Documentation** - Generate .env.example from schema

### CLI Commands

#### `schema init` - Create Schema Template

```bash
$ tripwire schema init

✓ Created .tripwire.toml

Next steps:
  1. Edit .tripwire.toml to define your environment variables
  2. Run tripwire schema validate to check your .env file
  3. Run tripwire schema generate-example to create .env.example from schema
```

#### `schema validate` - Validate Against Schema

```bash
$ tripwire schema validate --environment production

Validating .env against .tripwire.toml...

Environment: production

✓ Validation passed!
All environment variables are valid

Options:
  --env-file FILE       .env file to validate (default: .env)
  --schema-file FILE    Schema file (default: .tripwire.toml)
  --environment ENV     Environment name (default: development)
  --strict              Exit with error if validation fails

Examples:
  tripwire schema validate
  tripwire schema validate --environment production --strict
  tripwire schema validate --env-file .env.prod
```

#### `schema check` - Validate Schema Syntax

```bash
$ tripwire schema check

Checking .tripwire.toml...

✓ TOML syntax is valid
✓ Schema structure is valid
✓ All format validators exist
✓ All type values are valid
✓ Environment references are valid

✓ Schema is valid

Options:
  --schema-file FILE    Schema file to validate (default: .tripwire.toml)

Examples:
  tripwire schema check
  tripwire schema check --schema-file custom.toml
```

#### `schema import` - Generate from Code

```bash
$ tripwire schema import

Scanning Python files for environment variables...
Found 5 unique variable(s)

Generating .tripwire.toml...

✓ Generated .tripwire.toml with 5 variable(s)
  - 3 required
  - 2 optional

Next steps:
  1. Review .tripwire.toml and customize as needed
  2. Run: tripwire schema validate

Options:
  --output FILE    Output schema file (default: .tripwire.toml)
  --force          Overwrite existing file

Examples:
  tripwire schema import
  tripwire schema import --output custom.toml --force
```

#### `schema generate-example` - Generate .env.example

```bash
$ tripwire schema generate-example

Generating .env.example from .tripwire.toml...

✓ Generated .env.example
  11 variable(s) defined

Options:
  --schema-file FILE    Schema file (default: .tripwire.toml)
  --output FILE         Output file (default: .env.example)
  --force               Overwrite existing file

Examples:
  tripwire schema generate-example
  tripwire schema generate-example --output .env.dev
```

### GitHub Actions Integration

```yaml
name: Validate Environment

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install tripwire-py
      - run: tripwire schema validate --environment production --strict
```

**[See full documentation →](docs/CONFIGURATION_AS_CODE.md)**

---

## Development Roadmap

### Implemented Features ✅

- [x] Environment variable loading
- [x] Import-time validation
- [x] Type coercion (str, int, bool, float, list, dict)
- [x] Format validators (email, url, uuid, ipv4, postgresql)
- [x] Custom validators
- [x] Required vs optional variables
- [x] Helpful error messages
- [x] `.env.example` generation from code
- [x] Drift detection (`check` command)
- [x] Team sync (`sync` command)
- [x] Multi-environment support
- [x] Documentation generation (`docs` command)
- [x] Secret detection (45+ platform-specific patterns)
- [x] Generic credential detection (PASSWORD, TOKEN, SECRET, etc.)
- [x] Git history scanning for secrets (`scan` command)
- [x] **Git audit with timeline and remediation** (`audit` command)
- [x] **Auto-detect and audit all secrets** (`audit --all`)
- [x] CLI implementation with rich output
- [x] Project initialization (`init` command)

### Planned Features 📋

- [ ] Pre-commit hooks (`install-hooks` command)
- [ ] Configuration file support (`tripwire.toml`)
- [ ] VS Code extension (env var autocomplete)
- [ ] PyCharm plugin
- [ ] Cloud secrets support (AWS Secrets Manager, Vault, etc.)
- [ ] Encrypted .env files
- [ ] Web UI for team env management
- [ ] Environment variable versioning
- [ ] Audit logging
- [ ] Compliance reports (SOC2, HIPAA)

---

## Contributing

We welcome contributions! Here's how to get started:

### Development Setup

```bash
# Clone repository
git clone https://github.com/Daily-Nerd/TripWire.git
cd tripwire

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Format code
black .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tripwire --cov-report=html

# Run specific test file
pytest tests/test_validation.py
```

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Inspired by:
- [python-dotenv](https://github.com/theskumar/python-dotenv) - .env file loading
- [python-decouple](https://github.com/henriquebastos/python-decouple) - Config management
- [environs](https://github.com/sloria/environs) - Environment variable parsing
- [pydantic-settings](https://github.com/pydantic/pydantic-settings) - Settings management

Built with:
- [click](https://click.palletsprojects.com/) - CLI framework
- [rich](https://rich.readthedocs.io/) - Terminal formatting
- [python-dotenv](https://github.com/theskumar/python-dotenv) - .env parsing

---

## Support

- **GitHub**: [github.com/Daily-Nerd/TripWire](https://github.com/Daily-Nerd/TripWire)
- **Issues**: [github.com/Daily-Nerd/TripWire/issues](https://github.com/Daily-Nerd/TripWire/issues)

---

**TripWire** - Environment variables that just work. 🎯

*Stop debugging production crashes. Start shipping with confidence.*
