[Home](../README.md) / [Guides](README.md) / CLI Reference

# CLI Command Reference

Complete reference for all TripWire CLI commands with examples and best practices.

---

## Table of Contents

- [Core Commands](#core-commands)
  - [init](#tripwire-init)
  - [generate](#tripwire-generate)
  - [check](#tripwire-check)
  - [sync](#tripwire-sync)
  - [diff](#tripwire-diff)
- [Secret Management](#secret-management)
  - [scan](#tripwire-scan)
  - [audit](#tripwire-audit)
- [Schema Commands](#schema-commands)
  - [schema init](#tripwire-schema-init)
  - [schema validate](#tripwire-schema-validate)
  - [schema check](#tripwire-schema-check)
  - [schema import](#tripwire-schema-import)
  - [schema generate-example](#tripwire-schema-generate-example)
- [Validation](#validation)
  - [validate](#tripwire-validate)
  - [docs](#tripwire-docs)
- [Migration](#migration)
  - [migrate-to-schema](#tripwire-migrate-to-schema)

---

## Core Commands

### `tripwire init`

Initialize a new TripWire project with `.env` files and `.gitignore`.

**Syntax:**
```bash
tripwire init [OPTIONS]
```

**Options:**
- `--project-type [web|cli|data|other]` - Type of project (affects starter variables)
- `--force` - Overwrite existing files

**Examples:**

```bash
# Initialize with default template
tripwire init

# Initialize web application project
tripwire init --project-type web

# Initialize CLI tool
tripwire init --project-type cli

# Force overwrite existing files
tripwire init --force
```

**Output:**
```
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

**Project Templates:**

- **`web`**: Includes DATABASE_URL, SECRET_KEY, DEBUG, PORT
- **`cli`**: Includes LOG_LEVEL, OUTPUT_DIR, CONFIG_FILE
- **`data`**: Includes API_ENDPOINT, BATCH_SIZE, DATA_DIR
- **`other`**: Minimal template with common variables

**Best Practices:**
- Run `tripwire init` once per project
- Commit `.env.example` and `.gitignore` to version control
- Never commit `.env` to version control

---

### `tripwire generate`

Scan your code and generate `.env.example` automatically.

**Syntax:**
```bash
tripwire generate [OPTIONS]
```

**Options:**
- `--output FILE` - Output file (default: `.env.example`)
- `--check` - Check if `.env.example` is up to date (CI mode, exits 1 if outdated)
- `--force` - Overwrite existing file without prompting
- `--from-schema` - Generate from `.tripwire.toml` schema instead of code scanning

**Examples:**

```bash
# Generate .env.example from code
tripwire generate

# Check if .env.example is up to date (CI)
tripwire generate --check

# Generate to custom file
tripwire generate --output .env.dev

# Generate from schema file
tripwire generate --from-schema

# Force overwrite
tripwire generate --force
```

**Output:**
```
Scanning Python files for environment variables...
Found 5 unique environment variable(s)
✓ Generated .env.example with 5 variable(s)
  - 3 required
  - 2 optional
```

**How It Works:**
1. Scans all `.py` files in project
2. Finds `env.require()` and `env.optional()` calls
3. Extracts variable names, types, defaults, and descriptions
4. Generates commented `.env.example` template

**Best Practices:**
- Run after adding new environment variables
- Use `--check` in CI to ensure documentation stays current
- Commit generated `.env.example` to version control

---

### `tripwire check`

Compare your `.env` against `.env.example` to detect drift.

**Syntax:**
```bash
tripwire check [OPTIONS]
```

**Options:**
- `--env-file FILE` - `.env` file to check (default: `.env`)
- `--example FILE` - `.env.example` to compare against (default: `.env.example`)
- `--strict` - Exit 1 if differences found
- `--json` - Output as JSON for scripting

**Examples:**

```bash
# Check .env vs .env.example
tripwire check

# Check with strict mode (fails if drift)
tripwire check --strict

# Check production environment
tripwire check --env-file .env.prod

# JSON output for scripts
tripwire check --json
```

**Output:**
```
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

**Use Cases:**
- Local development: Ensure you have all required variables
- CI/CD: Verify environment files are complete
- Team sync: Check if team members are missing variables

**Best Practices:**
- Run before deploying to new environment
- Add to pre-commit hooks
- Use `--strict` in CI to enforce completeness

---

### `tripwire sync`

Synchronize your `.env` to match `.env.example`.

**Syntax:**
```bash
tripwire sync [OPTIONS]
```

**Options:**
- `--env-file FILE` - `.env` file to sync (default: `.env`)
- `--example FILE` - `.env.example` to sync from (default: `.env.example`)
- `--dry-run` - Show changes without applying
- `--interactive` - Confirm each change

**Examples:**

```bash
# Sync .env with .env.example
tripwire sync

# Preview changes
tripwire sync --dry-run

# Interactive mode
tripwire sync --interactive

# Sync production environment
tripwire sync --env-file .env.prod
```

**Output:**
```
Synchronizing .env with .env.example

Will add 1 missing variable(s):
  + NEW_VAR

✓ Synchronized .env
  Added 1 variable(s)

Note: Fill in values for new variables in .env
```

**What It Does:**
- Adds missing variables from `.env.example`
- Preserves existing values
- Does NOT remove extra variables (safety feature)
- Does NOT modify existing values

**Best Practices:**
- Review changes with `--dry-run` first
- Fill in values for new variables immediately
- Use `--interactive` for sensitive environments

---

### `tripwire diff`

Compare configuration files to identify differences. (New in v0.4.0)

**Syntax:**
```bash
tripwire diff <source> <target> [OPTIONS]
```

**Options:**
- `--format [table|summary|json]` - Output format (default: `table`)
- `--show-secrets` - Show secret values (use with caution!)
- `--hide-secrets` - Hide secret values (default)

**Examples:**

```bash
# Compare environments
tripwire diff .env .env.prod

# Compare .env vs TOML
tripwire diff .env pyproject.toml

# Summary format
tripwire diff .env.dev .env.staging --format=summary

# JSON output for scripts
tripwire diff .env .env.prod --format=json

# Show secret values (dangerous!)
tripwire diff .env .env.prod --show-secrets
```

**Output (table format):**
```
Comparing configurations: .env vs .env.prod

           Configuration Differences: .env vs .env.prod
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Status     ┃ Variable     ┃ .env              ┃ .env.prod         ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ + Added    │ PROD_FEATURE │                   │ enabled           │
│ - Removed  │ DEV_MODE     │ true              │                   │
│ ~ Modified │ DATABASE_URL │ localhost:5432/dev│ prod-db:5432/app  │
│ ~ Modified │ PORT         │ 8000              │ 80                │
└────────────┴──────────────┴───────────────────┴───────────────────┘

1 added, 1 removed, 2 modified
```

**Supported Formats:**
- `.env` files
- `.toml` / `pyproject.toml` files
- Cross-format comparison

**Use Cases:**
- Spot environment differences before deployment
- Verify configuration migrations
- Audit drift across environments
- Generate deployment reports

**Best Practices:**
- Always use `--hide-secrets` (default) when sharing output
- Use `--format=json` for automated tools
- Compare staging against production before releases

---

## Secret Management

### `tripwire scan`

Scan for potential secrets in `.env` file and git history.

**Syntax:**
```bash
tripwire scan [OPTIONS]
```

**Options:**
- `--strict` - Exit 1 if secrets found
- `--depth N` - Number of git commits to scan (default: 100)

**Examples:**

```bash
# Scan for secrets
tripwire scan

# Fail on secrets (CI)
tripwire scan --strict

# Scan more git history
tripwire scan --depth 500
```

**Output:**
```
Scanning for secrets...

Scanning .env file...
✓ No secrets found in .env

Scanning last 100 commits in git history...
✓ No secrets found in git history

✓ No secrets detected
Your environment files appear secure
```

**Detects 45+ Secret Types:**
- Cloud: AWS, Azure, GCP, DigitalOcean, Heroku, Alibaba, IBM
- CI/CD: GitHub, GitLab, CircleCI, Travis, Jenkins
- Communication: Slack, Discord, Twilio, SendGrid
- Payments: Stripe, PayPal, Square, Shopify
- Generic: PASSWORD, TOKEN, SECRET, API_KEY

**Best Practices:**
- Run in CI/CD pipeline
- Use `--strict` to prevent deployment with secrets
- Scan regularly with `--depth 1000` for comprehensive check

---

### `tripwire audit`

Audit git history for secret leaks with timeline and remediation.

**Syntax:**
```bash
tripwire audit [SECRET_NAME] [OPTIONS]
```

**Options:**
- `SECRET_NAME` - Name of secret to audit (or use `--all`)
- `--all` - Auto-detect and audit all secrets in `.env`
- `--value TEXT` - Actual secret value for exact matching
- `--max-commits INT` - Maximum commits to analyze (default: 1000)
- `--json` - Output as JSON

**Examples:**

```bash
# Audit specific secret
tripwire audit AWS_SECRET_ACCESS_KEY

# Auto-detect and audit all
tripwire audit --all

# Audit with exact value
tripwire audit API_KEY --value "sk-abc123..."

# Deep history scan
tripwire audit DATABASE_URL --max-commits 5000

# JSON output
tripwire audit --all --json
```

**Output:**
```
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

2. Remove from git history (using git-filter-repo)
   Urgency: HIGH

   git filter-repo --path .env --invert-paths --force
```

**What It Analyzes:**
- Timeline of when secret first/last appeared
- Which files contained the secret
- Who committed it (authors)
- How many commits are affected
- Which branches contain the secret
- Public/private repository status
- Severity calculation
- Step-by-step remediation instructions

**Best Practices:**
- Run `--all` after finding leaked secrets
- Follow remediation steps in order
- Coordinate with team before rewriting git history
- Use `--json` for integration with security tools

See [Git Audit Deep Dive](../advanced/git-audit.md) for detailed documentation.

---

## Schema Commands

### `tripwire schema init`

Create a `.tripwire.toml` schema template.

**Syntax:**
```bash
tripwire schema init [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing schema file

**Examples:**

```bash
# Create schema template
tripwire schema init

# Force overwrite
tripwire schema init --force
```

**Output:**
```
✓ Created .tripwire.toml

Next steps:
  1. Edit .tripwire.toml to define your environment variables
  2. Run tripwire schema validate to check your .env file
  3. Run tripwire schema generate-example to create .env.example from schema
```

**Generated File:**
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
```

---

### `tripwire schema validate`

Validate `.env` against `.tripwire.toml` schema.

**Syntax:**
```bash
tripwire schema validate [OPTIONS]
```

**Options:**
- `--env-file FILE` - `.env` file to validate (default: `.env`)
- `--schema-file FILE` - Schema file (default: `.tripwire.toml`)
- `--environment ENV` - Environment name (default: `development`)
- `--strict` - Exit with error if validation fails

**Examples:**

```bash
# Validate against schema
tripwire schema validate

# Validate production environment
tripwire schema validate --environment production

# Strict mode (fail on errors)
tripwire schema validate --strict

# Custom schema file
tripwire schema validate --schema-file custom.toml
```

**Output:**
```
Validating .env against .tripwire.toml...

Environment: production

✓ Validation passed!
All environment variables are valid
```

---

### `tripwire schema check`

Validate schema file syntax and structure.

**Syntax:**
```bash
tripwire schema check [OPTIONS]
```

**Options:**
- `--schema-file FILE` - Schema file to validate (default: `.tripwire.toml`)

**Examples:**

```bash
# Check schema syntax
tripwire schema check

# Check custom schema
tripwire schema check --schema-file custom.toml
```

**Output:**
```
Checking .tripwire.toml...

✓ TOML syntax is valid
✓ Schema structure is valid
✓ All format validators exist
✓ All type values are valid
✓ Environment references are valid

✓ Schema is valid
```

---

### `tripwire schema import`

Generate `.tripwire.toml` schema from your code.

**Syntax:**
```bash
tripwire schema import [OPTIONS]
```

**Options:**
- `--output FILE` - Output schema file (default: `.tripwire.toml`)
- `--force` - Overwrite existing file

**Examples:**

```bash
# Generate schema from code
tripwire schema import

# Custom output
tripwire schema import --output custom.toml

# Force overwrite
tripwire schema import --force
```

**Output:**
```
Scanning Python files for environment variables...
Found 5 unique variable(s)

Generating .tripwire.toml...

✓ Generated .tripwire.toml with 5 variable(s)
  - 3 required
  - 2 optional

Next steps:
  1. Review .tripwire.toml and customize as needed
  2. Run: tripwire schema validate
```

---

### `tripwire schema generate-example`

Generate `.env.example` from `.tripwire.toml` schema.

**Syntax:**
```bash
tripwire schema generate-example [OPTIONS]
```

**Options:**
- `--schema-file FILE` - Schema file (default: `.tripwire.toml`)
- `--output FILE` - Output file (default: `.env.example`)
- `--force` - Overwrite existing file

**Examples:**

```bash
# Generate .env.example from schema
tripwire schema generate-example

# Custom output
tripwire schema generate-example --output .env.dev

# Force overwrite
tripwire schema generate-example --force
```

**Output:**
```
Generating .env.example from .tripwire.toml...

✓ Generated .env.example
  11 variable(s) defined
```

---

## Validation

### `tripwire validate`

Validate that your `.env` file has all required variables.

**Syntax:**
```bash
tripwire validate [OPTIONS]
```

**Options:**
- `--env-file FILE` - `.env` file to validate (default: `.env`)

**Examples:**

```bash
# Validate current .env
tripwire validate

# Validate production .env
tripwire validate --env-file .env.prod
```

**Output:**
```
Validating .env...

Scanning code for environment variable requirements...
Found 5 variable(s): 3 required, 2 optional

✓ All required variables are set
  3 required variable(s) validated
  2 optional variable(s) available
```

---

### `tripwire docs`

Generate documentation for environment variables.

**Syntax:**
```bash
tripwire docs [OPTIONS]
```

**Options:**
- `--format [markdown|html|json]` - Output format (default: `markdown`)
- `--output FILE` - Output file (default: stdout)

**Examples:**

```bash
# Generate markdown docs
tripwire docs

# Generate HTML
tripwire docs --format html > docs.html

# Save to file
tripwire docs --output ENV_VARS.md

# JSON format
tripwire docs --format json
```

**Output:**
```markdown
# Environment Variables

This document describes all environment variables used in this project.

## Required Variables

| Variable | Type | Description | Validation |
|----------|------|-------------|------------|
| `API_KEY` | string | OpenAI API key | Pattern: `^sk-[a-zA-Z0-9]{32}$` |
| `DATABASE_URL` | string | PostgreSQL connection | Format: postgresql |

## Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEBUG` | bool | `False` | Enable debug mode |
| `PORT` | int | `8000` | HTTP server port |
```

---

## Migration

### `tripwire migrate-to-schema`

Migrate legacy `.env.example` to modern `.tripwire.toml` schema. (New in v0.4.1)

**Syntax:**
```bash
tripwire migrate-to-schema [OPTIONS]
```

**Options:**
- `--env-example FILE` - `.env.example` file to migrate (default: `.env.example`)
- `--output FILE` - Output schema file (default: `.tripwire.toml`)
- `--force` - Overwrite existing schema file

**Examples:**

```bash
# Migrate .env.example to schema
tripwire migrate-to-schema

# Custom input/output
tripwire migrate-to-schema --env-example .env.sample --output schema.toml

# Force overwrite
tripwire migrate-to-schema --force
```

**Output:**
```
Migrating .env.example to .tripwire.toml...

✓ Analyzed 12 variable(s)
  - 8 required
  - 4 optional
  - 3 secrets detected
  - 2 URLs detected
  - 1 PostgreSQL connection detected

✓ Generated .tripwire.toml

Next steps:
  1. Review .tripwire.toml and customize
  2. Run: tripwire schema validate
```

**What It Does:**
- Automatic type inference (int, float, bool, string)
- Secret detection based on variable names
- Format detection (postgresql, url, email, ipv4)
- Placeholder detection (your-*-here, change-me)
- Preserves comments and descriptions

---

## Best Practices

### CI/CD Integration

```yaml
# .github/workflows/validate.yml
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

      # Check .env.example is up to date
      - run: tripwire generate --check

      # Scan for secrets
      - run: tripwire scan --strict

      # Validate schema
      - run: tripwire schema validate --strict
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tripwire-generate
        name: Update .env.example
        entry: tripwire generate --check
        language: system
        pass_filenames: false

      - id: tripwire-scan
        name: Scan for secrets
        entry: tripwire scan --strict
        language: system
        pass_filenames: false
```

### Development Workflow

```bash
# 1. Add new environment variable to code
# config.py
NEW_VAR: str = env.require("NEW_VAR", format="url")

# 2. Generate .env.example
tripwire generate

# 3. Check if local .env needs update
tripwire check

# 4. Sync if needed
tripwire sync

# 5. Fill in value
# Edit .env: NEW_VAR=https://example.com

# 6. Validate
tripwire validate

# 7. Commit
git add config.py .env.example
git commit -m "Add NEW_VAR configuration"
```

---

**[Back to Guides](README.md)**
