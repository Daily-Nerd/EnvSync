[Home](../README.md) / [Getting Started](README.md) / Quick Start

# Quick Start

Get up and running with TripWire in 5 minutes.

---

## 1. Install TripWire

```bash
pip install tripwire-py
```

See [Installation Guide](installation.md) for other installation methods.

---

## 2. Initialize Your Project

Navigate to your project directory and run:

```bash
tripwire init
```

You'll see:

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

This creates:
- `.env` - Your local environment variables (gitignored)
- `.env.example` - Template for team members (committed)
- Updates `.gitignore` to exclude `.env`

---

## 3. Define Environment Variables

Edit your `.env` file:

```bash
# .env
DATABASE_URL=postgresql://localhost:5432/myapp
API_KEY=sk-1234567890abcdef1234567890abcdef
DEBUG=true
PORT=8000
```

---

## 4. Use in Your Code

Create `config.py` or add to your main application file:

```python
# config.py
from tripwire import env

# Required variables (fail if missing)
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
API_KEY: str = env.require("API_KEY", secret=True)

# Optional with defaults (type inferred from annotation)
DEBUG: bool = env.optional("DEBUG", default=False)
PORT: int = env.optional("PORT", default=8000, min_val=1, max_val=65535)

# Now use them safely - guaranteed to be valid!
print(f"Connecting to {DATABASE_URL}")
print(f"Debug mode: {DEBUG}")
print(f"Running on port {PORT}")
```

---

## 5. Run Your Application

```bash
python config.py
```

If any required variable is missing or invalid, you'll get a clear error message **before your app starts**:

```
EnvironmentError: DATABASE_URL is required but not set

Suggestions:
  1. Add DATABASE_URL to your .env file
  2. Set it as a system environment variable: export DATABASE_URL=<value>
  3. Check .env.example for expected format
```

---

## What Just Happened?

TripWire validated your environment variables **at import time**:

1. ✅ **Checked existence** - All required variables are present
2. ✅ **Validated types** - Converted strings to correct types (int, bool, etc.)
3. ✅ **Validated formats** - DATABASE_URL matches PostgreSQL format
4. ✅ **Applied constraints** - PORT is within valid range (1-65535)

If any validation fails, your application **won't start**. No more runtime crashes from bad config!

---

## Core Concepts

### Required vs Optional

```python
# Required - fails if not set
API_KEY = env.require("API_KEY")

# Optional - uses default if not set
DEBUG = env.optional("DEBUG", default=False, type=bool)
```

### Type Inference (New in v0.4.0)

TripWire automatically infers types from annotations:

```python
# Type inferred from annotation (int)
PORT: int = env.require("PORT", min_val=1, max_val=65535)

# No need to specify type= twice!
# Old way (still works): PORT: int = env.require("PORT", type=int, min_val=1)
```

### Format Validation

```python
# Email validation
ADMIN_EMAIL: str = env.require("ADMIN_EMAIL", format="email")

# URL validation
API_URL: str = env.require("API_URL", format="url")

# Database URL
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
```

---

## Common Use Cases

### Web Application

```python
from tripwire import env

# Database
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")

# Redis cache
REDIS_URL: str = env.optional("REDIS_URL", default="redis://localhost:6379")

# Security
SECRET_KEY: str = env.require("SECRET_KEY", secret=True, min_length=32)

# API keys
STRIPE_API_KEY: str = env.require("STRIPE_API_KEY", secret=True)
```

### CLI Application

```python
from tripwire import env

# Configuration
LOG_LEVEL: str = env.optional(
    "LOG_LEVEL",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"]
)

OUTPUT_DIR: str = env.optional("OUTPUT_DIR", default="./output")
```

### Data Processing

```python
from tripwire import env

# API credentials
API_ENDPOINT: str = env.require("API_ENDPOINT", format="url")
API_TOKEN: str = env.require("API_TOKEN", secret=True)

# Processing settings
BATCH_SIZE: int = env.optional("BATCH_SIZE", default=100, min_val=1)
MAX_WORKERS: int = env.optional("MAX_WORKERS", default=4, min_val=1, max_val=32)
```

---

## Next Steps

Great! You now have TripWire set up. Here's what to explore next:

### Learn More
- **[Your First Project](your-first-project.md)** - Detailed walkthrough of building with TripWire
- **[CLI Reference](../guides/cli-reference.md)** - Master the CLI tools
- **[Type System](../advanced/type-system.md)** - Deep dive into type inference

### Essential Features
- **[Generate .env.example](../guides/cli-reference.md#generate)** - Auto-generate from code
- **[Check for Drift](../guides/cli-reference.md#check)** - Keep team in sync
- **[Scan for Secrets](../guides/secret-management.md)** - Detect leaked secrets

### Advanced Topics
- **[Configuration as Code](../guides/configuration-as-code.md)** - Schema-based validation
- **[Framework Integration](../guides/framework-integration.md)** - Use with FastAPI, Django, Flask
- **[Git Audit](../advanced/git-audit.md)** - Find secret leaks in git history

---

## Troubleshooting

**App won't start?**
- Check the error message - it tells you exactly what's missing
- Verify `.env` file exists and is in the right location
- See [Troubleshooting Guide](../advanced/troubleshooting.md)

**Need help?**
- [GitHub Issues](https://github.com/Daily-Nerd/TripWire/issues)
- [Documentation Home](../README.md)

---

**[Back to Getting Started](README.md)**
