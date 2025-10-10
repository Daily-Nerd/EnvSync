# Configuration as Code - TripWire Schema System

**Status:** ✅ **Implemented** (v0.3.0)
**Feature Type:** Blue Ocean / Strategic Differentiator
**Alignment:** Directly supports GitHub Actions integration and validation workflows

---

## Overview

Configuration as Code allows you to define your environment variables declaratively using TOML schema files (`.tripwire.toml`). This provides a single source of truth for all environment variable contracts, enabling automatic validation, documentation generation, and type safety.

### Why This Matters

From the innovation-catalyst analysis:

> "Configuration as Code (CaC) - Declarative environment variable schemas with validation... Transforms TripWire from tool to platform. Opens codegen opportunities."

**Key Benefits:**
- **Single Source of Truth** - All env var contracts in one file
- **Automatic Validation** - Validate `.env` against schema before deployment
- **Type Safety** - Enforced types, formats, ranges, and constraints
- **CI/CD Integration** - Perfect for GitHub Actions validation workflows
- **Documentation Generation** - Auto-generate `.env.example` and docs from schema
- **Environment-Specific Defaults** - Different defaults for dev/staging/production

---

## Quick Start

### 1. Initialize Schema

```bash
tripwire schema init
```

Creates `.tripwire.toml` with starter template.

### 2. Define Your Variables

Edit `.tripwire.toml`:

```toml
[project]
name = "my-app"
version = "1.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
description = "PostgreSQL connection string"
secret = true
examples = ["postgresql://localhost:5432/dev"]

[variables.PORT]
type = "int"
required = false
default = 8000
min = 1024
max = 65535
description = "Server port"

[variables.DEBUG]
type = "bool"
required = false
default = false
description = "Enable debug mode"

[environments.development]
DATABASE_URL = "postgresql://localhost:5432/dev"
DEBUG = true

[environments.production]
DEBUG = false
strict_secrets = true
```

### 3. Validate Your .env File

```bash
tripwire schema validate
```

Output:
```
Validating .env against .tripwire.toml...
Environment: development

[OK] Validation passed!
All environment variables are valid
```

### 4. Generate .env.example Automatically

```bash
tripwire schema to-example
```

Creates comprehensive `.env.example` with descriptions, types, examples, and validation rules.

---

## Schema Specification

### Project Metadata

```toml
[project]
name = "project-name"          # Project identifier
version = "0.1.0"              # Schema version
description = "Description"    # Project description
```

### Validation Settings

```toml
[validation]
strict = true                  # Fail on unknown variables
allow_missing_optional = true  # Allow optional vars to be missing
warn_unused = true            # Warn about unused variables
```

### Security Settings

```toml
[security]
entropy_threshold = 4.5        # Entropy threshold for secret detection
scan_git_history = true       # Enable git history scanning
exclude_patterns = [          # Patterns to exclude from secret detection
    "TEST_*",
    "EXAMPLE_*"
]
```

### Variable Definitions

Each variable is defined under `[variables.VARIABLE_NAME]`:

```toml
[variables.API_KEY]
type = "string"               # Type: string, int, float, bool, list, dict
required = true               # Is this variable required?
default = "value"             # Default value (for optional vars)
description = "API key"       # Human-readable description
secret = true                 # Mark as secret (for auditing)
examples = ["sk-abc123"]      # Example values

# Validation rules
format = "email"              # Format validator (email, url, postgresql, uuid, ipv4)
pattern = "^sk-[a-z0-9]+$"    # Regex pattern
choices = ["opt1", "opt2"]    # Allowed values
min = 0                       # Minimum value (int/float)
max = 100                     # Maximum value (int/float)
min_length = 5                # Minimum string length
max_length = 100              # Maximum string length
```

### Environment-Specific Overrides

```toml
[environments.development]
DATABASE_URL = "postgresql://localhost:5432/dev"
DEBUG = true
LOG_LEVEL = "DEBUG"

[environments.test]
DATABASE_URL = "postgresql://localhost:5432/test"
DEBUG = false

[environments.production]
DEBUG = false
LOG_LEVEL = "INFO"
strict_secrets = true  # Fail if secrets are using example/default values
```

---

## CLI Commands

### `tripwire schema init`

Create a starter `.tripwire.toml` schema file.

```bash
tripwire schema init
```

Options:
- Creates template with commented examples
- Prompts before overwriting existing file

### `tripwire schema validate`

Validate `.env` file against schema.

```bash
# Validate .env for development environment
tripwire schema validate

# Validate for production environment
tripwire schema validate --environment production

# Validate different file
tripwire schema validate --env-file .env.prod --environment production

# Exit with error if validation fails (CI mode)
tripwire schema validate --strict
```

**Exit codes:**
- `0` - Validation passed
- `1` - Validation failed (with `--strict`)

**Output:**
```
Validating .env against .tripwire.toml...
Environment: development

[OK] Validation passed!
All environment variables are valid
```

Or on failure:
```
━(✗)━ Validation failed with 3 error(s):

Validation Errors
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Error                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Required variable missing: DATABASE_URL  │
│ PORT: Maximum value is 65535             │
│ LOG_LEVEL: Must be one of: DEBUG, INFO... │
└──────────────────────────────────────────┘
```

### `tripwire schema to-example`

Generate `.env.example` from schema.

```bash
# Generate .env.example
tripwire schema to-example

# Force overwrite
tripwire schema to-example --force

# Custom output file
tripwire schema to-example --output .env.template
```

**Generated output includes:**
- Variable descriptions
- Type information
- Validation rules (format, range, choices)
- Examples
- Required/Optional status
- Default values

Example output:
```bash
# Environment Variables
# Generated from .tripwire.toml

# Required Variables

# PostgreSQL database connection string
# Type: string | Required | Format: postgresql
# Examples: postgresql://localhost:5432/dev
DATABASE_URL=postgresql://localhost:5432/dev

# Optional Variables

# Server port number
# Type: int | Optional | Default: 8000 | Range: min: 1024, max: 65535
PORT=8000
```

### `tripwire schema to-docs`

Generate documentation from schema.

```bash
# Generate markdown docs to stdout
tripwire schema to-docs

# Save to file
tripwire schema to-docs --output ENV_VARS.md

# HTML format
tripwire schema to-docs --format html --output docs.html
```

**Output includes:**
- Project metadata
- Required variables table
- Optional variables table
- Environment-specific configurations
- Validation rules

---

## GitHub Actions Integration

### Basic Validation Workflow

```yaml
name: Validate Environment

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Validate schema against .env
        run: tripwire schema validate --strict --environment production
```

### Advanced: Multi-Environment Validation

```yaml
name: Multi-Environment Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [development, staging, production]

    steps:
      - uses: actions/checkout@v3

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Create test .env for ${{ matrix.environment }}
        run: |
          # Copy environment-specific template
          cp .env.${{ matrix.environment }}.example .env

          # Inject secrets from GitHub Secrets
          echo "DATABASE_URL=${{ secrets.DATABASE_URL }}" >> .env
          echo "API_KEY=${{ secrets.API_KEY }}" >> .env

      - name: Validate ${{ matrix.environment }} environment
        run: |
          tripwire schema validate \
            --environment ${{ matrix.environment }} \
            --strict
```

### Schema Drift Detection

```yaml
name: Check Schema Drift

on: [pull_request]

jobs:
  schema-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Generate .env.example from schema
        run: tripwire schema to-example --output /tmp/generated.env.example

      - name: Check if .env.example is up to date
        run: |
          if ! diff -q .env.example /tmp/generated.env.example; then
            echo "::error::.env.example is out of sync with schema!"
            echo "Run: tripwire schema to-example --force"
            diff .env.example /tmp/generated.env.example
            exit 1
          fi
```

### Complete CI/CD Pipeline

```yaml
name: TripWire Validation Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Step 1: Validate schema syntax
  schema-check:
    name: Validate Schema Syntax
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install TripWire
        run: pip install tripwire-py
      - name: Check schema is valid TOML
        run: python -c "import tomllib; tomllib.load(open('.tripwire.toml', 'rb'))"

  # Step 2: Validate environment files
  env-validation:
    name: Validate Environment Files
    needs: schema-check
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [development, staging, production]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install TripWire
        run: pip install tripwire-py
      - name: Create .env from template
        run: cp .env.${{ matrix.environment }}.example .env
      - name: Validate environment
        run: tripwire schema validate --environment ${{ matrix.environment }} --strict

  # Step 3: Check documentation is up to date
  docs-check:
    name: Check Documentation Sync
    needs: schema-check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install TripWire
        run: pip install tripwire-py
      - name: Generate docs
        run: tripwire schema to-docs --output /tmp/ENV_VARS.md
      - name: Check if docs are current
        run: |
          if [ -f docs/ENV_VARS.md ]; then
            if ! diff -q docs/ENV_VARS.md /tmp/ENV_VARS.md; then
              echo "::warning::Documentation is out of sync"
              echo "Run: tripwire schema to-docs --output docs/ENV_VARS.md"
            fi
          fi

  # Step 4: Security scan
  security-check:
    name: Secret Detection
    needs: env-validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install TripWire
        run: pip install tripwire-py
      - name: Scan for secrets
        run: tripwire scan --strict
```

---

## Use Cases

### 1. Pre-Deployment Validation

Ensure all required environment variables are set before deploying:

```bash
# In deployment script
tripwire schema validate --environment production --strict || {
    echo "Environment validation failed - deployment aborted"
    exit 1
}

# Deploy application
kubectl apply -f deployment.yaml
```

### 2. Developer Onboarding

New developers can quickly understand all environment variables:

```bash
# 1. Clone repo
git clone repo-url
cd repo

# 2. Initialize environment
tripwire schema to-example
cp .env.example .env

# 3. Validate setup
tripwire schema validate
```

### 3. CI/CD Quality Gates

Add validation as a quality gate in your pipeline:

```yaml
# In .github/workflows/deploy.yml
- name: Validate environment before deploy
  run: tripwire schema validate --environment production --strict
```

### 4. Documentation Generation

Keep environment variable documentation in sync automatically:

```bash
# Generate documentation
tripwire schema to-docs --output docs/ENV_VARS.md

# Commit to repo
git add docs/ENV_VARS.md
git commit -m "docs: Update environment variable documentation"
```

---

## Advanced Features

### Type-Safe Validation

Schema enforces type constraints:

```toml
[variables.MAX_CONNECTIONS]
type = "int"
min = 1
max = 1000

[variables.TIMEOUT]
type = "float"
min = 0.1
max = 300.0

[variables.FEATURE_FLAGS]
type = "dict"  # Validates JSON objects
```

### Format Validation

Built-in format validators:

```toml
[variables.ADMIN_EMAIL]
format = "email"  # Validates email format

[variables.API_URL]
format = "url"  # Validates URL format

[variables.DATABASE_URL]
format = "postgresql"  # Validates PostgreSQL connection string

[variables.SERVICE_ID]
format = "uuid"  # Validates UUID format

[variables.SERVER_IP]
format = "ipv4"  # Validates IPv4 address
```

### Enum/Choices Validation

Restrict to specific values:

```toml
[variables.LOG_LEVEL]
type = "string"
choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

[variables.ENVIRONMENT]
type = "string"
choices = ["development", "staging", "production"]
```

### Pattern Matching

Custom regex validation:

```toml
[variables.API_KEY]
type = "string"
pattern = "^sk-[a-zA-Z0-9]{32}$"
description = "Must start with 'sk-' followed by 32 alphanumeric characters"
```

---

## Migration Guide

### From Manual .env.example to Schema

**Step 1:** Create schema from existing .env.example

```bash
tripwire schema init
```

**Step 2:** Manually transfer variables to `.tripwire.toml`

For each variable in your `.env.example`, create an entry:

```toml
[variables.YOUR_VARIABLE]
type = "string"  # or int, bool, etc.
required = true  # or false
description = "Description from .env.example comments"
```

**Step 3:** Add validation rules

Enhance with types, formats, ranges:

```toml
[variables.PORT]
type = "int"
required = false
default = 8000
min = 1024
max = 65535
```

**Step 4:** Validate against existing .env

```bash
tripwire schema validate
```

Fix any validation errors.

**Step 5:** Replace .env.example generation

Update your workflow to use schema:

```bash
# Old
tripwire generate

# New
tripwire schema to-example
```

### From Code Scanning to Schema

If you're using `tripwire generate` (code scanning), transition to schema:

**Step 1:** Generate schema from current code

```bash
# Scan code
tripwire generate --output /tmp/vars.txt

# Use output to create schema entries
```

**Step 2:** Add validation rules manually

Code scanning can't infer validation rules - add them in schema:

```toml
[variables.DETECTED_VAR]
type = "string"
format = "email"  # Add this manually
```

**Step 3:** Use schema validation in CI

Replace code scanning validation with schema validation:

```yaml
# Old
- run: tripwire generate --check

# New
- run: tripwire schema validate --strict
```

---

## Best Practices

### 1. Keep Schema in Version Control

```bash
git add .tripwire.toml
git commit -m "feat: Add environment variable schema"
```

### 2. Environment-Specific Defaults

Use environment sections for different deployments:

```toml
[environments.development]
DATABASE_URL = "postgresql://localhost:5432/dev"
DEBUG = true
LOG_LEVEL = "DEBUG"

[environments.production]
DEBUG = false
LOG_LEVEL = "INFO"
strict_secrets = true
```

### 3. Document Why, Not Just What

Use descriptions to explain purpose:

```toml
[variables.MAX_RETRIES]
description = "Maximum retry attempts for failed API calls. Set to 0 to disable retries. Higher values improve reliability but increase latency."
```

### 4. Use Examples Effectively

Provide realistic examples:

```toml
examples = [
    "postgresql://user:pass@prod-db.company.com:5432/production",
    "postgresql://localhost:5432/dev"
]
```

### 5. Secret Marking

Mark sensitive variables as secrets:

```toml
[variables.API_KEY]
secret = true  # Enables secret detection and auditing
```

### 6. Validate Early and Often

Add validation to all stages:

```bash
# Local development
tripwire schema validate

# Pre-commit hook
tripwire schema validate --strict

# CI/CD
tripwire schema validate --environment production --strict

# Pre-deployment
tripwire schema validate --environment production --strict
```

---

## Troubleshooting

### Common Errors

**Error:** `Schema file not found: .tripwire.toml`

**Solution:** Run `tripwire schema init` to create schema file.

---

**Error:** `Required variable missing: DATABASE_URL`

**Solution:** Add the variable to your `.env` file or mark it as optional in schema.

---

**Error:** `PORT: Maximum value is 65535`

**Solution:** Ensure PORT value is within the specified range.

---

**Error:** `LOG_LEVEL: Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL`

**Solution:** Use one of the allowed choices defined in schema.

---

**Error:** `Unknown variable: EXTRA_VAR (not in schema)`

**Solution:** Either remove the variable from `.env` or add it to schema. If using `strict = false`, this is just a warning.

---

## Comparison with Alternatives

### vs. Code Scanning (`tripwire generate`)

| Feature | Schema (`tripwire schema`) | Code Scanning (`tripwire generate`) |
|---------|----------------------------|-------------------------------------|
| **Single source of truth** | ✅ `.tripwire.toml` | ❌ Scattered across code |
| **Type validation** | ✅ Enforced | ❌ No validation |
| **Format validation** | ✅ Yes | ❌ No |
| **Environment-specific** | ✅ Built-in | ❌ Manual |
| **Documentation generation** | ✅ Rich, structured | ⚠️ Basic |
| **CI/CD integration** | ✅ Excellent | ⚠️ Limited |
| **Setup effort** | ⚠️ Manual schema creation | ✅ Automatic scanning |

**Recommendation:** Use schema for production applications. Use code scanning for quick prototyping.

### vs. pydantic-settings

TripWire schema provides configuration as code WITHOUT requiring code changes. pydantic-settings requires defining classes in your application code.

**TripWire Schema:**
```toml
# .tripwire.toml (separate config file)
[variables.DATABASE_URL]
type = "string"
format = "postgresql"
```

**pydantic-settings:**
```python
# settings.py (in application code)
class Settings(BaseSettings):
    DATABASE_URL: PostgresqlUrl
```

**Advantage:** TripWire schema is language-agnostic and can be used for validation without running application code.

---

## Future Enhancements

### Planned Features (v0.4.0+)

1. **Code Generation** - Generate type-safe Python classes from schema
2. **Schema Versioning** - Track schema changes over time
3. **Schema Validation API** - HTTP API for remote validation
4. **IDE Integration** - VSCode extension with schema autocomplete
5. **Multi-Language Support** - Generate TypeScript/Go types from schema

---

## Related Documentation

- **GitHub Actions Integration:** `.github/workflows/ci.yml`
- **CLI Reference:** [CLI Commands](./cli.md)
- **Validation Guide:** [Validation](./validation.md)
- **Migration Checklist:** [Migration](./MIGRATION_CHECKLIST.md)

---

**TripWire v0.3.0** - Configuration as Code for Modern Applications 🎯
