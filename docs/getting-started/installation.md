[Home](../README.md) / [Getting Started](README.md) / Installation

# Installation

Get TripWire installed and ready to use in minutes.

---

## Requirements

- **Python 3.11+** required
- Compatible with Linux, macOS, and Windows
- Git recommended (for audit features)

---

## Install from PyPI

```bash
pip install tripwire-py
```

> **Important Note:** The package name on PyPI is `tripwire-py` (with hyphen), but you import and use it as `tripwire` (without hyphen):
>
> ```python
> from tripwire import env  # Import name is 'tripwire'
> ```

This naming is intentional to avoid conflicts with existing packages on PyPI.

---

## Verify Installation

Check that TripWire is installed correctly:

```bash
tripwire --version
```

You should see output like:

```
TripWire version 0.4.1
```

---

## Install Development Dependencies

If you're contributing to TripWire or want to run tests:

```bash
# Clone the repository
git clone https://github.com/Daily-Nerd/TripWire.git
cd TripWire

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

---

## Alternative Installation Methods

### Using uv (Recommended for Speed)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer:

```bash
uv pip install tripwire-py
```

### Using pipx (For CLI Tools)

If you only want the CLI commands without importing in Python:

```bash
pipx install tripwire-py
```

### Using Poetry

```bash
poetry add tripwire-py
```

### Using requirements.txt

Add to your `requirements.txt`:

```
tripwire-py>=0.4.1
```

Then install:

```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### "command not found: tripwire"

**Problem:** The CLI is not in your PATH.

**Solution:**
```bash
# Check if installed correctly
pip show tripwire-py

# Reinstall
pip install --force-reinstall tripwire-py
```

### "ImportError: No module named tripwire"

**Problem:** Package installed with wrong name or in wrong environment.

**Solution:**
```bash
# Ensure correct package name
pip uninstall tripwire tripwire-py
pip install tripwire-py

# Verify in Python
python -c "from tripwire import env; print('Success!')"
```

### Version Mismatch

**Problem:** Old version installed.

**Solution:**
```bash
# Upgrade to latest
pip install --upgrade tripwire-py
```

---

## Next Steps

Now that TripWire is installed:

1. **[Quick Start](quick-start.md)** - Get started in 5 minutes
2. **[Your First Project](your-first-project.md)** - Build your first project with TripWire
3. **[CLI Reference](../guides/cli-reference.md)** - Explore all CLI commands

---

## System Requirements Details

### Python Version

TripWire requires Python 3.11 or higher to take advantage of:
- Modern type hints (`Self`, `TypeVar` improvements)
- Pattern matching (`match` statements)
- Exception groups
- Performance improvements

### Dependencies

TripWire has minimal dependencies:
- `python-dotenv` - .env file parsing
- `click` - CLI framework
- `rich` - Terminal formatting
- `tomli` / `tomli-w` - TOML support (Python < 3.11)

All dependencies are automatically installed.

---

**[Back to Documentation Home](../README.md)**
