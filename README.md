# EnvSync

**Smart Environment Variable Management for Python**

> Catch missing/invalid environment variables at import time (not runtime) with type validation, secret detection, and git history auditing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

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

## The Solution: EnvSync

EnvSync validates environment variables **at import time** and keeps your team in sync.

### Before EnvSync
```python
import os

# Runtime crash waiting to happen
DATABASE_URL = os.getenv("DATABASE_URL")  # Could be None
PORT = int(os.getenv("PORT"))  # ValueError if PORT not set
DEBUG = os.getenv("DEBUG") == "true"  # Wrong! Returns False for "True", "1", etc.
```

### After EnvSync
```python
from envsync import env

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
$ envsync audit --all

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
$ envsync audit AWS_SECRET_ACCESS_KEY

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
from envsync import env

# ✅ This validates IMMEDIATELY when Python imports the module
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

# Your app won't even start if config is invalid!
```

**Drift detection:**
```bash
$ envsync check

Comparing .env against .env.example

Missing Variables
┌─────────────┬───────────────────┐
│ Variable    │ Status            │
├─────────────┼───────────────────┤
│ NEW_VAR     │ Not set in .env   │
└─────────────┴───────────────────┘

Found 1 missing and 0 extra variable(s)

To add missing variables:
  envsync sync
```

---

## Quick Start

### Installation

```bash
pip install envsync
```

### Initialize Your Project

```bash
$ envsync init

Welcome to EnvSync! 🎯

✅ Created .env
✅ Created .env.example
✅ Updated .gitignore

Setup complete! ✅

Next steps:
  1. Edit .env with your configuration values
  2. Import in your code: from envsync import env
  3. Use variables: API_KEY = env.require('API_KEY')
```

### Basic Usage

```python
# app.py
from envsync import env

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
from envsync import env

# This line MUST succeed or ImportError is raised
API_KEY = env.require("API_KEY")

# No more runtime surprises!
```

### 2. Type Coercion & Validation

Automatic type conversion with validation.

```python
from envsync import env

# Strings (default)
API_KEY: str = env.require("API_KEY")

# Integers with range validation
PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
MAX_CONNECTIONS: int = env.optional("MAX_CONNECTIONS", default=100, type=int, min_val=1)

# Booleans (handles "true", "True", "1", "yes", "on", etc.)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

# Floats
TIMEOUT: float = env.optional("TIMEOUT", default=30.0, type=float)

# Lists (comma-separated or JSON)
ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS", type=list)
# .env: ALLOWED_HOSTS=localhost,example.com,api.example.com
# Or: ALLOWED_HOSTS=["localhost", "example.com"]

# Dictionaries (JSON or key=value pairs)
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={}, type=dict)
# .env: FEATURE_FLAGS={"new_ui": true, "beta": false}
# Or: FEATURE_FLAGS=new_ui=true,beta=false

# Choices/Enums
ENVIRONMENT: str = env.require(
    "ENVIRONMENT",
    choices=["development", "staging", "production"]
)
```

### 3. Format Validators

Built-in validators for common formats.

```python
from envsync import env

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
from envsync import env, validator

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

### `envsync init` - Initialize Project

Create .env files and update .gitignore.

```bash
$ envsync init --project-type web

Options:
  --project-type [web|cli|data|other]  Type of project (affects starter variables)

Examples:
  envsync init                    # Initialize with default template
  envsync init --project-type web # Web application with DATABASE_URL, etc.
```

### `envsync generate` - Generate .env.example

Scans your code and generates .env.example automatically.

```bash
$ envsync generate

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
  envsync generate                    # Create .env.example
  envsync generate --check            # Validate in CI
  envsync generate --output .env.dev  # Custom output
```

### `envsync check` - Check for Drift

Compare your .env against .env.example.

```bash
$ envsync check

Comparing .env against .env.example

Missing Variables
┌─────────────┬───────────────────┐
│ Variable    │ Status            │
├─────────────┼───────────────────┤
│ NEW_VAR     │ Not set in .env   │
└─────────────┴───────────────────┘

Found 1 missing and 0 extra variable(s)

To add missing variables:
  envsync sync

Options:
  --env-file FILE   .env file to check (default: .env)
  --example FILE    .env.example to compare against
  --strict          Exit 1 if differences found
  --json            Output as JSON

Examples:
  envsync check                       # Check .env vs .env.example
  envsync check --strict              # Exit 1 if differences
  envsync check --env-file .env.prod  # Check production env
```

### `envsync sync` - Synchronize .env

Update your .env to match .env.example.

```bash
$ envsync sync

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
  envsync sync                        # Sync .env
  envsync sync --dry-run              # Preview changes
  envsync sync --interactive          # Confirm each change
```

### `envsync scan` - Scan for Secrets

Detect potential secrets in .env file and git history.

```bash
$ envsync scan

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
  envsync scan               # Scan for secrets
  envsync scan --strict      # Fail on secrets (CI)
  envsync scan --depth 500   # Scan more commits
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

### `envsync audit` - Audit Git History for Secret Leaks

**FLAGSHIP FEATURE** - Find when and where secrets were leaked in git history.

```bash
# Audit a specific secret
$ envsync audit AWS_SECRET_ACCESS_KEY

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
$ envsync audit --all

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
envsync audit SECRET_NAME

# Auto-detect and audit all secrets in .env
envsync audit --all

# Provide actual secret value for exact matching
envsync audit API_KEY --value "sk-abc123..."

# Control commit depth
envsync audit SECRET_KEY --max-commits 5000

# JSON output for CI/CD
envsync audit --all --json

Options:
  SECRET_NAME         Name of secret to audit (or use --all)
  --all               Auto-detect and audit all secrets in .env
  --value TEXT        Actual secret value (more accurate)
  --max-commits INT   Maximum commits to analyze (default: 1000)
  --json              Output as JSON

Examples:
  envsync audit AWS_SECRET_ACCESS_KEY       # Audit specific secret
  envsync audit --all                       # Auto-detect and audit all
  envsync audit API_KEY --value "sk-..."    # Exact value matching
  envsync audit DATABASE_URL --json         # JSON output
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

### `envsync validate` - Validate Without Running App

Check that your .env file has all required variables.

```bash
$ envsync validate

Validating .env...

Scanning code for environment variable requirements...
Found 5 variable(s): 3 required, 2 optional

✓ All required variables are set
  3 required variable(s) validated
  2 optional variable(s) available

Options:
  --env-file FILE   .env file to validate (default: .env)

Examples:
  envsync validate                    # Validate current .env
  envsync validate --env-file .env.prod
```

### `envsync docs` - Generate Documentation

Create documentation for environment variables.

```bash
$ envsync docs

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
  envsync docs                         # Markdown to stdout
  envsync docs --format html > doc.html
  envsync docs --output ENV_VARS.md
```

---

## Advanced Usage

### Multi-Environment Support

Load different env files for different environments.

```python
from envsync import env

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
from envsync import EnvSync

# Create custom instance
custom_env = EnvSync(
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
from envsync import env

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
from envsync import env

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
from envsync import env

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

      - name: Install EnvSync
        run: pip install envsync

      - name: Validate .env.example is up to date
        run: envsync generate --check

      - name: Check for secrets in git
        run: envsync scan --strict
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

      - name: Install envsync
        run: pip install envsync

      - name: Audit all secrets
        run: |
          # Create temporary .env for detection
          cat > .env << EOF
          AWS_SECRET_ACCESS_KEY=placeholder
          DATABASE_URL=placeholder
          API_KEY=placeholder
          EOF

          # Run audit
          envsync audit --all --json > audit_results.json

          # Check if any secrets leaked
          if jq -e '.secrets[] | select(.status == "LEAKED")' audit_results.json; then
            echo "::error::Secret leak detected in git history!"
            jq . audit_results.json
            exit 1
          fi
```

---

## Comparison with Alternatives

| Feature | EnvSync | python-decouple | environs | pydantic-settings | python-dotenv |
|---------|---------|-----------------|----------|-------------------|---------------|
| Import-time validation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Type coercion | ✅ | ⚠️ Basic | ✅ | ✅ | ❌ |
| Format validators | ✅ | ❌ | ⚠️ Limited | ✅ | ❌ |
| .env.example generation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Team sync (drift detection) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Secret detection (45+ patterns) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Git history auditing | ✅ | ❌ | ❌ | ❌ | ❌ |
| CLI tools | ✅ | ❌ | ❌ | ❌ | ❌ |
| Helpful error messages | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| Multi-environment | ✅ | ⚠️ | ✅ | ✅ | ⚠️ |

**Why EnvSync?**

- **python-dotenv**: Just loads `.env` files, no validation
- **python-decouple**: Basic type casting, but runtime errors only
- **environs**: Good validation, but verbose API and no team sync
- **pydantic-settings**: Requires Pydantic models (overkill for simple configs)

**EnvSync combines the best features** and adds unique capabilities like git history auditing and 45+ secret detection patterns.

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
- [ ] Configuration file support (`envsync.toml`)
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
git clone https://github.com/Daily-Nerd/EnvSync.git
cd envsync

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
pytest --cov=envsync --cov-report=html

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

- **GitHub**: [github.com/Daily-Nerd/EnvSync](https://github.com/Daily-Nerd/EnvSync)
- **Issues**: [github.com/Daily-Nerd/EnvSync/issues](https://github.com/Daily-Nerd/EnvSync/issues)

---

**EnvSync** - Environment variables that just work. 🎯

*Stop debugging production crashes. Start shipping with confidence.*
