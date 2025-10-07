# EnvSync CLI Workflow Guide

This guide demonstrates the complete EnvSync CLI workflow for managing environment variables in your project.

## Initial Setup

### 1. Initialize Your Project

```bash
# Create initial .env, .env.example, and update .gitignore
envsync init --project-type web
```

This creates:
- `.env` - Your local environment file (gitignored)
- `.env.example` - Template for team members (committed to git)
- Updates `.gitignore` to protect secrets

## Development Workflow

### 2. Write Your Application Code

```python
# app.py
from envsync import env

# Required variables
API_KEY = env.require(
    'API_KEY',
    description='API key for external service',
    secret=True,
)

DATABASE_URL = env.require(
    'DATABASE_URL',
    format='postgresql',
    description='PostgreSQL connection string',
)

# Optional variables with defaults
DEBUG = env.optional(
    'DEBUG',
    default=False,
    type=bool,
    description='Enable debug mode',
)

PORT = env.optional(
    'PORT',
    default=8000,
    type=int,
    min_val=1024,
    max_val=65535,
    description='Server port',
)
```

### 3. Generate .env.example from Code

```bash
# Scan your code and generate .env.example
envsync generate --force
```

This scans all Python files, finds `env.require()` and `env.optional()` calls, and generates a comprehensive `.env.example` file with:
- All discovered variables
- Types and validation rules in comments
- Separate sections for required vs optional variables
- Default values for optional variables

### 4. Check for Drift

```bash
# Compare .env against .env.example
envsync check

# Strict mode (exit with error if drift detected)
envsync check --strict

# JSON output for CI/CD
envsync check --json
```

This detects:
- Variables in `.env.example` but missing from `.env`
- Extra variables in `.env` not in `.env.example`

### 5. Synchronize .env with .env.example

```bash
# Preview changes
envsync sync --dry-run

# Apply changes
envsync sync

# Interactive mode (confirm each change)
envsync sync --interactive
```

This adds missing variables to your `.env` file while preserving existing values.

## Security & Validation

### 6. Scan for Secrets

```bash
# Scan .env file for exposed secrets
envsync scan

# Also scan git history
envsync scan --depth 100

# Strict mode (fail CI if secrets found)
envsync scan --strict
```

Detects:
- AWS access keys
- GitHub tokens
- API keys
- Database credentials
- High-entropy strings

### 7. Validate Environment

```bash
# Validate .env file before deploying
envsync validate

# Validate specific file
envsync validate --env-file .env.production
```

Ensures all required variables are set before running your application.

## Documentation

### 8. Generate Documentation

```bash
# Markdown docs (for README or wiki)
envsync docs --format markdown

# Save to file
envsync docs --format markdown --output docs/environment.md

# HTML docs (for internal documentation)
envsync docs --format html --output docs/environment.html

# JSON (for automation/tools)
envsync docs --format json
```

## CI/CD Integration

### Example GitHub Actions Workflow

```yaml
name: Environment Check
on: [push, pull_request]

jobs:
  env-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install EnvSync
        run: pip install envsync

      - name: Check .env.example is up to date
        run: envsync generate --check

      - name: Scan for secrets
        run: envsync scan --strict

      - name: Validate environment structure
        run: |
          cp .env.example .env
          envsync validate
```

## Team Collaboration

### For New Team Members

```bash
# 1. Clone repository
git clone <repo-url>
cd <project>

# 2. Copy example file
cp .env.example .env

# 3. Fill in values (use password manager/secret vault)
# Edit .env with your editor

# 4. Validate configuration
envsync validate
```

### When Adding New Variables

```bash
# 1. Add env.require() or env.optional() in code
# 2. Update .env.example
envsync generate --force

# 3. Commit the updated .env.example
git add .env.example
git commit -m "Add new environment variables"

# 4. Team members sync their .env
envsync sync
```

### Code Review Checklist

- [ ] `.env.example` is updated (run `envsync generate --check`)
- [ ] No secrets in git history (run `envsync scan`)
- [ ] All required variables documented
- [ ] Validation rules are appropriate

## Best Practices

1. **Never commit .env** - Always in `.gitignore`
2. **Always commit .env.example** - Template for team
3. **Use envsync generate** - Keep .env.example in sync with code
4. **Run envsync check in CI** - Prevent configuration drift
5. **Scan for secrets regularly** - `envsync scan --strict`
6. **Document variables** - Use the `description` parameter
7. **Validate before deploy** - `envsync validate` in deployment scripts

## Troubleshooting

### "No environment variables found in code"
- Ensure you're using `from envsync import env`
- Check that `.py` files aren't excluded by default patterns
- Verify you're calling `env.require()` or `env.optional()`

### "File already exists"
- Use `--force` flag to overwrite: `envsync generate --force`

### Drift detected but .env seems correct
- Run `envsync sync --dry-run` to see what would change
- Check for typos in variable names
- Ensure .env.example is up to date: `envsync generate --force`

## Advanced Usage

See `advanced_usage.py` in the examples directory for:
- Complex validation patterns
- Multiple environment configurations
- Custom validators
- Secret management integration
