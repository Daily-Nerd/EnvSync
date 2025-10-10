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

[Quick Start](docs/getting-started/quick-start.md) • [Documentation](docs/README.md) • [CLI Reference](docs/guides/cli-reference.md) • [API Docs](docs/reference/api.md)

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
- Environment variables fail at runtime, not at startup
- No validation (wrong types, missing values, invalid formats)
- .env files drift across team members
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
PORT: int = env.require("PORT", min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False)

# Your app won't even start with bad config!
```

**Key Benefits:**
- ✅ **Import-time validation** - Fail fast, not in production
- ✅ **Type safety** - Automatic type coercion with validation
- ✅ **Team sync** - Keep .env files consistent across team
- ✅ **Auto-documentation** - Generate .env.example from code
- ✅ **Secret detection** - 45+ platform-specific patterns (AWS, GitHub, Stripe, etc.)
- ✅ **Git history auditing** - Find when secrets were leaked and generate remediation steps
- ✅ **Great error messages** - Know exactly what's wrong and how to fix it

---

## Quick Start

### Installation

```bash
pip install tripwire-py
```

> **Note:** The package name on PyPI is `tripwire-py`, but you import it as `tripwire`:
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
# config.py
from tripwire import env

# Required variables (fail if missing)
API_KEY: str = env.require("API_KEY")
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

# Optional with defaults
DEBUG: bool = env.optional("DEBUG", default=False)
MAX_RETRIES: int = env.optional("MAX_RETRIES", default=3)

# Validated formats
EMAIL: str = env.require("ADMIN_EMAIL", format="email")
REDIS_URL: str = env.require("REDIS_URL", format="url")

# Now use them safely - guaranteed to be valid!
print(f"Connecting to {DATABASE_URL}")
```

[Learn more in the Quick Start Guide →](docs/getting-started/quick-start.md)

---

## Core Features

### 1. Import-Time Validation

Your app won't start with bad config.

```python
from tripwire import env

# This line MUST succeed or ImportError is raised
API_KEY = env.require("API_KEY")
# No more runtime surprises!
```

### 2. Type Inference & Validation

Automatic type detection from annotations (v0.4.0+) - no need to specify `type=` twice!

```python
from tripwire import env

# Type inferred from annotation
PORT: int = env.require("PORT", min_val=1, max_val=65535)
DEBUG: bool = env.optional("DEBUG", default=False)
TIMEOUT: float = env.optional("TIMEOUT", default=30.0)

# Lists and dicts
ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS")  # Handles CSV or JSON
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={})

# Choices/enums
ENVIRONMENT: str = env.require("ENVIRONMENT", choices=["dev", "staging", "prod"])
```

[Learn more about Type Inference →](docs/reference/type-inference.md)

### 3. Format Validators

Built-in validators for common formats.

```python
# Email, URL, database, IP, UUID validation
ADMIN_EMAIL: str = env.require("ADMIN_EMAIL", format="email")
API_URL: str = env.require("API_URL", format="url")
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
SERVER_IP: str = env.require("SERVER_IP", format="ipv4")

# Custom regex patterns
API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")
```

[See all validators →](docs/reference/validators.md)

### 4. Secret Detection & Git Audit

Detect secrets in .env and audit git history for leaks.

```bash
# Auto-detect and audit all secrets
$ tripwire audit --all

🔍 Auto-detecting secrets in .env file...
⚠️  Found 3 potential secret(s)

📊 Secret Leak Blast Radius
═══════════════════════════
🔍 Repository Secret Exposure
├─ 🔴 🚨 AWS_SECRET_ACCESS_KEY (47 occurrence(s))
│  ├─ Branches: origin/main, origin/develop
│  └─ Files: .env
├─ 🟡 ⚠️ STRIPE_SECRET_KEY (12 occurrence(s))
└─ 🟢 DATABASE_PASSWORD (0 occurrence(s))

📈 Summary: 2 leaked, 1 clean, 59 commits affected
```

**Detects 45+ secret types:** AWS, GitHub, Stripe, Azure, GCP, Slack, and more.

[Learn more about Secret Management →](docs/guides/secret-management.md) | [Git Audit Deep Dive →](docs/advanced/git-audit.md)

---

## Essential CLI Commands

```bash
# Initialize project
tripwire init

# Generate .env.example from code
tripwire generate

# Check for drift between .env and .env.example
tripwire check

# Sync .env with .env.example
tripwire sync

# Compare configurations (v0.4.0+)
tripwire diff .env .env.prod

# Scan for secrets
tripwire scan --strict

# Audit git history for secret leaks
tripwire audit --all

# Validate .env without running app
tripwire validate
```

[Complete CLI Reference →](docs/guides/cli-reference.md)

---

## Framework Integration

### FastAPI

```python
from fastapi import FastAPI
from tripwire import env

# Validate at import time
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
SECRET_KEY: str = env.require("SECRET_KEY", secret=True, min_length=32)
DEBUG: bool = env.optional("DEBUG", default=False)

app = FastAPI(debug=DEBUG)

@app.on_event("startup")
async def startup():
    print(f"Connecting to {DATABASE_URL[:20]}...")
```

### Django

```python
# settings.py
from tripwire import env

SECRET_KEY = env.require("DJANGO_SECRET_KEY", secret=True, min_length=50)
DEBUG = env.optional("DEBUG", default=False)
ALLOWED_HOSTS = env.optional("ALLOWED_HOSTS", default=["localhost"], type=list)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.require("DB_NAME"),
        'USER': env.require("DB_USER"),
        'PASSWORD': env.require("DB_PASSWORD", secret=True),
        'HOST': env.optional("DB_HOST", default="localhost"),
        'PORT': env.optional("DB_PORT", default=5432),
    }
}
```

### Flask

```python
from flask import Flask
from tripwire import env

# Validate before app creation
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
SECRET_KEY: str = env.require("SECRET_KEY", secret=True)
DEBUG: bool = env.optional("DEBUG", default=False)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = SECRET_KEY
```

[More framework examples →](docs/guides/framework-integration.md)

---

## Configuration as Code

Define environment variables declaratively using TOML schemas (v0.3.0+).

```toml
# .tripwire.toml
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

[environments.production]
strict_secrets = true
```

```bash
# Validate against schema
tripwire schema validate --environment production

# Generate .env.example from schema
tripwire schema generate-example

# Migrate legacy .env.example to schema (v0.4.1+)
tripwire migrate-to-schema
```

[Learn more about Configuration as Code →](docs/guides/configuration-as-code.md)

---

## CI/CD Integration

### GitHub Actions

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
      - run: tripwire generate --check
      - run: tripwire scan --strict
      - run: tripwire schema validate --strict
```

[More CI/CD examples →](docs/guides/ci-cd-integration.md)

---

## Comparison with Alternatives

| Feature | TripWire | python-decouple | environs | pydantic-settings | python-dotenv |
|---------|---------|-----------------|----------|-------------------|---------------|
| Import-time validation | ✅ | ❌ | ⚠️ | ⚠️ | ❌ |
| Type coercion | ✅ | ⚠️ Basic | ✅ | ✅ | ❌ |
| Format validators | ✅ | ❌ | ✅ | ✅ | ❌ |
| .env.example generation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Team sync (drift detection) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Secret detection (45+ patterns) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Git history auditing | ✅ | ❌ | ❌ | ❌ | ❌ |
| CLI tools | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| Multi-environment | ✅ | ✅ | ✅ | ✅ | ✅ |

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

**Choose python-dotenv When:**
- You need a minimal, zero-config .env loader
- You're building a simple script or small project
- Minimal dependencies are a priority

**Choose environs When:**
- You need comprehensive type validation powered by marshmallow
- You're already using marshmallow in your project

**Choose pydantic-settings When:**
- Your project already uses Pydantic for data validation
- You need settings to integrate seamlessly with FastAPI

**Choose python-decouple When:**
- You want strict separation of config from code with minimal overhead
- You need zero dependencies

### Acknowledgments

TripWire builds on the excellent work of the Python community, particularly:
- **python-dotenv** for reliable .env file parsing
- The validation patterns pioneered by **environs** and **pydantic**
- The config separation philosophy of **python-decouple**

---

## Development Roadmap

### Implemented Features ✅

- [x] Environment variable loading
- [x] Import-time validation
- [x] Type coercion (str, int, bool, float, list, dict)
- [x] **Type inference from annotations** (v0.4.0)
- [x] Format validators (email, url, uuid, ipv4, postgresql)
- [x] Custom validators
- [x] .env.example generation from code
- [x] Drift detection and team sync
- [x] **Configuration comparison** (diff command - v0.4.0)
- [x] Multi-environment support
- [x] **Unified config abstraction** (.env + TOML - v0.4.0)
- [x] Secret detection (45+ platform patterns)
- [x] **Git audit with timeline and remediation** (audit command)
- [x] **Configuration as Code** (TOML schemas - v0.3.0)
- [x] **Tool configuration** (`[tool.tripwire]` - v0.4.1)
- [x] **Schema migration** (migrate-to-schema - v0.4.1)

### Planned Features 📋

- [ ] VS Code extension (env var autocomplete)
- [ ] PyCharm plugin
- [ ] Cloud secrets support (AWS Secrets Manager, Vault)
- [ ] Encrypted .env files
- [ ] Web UI for team env management
- [ ] Environment variable versioning
- [ ] Compliance reports (SOC2, HIPAA)

---

## Documentation

Complete documentation is available at [docs/README.md](docs/README.md):

### Getting Started
- [Installation](docs/getting-started/installation.md)
- [Quick Start (5 minutes)](docs/getting-started/quick-start.md)
- [Your First Project](docs/getting-started/your-first-project.md)

### Guides
- [CLI Reference](docs/guides/cli-reference.md)
- [Configuration as Code](docs/guides/configuration-as-code.md)
- [Secret Management](docs/guides/secret-management.md)
- [Framework Integration](docs/guides/framework-integration.md)
- [Multi-Environment](docs/guides/multi-environment.md)
- [CI/CD Integration](docs/guides/ci-cd-integration.md)

### Reference
- [Python API](docs/reference/api.md)
- [Validators](docs/reference/validators.md)
- [Type Inference](docs/reference/type-inference.md)
- [Configuration](docs/reference/configuration.md)

### Advanced
- [Custom Validators](docs/advanced/custom-validators.md)
- [Git Audit Deep Dive](docs/advanced/git-audit.md)
- [Type System](docs/advanced/type-system.md)
- [Troubleshooting](docs/advanced/troubleshooting.md)

---

## Contributing

We welcome contributions! See our development workflow:

```bash
# Clone and setup
git clone https://github.com/Daily-Nerd/TripWire.git
cd tripwire
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Format code
black .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Support

- **GitHub**: [github.com/Daily-Nerd/TripWire](https://github.com/Daily-Nerd/TripWire)
- **Issues**: [github.com/Daily-Nerd/TripWire/issues](https://github.com/Daily-Nerd/TripWire/issues)
- **PyPI**: [pypi.org/project/tripwire-py](https://pypi.org/project/tripwire-py/)

---

**TripWire** - Environment variables that just work. 🎯

*Stop debugging production crashes. Start shipping with confidence.*
