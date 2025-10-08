# EnvSync

**Smart Environment Variable Management for Python**

> Catch missing/invalid environment variables at import time (not runtime) with automatic .env sync, type validation, and team collaboration features.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 The Problem

Every Python developer has experienced this:

```python
# Your code
import os
API_KEY = os.getenv("API_KEY")  # Typo: should be "API_KEY" not "APIKEY"

# 2 hours later in production...
response = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
# 💥 TypeError: can only concatenate str (not "NoneType") to str

# Production is down. Users are angry. You're debugging at 2 AM.
```

**The pain:**
- Environment variables fail at **runtime**, not at startup
- No validation (wrong types, missing values, invalid formats)
- `.env` files drift across team members
- New developers don't know what env vars they need
- Secrets accidentally committed to git
- No type safety for configuration

**The cost:**
- Production crashes
- Hours of debugging
- Security vulnerabilities
- Team frustration

---

## ✨ The Solution: EnvSync

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
PORT: int = env.require("PORT", type=int, range=(1, 65535))
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

# Your app won't even start with bad config!
```

**Key Benefits:**
- ✅ **Import-time validation** - Fail fast, not in production
- ✅ **Type safety** - Automatic type coercion with validation
- ✅ **Team sync** - Keep `.env` files consistent across team
- ✅ **Auto-documentation** - Generate `.env.example` from code
- ✅ **Secret detection** - Warn before committing secrets
- ✅ **Great error messages** - Know exactly what's wrong and how to fix it

---

## 🚀 Quick Start

### Installation

```bash
pip install envsync
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

# Now use them safely
print(f"Connecting to {DATABASE_URL}")
```

### Create `.env` file

```bash
# .env
API_KEY=sk-1234567890abcdef
DATABASE_URL=postgresql://localhost/mydb
ADMIN_EMAIL=admin@example.com
REDIS_URL=redis://localhost:6379
DEBUG=true
MAX_RETRIES=5
```

### Run your app

```bash
$ python app.py

# If env vars missing:
❌ EnvSync Validation Failed!

Missing required environment variables:
  - API_KEY
  - DATABASE_URL

To fix, add to .env:
  API_KEY=your-api-key-here
  DATABASE_URL=postgresql://user:pass@localhost/dbname

Or run: envsync generate
```

---

## 🎨 Core Features

### 1. Import-Time Validation

**The killer feature** - Your app won't start with bad config.

```python
from envsync import env

# This line MUST succeed or ImportError is raised
API_KEY = env.require("API_KEY")

# No more runtime surprises!
```

**Traditional approach (runtime failure):**
```python
import os
API_KEY = os.getenv("API_KEY")  # None - no error yet

# Later, deep in your code...
def call_api():
    headers = {"Authorization": f"Bearer {API_KEY}"}  # 💥 Crash!
```

**EnvSync approach (import-time failure):**
```python
from envsync import env
API_KEY = env.require("API_KEY")  # 💥 ImportError immediately if missing!

# Never reaches here with bad config
def call_api():
    headers = {"Authorization": f"Bearer {API_KEY}"}  # Always works!
```

### 2. Type Coercion & Validation

Automatic type conversion with validation.

```python
from envsync import env

# Strings (default)
API_KEY: str = env.require("API_KEY")

# Integers with range validation
PORT: int = env.require("PORT", type=int, range=(1, 65535))
MAX_CONNECTIONS: int = env.optional("MAX_CONNECTIONS", default=100, type=int, min=1)

# Booleans (handles "true", "True", "1", "yes", etc.)
DEBUG: bool = env.optional("DEBUG", default=False, type=bool)
ENABLE_CACHE: bool = env.require("ENABLE_CACHE", type=bool)

# Floats
TIMEOUT: float = env.optional("TIMEOUT", default=30.0, type=float)

# Lists (comma-separated)
ALLOWED_HOSTS: list[str] = env.require("ALLOWED_HOSTS", type=list)
# .env: ALLOWED_HOSTS=localhost,example.com,api.example.com

# Dictionaries (JSON)
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={}, type=dict)
# .env: FEATURE_FLAGS={"new_ui": true, "beta_features": false}

# Enums/Choices
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
# Valid: admin@example.com
# Invalid: not-an-email

# URL validation
API_BASE_URL: str = env.require("API_BASE_URL", format="url")
# Valid: https://api.example.com
# Invalid: not a url

# Database URL validation
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
# Valid: postgresql://user:pass@localhost:5432/dbname
# Invalid: mysql://... (wrong protocol)

# UUID validation
SERVICE_ID: str = env.require("SERVICE_ID", format="uuid")
# Valid: 550e8400-e29b-41d4-a716-446655440000

# IP address
SERVER_IP: str = env.require("SERVER_IP", format="ipv4")
# Valid: 192.168.1.1

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

### 5. Automatic `.env.example` Generation

EnvSync scans your code and generates `.env.example` automatically.

```python
# app.py
from envsync import env

API_KEY: str = env.require("API_KEY", description="OpenAI API key")
DATABASE_URL: str = env.require("DATABASE_URL", description="PostgreSQL connection string")
DEBUG: bool = env.optional("DEBUG", default=False, description="Enable debug mode")
```

```bash
$ envsync generate

Created: .env.example

# .env.example (generated):
# OpenAI API key
API_KEY=

# PostgreSQL connection string
DATABASE_URL=

# Enable debug mode (default: False)
DEBUG=false
```

**Share with team:**
```bash
git add .env.example
git commit -m "Add environment variable documentation"

# New team member:
cp .env.example .env
# Fill in values, start working immediately!
```

### 6. Team Synchronization

Detect when your `.env` is out of sync with the team.

```bash
$ envsync check

Checking .env against .env.example...

✅ API_KEY (present)
✅ DATABASE_URL (present)
❌ NEW_FEATURE_FLAG (missing in your .env)
⚠️  DEPRECATED_VAR (in your .env but not in .env.example)

Missing variables:
  NEW_FEATURE_FLAG=true

Extra variables (safe to remove):
  DEPRECATED_VAR

Run: envsync sync
```

```bash
$ envsync sync

Syncing .env with .env.example...

Added to .env:
  + NEW_FEATURE_FLAG=true

Removed from .env:
  - DEPRECATED_VAR

✅ Your .env is now up to date!
```

### 7. Secret Detection

Prevent accidentally committing secrets.

```python
from envsync import env

# Mark as secret
AWS_SECRET_KEY: str = env.require("AWS_SECRET_KEY", secret=True)
STRIPE_SECRET: str = env.require("STRIPE_SECRET", secret=True)
```

```bash
$ envsync scan

Scanning for secrets in git history...

⚠️  Warning: Potential secrets detected!

File: config.py (committed 2024-01-15)
  Line 12: AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           This looks like an AWS access key!

File: .env (in staging area)
  Line 3: STRIPE_SECRET=sk_test_1234567890
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          This looks like a Stripe secret key!

❌ Aborting commit. Remove secrets before committing.

To ignore: git commit --no-verify
```

### 8. Multi-Environment Support

Load different env files for different environments.

```python
from envsync import env

# Load base .env
env.load(".env")

# Override with environment-specific settings
env.load(".env.local", override=True)  # Local development
env.load(".env.test", override=True)   # Testing
env.load(".env.production", override=True)  # Production

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
.env.production       # Production (gitignored, managed by deployment)
```

### 9. Helpful Error Messages

EnvSync gives you actionable error messages.

```bash
$ python app.py

❌ EnvSync Validation Failed!

Missing required environment variable: API_KEY

Expected:
  Type: string
  Description: OpenAI API key
  Format: Must match pattern ^sk-[a-zA-Z0-9]{32}$

To fix:
  1. Add to .env:
     API_KEY=sk-your-api-key-here

  2. Or set in environment:
     export API_KEY=sk-your-api-key-here

  3. Or generate .env.example:
     envsync generate

Did you mean?
  - API_SECRET (similar name in .env.example)
  - API_TOKEN (similar name in .env.example)

For help: envsync --help
```

### 10. CI/CD Integration

Validate environment in CI pipelines.

```yaml
# .github/workflows/validate-env.yml
name: Validate Environment

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install EnvSync
        run: pip install envsync

      - name: Validate .env.example is up to date
        run: |
          envsync generate --check
          # Fails if .env.example is out of sync with code

      - name: Check for secrets in git
        run: envsync scan --strict
```

---

## 📚 CLI Reference

### `envsync generate`

Generate `.env.example` from your code.

```bash
$ envsync generate

Options:
  --output FILE        Output file (default: .env.example)
  --check              Check if .env.example is up to date (CI mode)
  --force              Overwrite existing .env.example
  --format json|yaml   Output format (default: dotenv)

Examples:
  envsync generate                    # Create .env.example
  envsync generate --check            # Validate in CI
  envsync generate --output .env.dev  # Custom output
```

### `envsync check`

Check your `.env` for missing/extra variables.

```bash
$ envsync check

Options:
  --env-file FILE      .env file to check (default: .env)
  --example FILE       .env.example to compare against
  --strict             Fail if any differences found
  --json               Output as JSON

Examples:
  envsync check                       # Check .env vs .env.example
  envsync check --strict              # Exit 1 if differences
  envsync check --env-file .env.prod  # Check production env
```

### `envsync sync`

Synchronize your `.env` with `.env.example`.

```bash
$ envsync sync

Options:
  --env-file FILE      .env file to sync (default: .env)
  --example FILE       .env.example to sync from
  --dry-run            Show what would change without applying
  --interactive        Ask before each change

Examples:
  envsync sync                        # Sync .env
  envsync sync --dry-run              # Preview changes
  envsync sync --interactive          # Confirm each change
```

### `envsync scan`

Scan for secrets in git history.

```bash
$ envsync scan

Options:
  --strict             Fail if secrets found
  --depth N            Scan N commits deep (default: 100)
  --fix                Offer to remove secrets from git history

Examples:
  envsync scan                        # Scan for secrets
  envsync scan --strict               # Fail on secrets (CI)
  envsync scan --fix                  # Remove secrets from git
```

### `envsync validate`

Validate environment variables without running app.

```bash
$ envsync validate

Options:
  --env-file FILE      .env file to validate (default: .env)
  --app MODULE         Python module to validate

Examples:
  envsync validate                    # Validate current .env
  envsync validate --app myapp.config # Validate specific module
```

### `envsync docs`

Generate documentation for environment variables.

```bash
$ envsync docs

Options:
  --format markdown|html|json
  --output FILE

Examples:
  envsync docs > ENV_VARS.md          # Markdown table
  envsync docs --format html > docs/env.html
```

**Example output:**

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| API_KEY | string | Yes | - | OpenAI API key |
| DATABASE_URL | string | Yes | - | PostgreSQL connection |
| DEBUG | boolean | No | false | Enable debug mode |
| MAX_RETRIES | integer | No | 3 | Maximum retry attempts |

---

## 🎓 Advanced Usage

### Configuration File

Create `envsync.toml` for project-wide settings.

```toml
# envsync.toml
[envsync]
# Env files to load (in order)
env_files = [".env", ".env.local"]

# Validation strictness
strict = true  # Fail on warnings

# Secret detection
detect_secrets = true
secret_patterns = [
    "sk-[a-zA-Z0-9]{32}",  # OpenAI
    "AKIA[0-9A-Z]{16}",    # AWS
    "ghp_[a-zA-Z0-9]{36}"  # GitHub PAT
]

# Team sync
auto_sync = true  # Sync on startup

# Error handling
on_error = "raise"  # or "warn", "ignore"

[envsync.defaults]
# Default values for all environments
LOG_LEVEL = "INFO"
TIMEOUT = 30

[envsync.development]
# Development-specific defaults
DEBUG = true
LOG_LEVEL = "DEBUG"

[envsync.production]
# Production-specific defaults
DEBUG = false
LOG_LEVEL = "WARNING"
```

### Programmatic Usage

```python
from envsync import EnvSync

# Create custom instance
env = EnvSync(
    env_file=".env.custom",
    auto_load=True,
    strict=True,
    detect_secrets=True
)

# Load multiple files
env.load_files([".env", ".env.local", ".env.production"])

# Get variable with validation
api_key = env.get(
    "API_KEY",
    required=True,
    type=str,
    pattern=r"^sk-[a-zA-Z0-9]{32}$"
)

# Check if variable exists
if env.has("FEATURE_FLAG"):
    feature_enabled = env.get("FEATURE_FLAG", type=bool)

# Get all variables
all_vars = env.all()  # Dict of all env vars

# Validate all
try:
    env.validate()
    print("✅ All environment variables valid")
except EnvSyncError as e:
    print(f"❌ Validation failed: {e}")

# Generate .env.example
env.generate_example(output=".env.example")
```

### Framework Integrations

#### FastAPI

```python
from fastapi import FastAPI
from envsync import env

# Load env vars at module level
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

### Testing

```python
# tests/test_config.py
import pytest
from envsync import env, EnvSyncError

def test_required_env_vars_present(monkeypatch):
    """Test that all required env vars are set."""
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    # Should not raise
    from myapp import config

def test_missing_env_var_raises_error(monkeypatch):
    """Test that missing env vars raise ImportError."""
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(ImportError, match="Missing required.*API_KEY"):
        from myapp import config

def test_invalid_type_raises_error(monkeypatch):
    """Test that invalid types raise errors."""
    monkeypatch.setenv("PORT", "not-a-number")

    with pytest.raises(EnvSyncError, match="Invalid type.*PORT"):
        PORT = env.require("PORT", type=int)

# Test with temporary .env file
def test_with_temp_env(tmp_path):
    """Test with temporary .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=test-key\nDEBUG=true\n")

    temp_env = EnvSync(env_file=str(env_file))
    assert temp_env.get("API_KEY") == "test-key"
    assert temp_env.get("DEBUG", type=bool) is True
```

---

## 🔧 Configuration Options

### Environment Variable Loading

```python
from envsync import env

# Basic loading
env.load(".env")  # Load .env file

# Multiple files (last wins)
env.load_files([".env", ".env.local"])

# Override existing values
env.load(".env.production", override=True)

# Don't override existing OS environment variables
env.load(".env", override=False)  # Default

# Interpolation
env.load(".env", interpolate=True)
# Supports: DATABASE_URL=postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}
```

### Validation Options

```python
# Strict mode (warnings become errors)
env = EnvSync(strict=True)

# Custom error handling
env = EnvSync(
    on_error="warn"  # "raise", "warn", "ignore"
)

# Validate on load
env = EnvSync(validate_on_load=True)

# Require .env file
env = EnvSync(require_env_file=True)
```

### Secret Detection

```python
env = EnvSync(
    detect_secrets=True,
    secret_patterns=[
        r"sk-[a-zA-Z0-9]{32}",         # OpenAI
        r"AKIA[0-9A-Z]{16}",           # AWS Access Key
        r"ghp_[a-zA-Z0-9]{36}",        # GitHub PAT
        r"xoxb-[0-9]{11}-[0-9]{11}",   # Slack Bot Token
    ],
    on_secret_found="warn"  # "raise", "warn", "ignore"
)
```

---

## 📊 Comparison with Alternatives

| Feature | EnvSync | python-decouple | environs | pydantic-settings | python-dotenv |
|---------|---------|-----------------|----------|-------------------|---------------|
| Import-time validation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Type coercion | ✅ | ⚠️ Basic | ✅ | ✅ | ❌ |
| Format validators | ✅ | ❌ | ⚠️ Limited | ✅ | ❌ |
| .env.example generation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Team sync (drift detection) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Secret detection | ✅ | ❌ | ❌ | ❌ | ❌ |
| CLI tools | ✅ | ❌ | ❌ | ❌ | ❌ |
| Helpful error messages | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| Multi-environment | ✅ | ⚠️ | ✅ | ✅ | ⚠️ |
| Zero dependencies | ❌ | ✅ | ❌ | ❌ | ✅ |

**Why EnvSync?**

- **python-dotenv**: Just loads `.env` files, no validation
- **python-decouple**: Basic type casting, but runtime errors only
- **environs**: Good validation, but verbose API and no team sync
- **pydantic-settings**: Requires Pydantic models (overkill for simple configs)

**EnvSync combines the best features** and adds unique capabilities (import-time validation, team sync, secret detection).

---

## 🛠️ Development Roadmap

### Phase 1: Core MVP (Weeks 1-6) ✅
- [x] Environment variable loading
- [x] Import-time validation
- [x] Type coercion (str, int, bool, float, list, dict)
- [x] Format validators (email, URL, UUID, IP)
- [x] Custom validators
- [x] Required vs optional variables
- [x] Helpful error messages

### Phase 2: Team Features (Weeks 7-10) ✅
- [x] `.env.example` generation
- [x] Drift detection (`check` command)
- [x] Team sync (`sync` command)
- [x] CLI implementation
- [x] Multi-environment support
- [x] Documentation generation

### Phase 3: Security & Polish (Weeks 11-12) 🚧
- [ ] Secret detection
- [ ] Git integration (pre-commit hook)
- [ ] Performance optimization
- [ ] Comprehensive test suite
- [ ] Documentation website

### Phase 4: Integrations (Months 4-6) 📋
- [ ] VS Code extension (env var autocomplete)
- [ ] PyCharm plugin
- [ ] GitHub Actions integration
- [ ] Docker integration
- [ ] Cloud secrets support (AWS, GCP, Azure)
- [ ] 1Password/Vault integration

### Phase 5: Advanced Features (Future) 💡
- [ ] Web UI for team env management
- [ ] Encrypted .env files
- [ ] Environment variable versioning
- [ ] Audit logging
- [ ] RBAC for secret access
- [ ] Compliance reports (SOC2, HIPAA)

---

## 🤝 Contributing

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

# Run specific test
pytest tests/test_validation.py::test_import_time_validation
```

### Project Structure

```
envsync/
├── envsync/
│   ├── __init__.py          # Public API
│   ├── core.py              # Core EnvSync class
│   ├── validation.py        # Validators
│   ├── cli.py               # CLI commands
│   ├── scanner.py           # Secret scanning
│   ├── sync.py              # Team sync features
│   └── exceptions.py        # Custom exceptions
├── tests/
│   ├── test_core.py
│   ├── test_validation.py
│   ├── test_cli.py
│   └── test_sync.py
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   └── api-reference.md
├── examples/
│   ├── fastapi_app/
│   ├── django_app/
│   └── flask_app/
├── pyproject.toml
├── README.md
└── LICENSE
```

### Areas for Contribution

- 🐛 **Bug fixes**: Check [issues](https://github.com/Daily-Nerd/EnvSync/issues)
- 🎨 **New validators**: Add format validators for common patterns
- 🔌 **Framework integrations**: Django, FastAPI, Flask plugins
- 📚 **Documentation**: Examples, tutorials, guides
- 🧪 **Tests**: Improve test coverage
- 🌍 **Internationalization**: Error messages in other languages

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Inspired by:
- [python-dotenv](https://github.com/theskumar/python-dotenv) - .env file loading
- [python-decouple](https://github.com/henriquebastos/python-decouple) - Config management
- [environs](https://github.com/sloria/environs) - Environment variable parsing
- [pydantic-settings](https://github.com/pydantic/pydantic-settings) - Settings management
- [direnv](https://direnv.net/) - Environment management inspiration

Built with:
- [click](https://click.palletsprojects.com/) - CLI framework
- [rich](https://rich.readthedocs.io/) - Terminal formatting
- [python-dotenv](https://github.com/theskumar/python-dotenv) - .env parsing

---

## 📞 Support & Community

- **Documentation**: [envsync.dev](https://envsync.dev)
- **GitHub**: [github.com/Daily-Nerd/EnvSync](https://github.com/Daily-Nerd/EnvSync)
- **Issues**: [github.com/Daily-Nerd/EnvSync/issues](https://github.com/Daily-Nerd/EnvSync/issues)
- **Discord**: [discord.gg/envsync](https://discord.gg/envsync)
- **Twitter**: [@envsync](https://twitter.com/envsync)

---

## ⭐ Star History

If EnvSync helps you, please give it a star on GitHub!

[![Star History](https://api.star-history.com/svg?repos=yourusername/envsync&type=Date)](https://star-history.com/#yourusername/envsync&Date)

---

**EnvSync** - Environment variables that just work. 🎯

*Stop debugging production crashes. Start shipping with confidence.*
