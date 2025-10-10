[Home](../README.md) / [Guides](README.md) / Multi-Environment

# Multi-Environment Configuration

Manage development, staging, and production configurations with TripWire.

---

## File Structure

Recommended structure for multi-environment projects:

```
project/
├── .env                  # Base config (committed, no secrets)
├── .env.example          # Template (committed)
├── .env.local            # Local overrides (gitignored)
├── .env.development      # Dev config (committed, no secrets)
├── .env.staging          # Staging config (committed, no secrets)
├── .env.production       # Prod config (gitignored, has secrets)
└── .env.test             # Test config (committed)
```

**`.gitignore`:**
```
.env.local
.env.production
.env.*.local
```

---

## Loading Strategy

### Method 1: Environment Variable

```python
# config.py
from tripwire import env
import os

# Load base configuration
env.load(".env")

# Load environment-specific configuration
environment = os.getenv("ENVIRONMENT", "development")
env.load(f".env.{environment}", override=True)

# Load local overrides (developer-specific)
env.load(".env.local", override=True, silent=True)

# Now declare variables
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
DEBUG: bool = env.optional("DEBUG", default=False)
```

**Usage:**
```bash
# Development (default)
python app.py

# Staging
ENVIRONMENT=staging python app.py

# Production
ENVIRONMENT=production python app.py
```

### Method 2: Explicit Loading

```python
# config.py
from tripwire import TripWire

def load_config(environment: str = "development"):
    """Load configuration for specific environment."""
    tw = TripWire()

    # Load in order of precedence (last wins)
    tw.load(".env")  # Base
    tw.load(f".env.{environment}", override=True)  # Environment-specific
    tw.load(".env.local", override=True, silent=True)  # Local overrides

    return tw

# Create environment-specific instances
dev_env = load_config("development")
prod_env = load_config("production")
```

---

## Configuration Examples

### `.env` (Base - Committed)

```bash
# Base configuration - shared across all environments
# NO SECRETS HERE!

# Application
APP_NAME=MyApp
LOG_FORMAT=json

# Database
DB_POOL_SIZE=5
DB_POOL_MAX_OVERFLOW=10

# Features
FEATURE_ANALYTICS=true
```

### `.env.development` (Committed)

```bash
# Development environment
DEBUG=true
LOG_LEVEL=DEBUG

# Local database
DATABASE_URL=postgresql://localhost:5432/myapp_dev

# Local Redis
REDIS_URL=redis://localhost:6379/0

# Development API keys (test keys only!)
STRIPE_API_KEY=sk_test_...
OPENAI_API_KEY=sk-test-...
```

### `.env.staging` (Committed)

```bash
# Staging environment
DEBUG=false
LOG_LEVEL=INFO

# Staging database (placeholder - actual value in secrets)
DATABASE_URL=postgresql://staging-db:5432/myapp

# Staging Redis
REDIS_URL=redis://staging-redis:6379/0

# Note: Actual API keys injected via CI/CD secrets
```

### `.env.production` (Gitignored - Has Secrets)

```bash
# Production environment
DEBUG=false
LOG_LEVEL=WARNING

# Production database
DATABASE_URL=postgresql://prod-db.internal:5432/myapp

# Production Redis with auth
REDIS_URL=redis://:actual-password@prod-redis.internal:6379/0

# Real API keys
STRIPE_API_KEY=sk_live_actual_key_here
OPENAI_API_KEY=sk-proj-actual_key_here
SECRET_KEY=actual_production_secret_here
```

### `.env.local` (Gitignored - Developer-Specific)

```bash
# Personal overrides for this developer
# Overrides any value from other files

# Use local Postgres instead of Docker
DATABASE_URL=postgresql://localhost:5432/myapp_local

# Increase log verbosity
LOG_LEVEL=DEBUG

# Personal test API key
OPENAI_API_KEY=sk-my-personal-test-key
```

### `.env.test` (Committed)

```bash
# Test environment
DEBUG=false
LOG_LEVEL=ERROR

# In-memory database for tests
DATABASE_URL=sqlite:///:memory:

# Mock Redis
REDIS_URL=redis://localhost:6379/15

# Test API keys (non-functional)
STRIPE_API_KEY=sk_test_mock
OPENAI_API_KEY=sk-test-mock
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install tripwire-py
          pip install -r requirements.txt

      - name: Create test .env
        run: cp .env.test .env

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          SECRET_KEY: ${{ secrets.TEST_SECRET_KEY }}
        run: pytest

  deploy-staging:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3

      - name: Create staging .env
        run: |
          cat > .env << EOF
          DATABASE_URL=${{ secrets.STAGING_DATABASE_URL }}
          REDIS_URL=${{ secrets.STAGING_REDIS_URL }}
          SECRET_KEY=${{ secrets.STAGING_SECRET_KEY }}
          STRIPE_API_KEY=${{ secrets.STAGING_STRIPE_KEY }}
          EOF

      - name: Validate configuration
        run: |
          pip install tripwire-py
          tripwire validate

      - name: Deploy to staging
        run: ./deploy-staging.sh
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
    env_file:
      - .env
      - .env.${ENVIRONMENT:-development}
      - .env.local
    ports:
      - "8000:8000"
```

**Usage:**
```bash
# Development
docker-compose up

# Staging
ENVIRONMENT=staging docker-compose up

# Production
ENVIRONMENT=production docker-compose up
```

---

## Best Practices

### 1. Layered Configuration

Load configs in order from least to most specific:

```python
# Lowest priority
env.load(".env")                # Base defaults

# Medium priority
env.load(".env.development")    # Environment-specific

# Highest priority
env.load(".env.local")          # Developer overrides
```

### 2. No Secrets in Committed Files

**✅ DO:**
```bash
# .env.development (committed)
STRIPE_API_KEY=sk_test_placeholder
```

**❌ DON'T:**
```bash
# .env.development (committed)
STRIPE_API_KEY=sk_live_actual_secret  # NEVER!
```

### 3. Document Required Variables

```bash
# .env.example
# PostgreSQL connection string
# Development: postgresql://localhost:5432/myapp_dev
# Production: Set via CI/CD secrets
DATABASE_URL=

# Secret key for sessions (generate with: openssl rand -hex 32)
SECRET_KEY=
```

### 4. Validate Per Environment

```python
# config.py
ENVIRONMENT: str = env.optional("ENVIRONMENT", default="development")

if ENVIRONMENT == "production":
    # Stricter validation for production
    SECRET_KEY: str = env.require("SECRET_KEY", min_length=64, secret=True)
    DEBUG: bool = False  # Force DEBUG=False in production
else:
    SECRET_KEY: str = env.require("SECRET_KEY", min_length=32, secret=True)
    DEBUG: bool = env.optional("DEBUG", default=True)
```

### 5. Use Schema for Complex Configs

```toml
# .tripwire.toml
[environments.development]
DATABASE_URL = "postgresql://localhost:5432/myapp_dev"
DEBUG = true
LOG_LEVEL = "DEBUG"

[environments.staging]
DATABASE_URL = "postgresql://staging-db:5432/myapp"
DEBUG = false
LOG_LEVEL = "INFO"

[environments.production]
strict_secrets = true  # Enforce all secrets are set
DATABASE_URL = ""  # Must be provided
DEBUG = false
LOG_LEVEL = "WARNING"
```

---

## Common Patterns

### Database URLs

```bash
# .env.development
DATABASE_URL=postgresql://localhost:5432/myapp_dev

# .env.staging
DATABASE_URL=postgresql://staging:5432/myapp

# .env.production
DATABASE_URL=postgresql://user:pass@prod-db.internal:5432/myapp
```

### Feature Flags

```bash
# .env.development
ENABLE_NEW_UI=true
ENABLE_BETA_API=true
ENABLE_ANALYTICS=false

# .env.staging
ENABLE_NEW_UI=true
ENABLE_BETA_API=false
ENABLE_ANALYTICS=true

# .env.production
ENABLE_NEW_UI=false
ENABLE_BETA_API=false
ENABLE_ANALYTICS=true
```

### API Endpoints

```bash
# .env.development
API_BASE_URL=http://localhost:8000/api/v1

# .env.staging
API_BASE_URL=https://api-staging.example.com/v1

# .env.production
API_BASE_URL=https://api.example.com/v1
```

---

## Troubleshooting

### Issue: Wrong environment loaded

**Problem:** Production config loaded in development.

**Solution:**
```python
# Add validation
ENVIRONMENT: str = env.optional("ENVIRONMENT", default="development")
assert ENVIRONMENT in ["development", "staging", "production"]

print(f"Loaded environment: {ENVIRONMENT}")
```

### Issue: Local overrides not working

**Problem:** `.env.local` values ignored.

**Solution:** Ensure `override=True`:
```python
env.load(".env.local", override=True)  # ✅ override=True
```

### Issue: Secrets in wrong file

**Problem:** Committed secrets accidentally.

**Solution:**
```bash
# Remove from git
git rm --cached .env.production
echo ".env.production" >> .gitignore

# Scan for leaks
tripwire audit --all
```

---

**[Back to Guides](README.md)**
