[Home](../README.md) / [Advanced](README.md) / Troubleshooting

# Troubleshooting Guide

Common issues and solutions when using TripWire.

---

## Installation Issues

### "command not found: tripwire"

**Problem:** CLI not in PATH after installation.

**Solutions:**

1. **Verify installation:**
   ```bash
   pip show tripwire-py
   ```

2. **Reinstall:**
   ```bash
   pip install --force-reinstall tripwire-py
   ```

3. **Check PATH:**
   ```bash
   which tripwire
   # Should show: /path/to/python/bin/tripwire
   ```

4. **Use python -m:**
   ```bash
   python -m tripwire.cli --version
   ```

---

### "ImportError: No module named tripwire"

**Problem:** Package not installed or wrong environment.

**Solutions:**

1. **Verify correct package name:**
   ```bash
   pip uninstall tripwire tripwire-py
   pip install tripwire-py
   ```

2. **Check virtual environment:**
   ```bash
   which python
   # Ensure you're in correct venv
   ```

3. **Test import:**
   ```bash
   python -c "from tripwire import env; print('Success!')"
   ```

---

## Validation Errors

### "EnvironmentError: VARIABLE_NAME not set"

**Problem:** Required environment variable is missing.

**Solutions:**

1. **Add to .env:**
   ```bash
   echo "VARIABLE_NAME=value" >> .env
   ```

2. **Set as system variable:**
   ```bash
   export VARIABLE_NAME=value
   ```

3. **Make it optional:**
   ```python
   # Change from require to optional
   VALUE: str = env.optional("VARIABLE_NAME", default="default_value")
   ```

---

### "Type coercion failed: cannot convert 'abc' to int"

**Problem:** Value in .env cannot be converted to expected type.

**Solutions:**

1. **Check .env value:**
   ```bash
   # .env
   PORT=abc  # ❌ Invalid

   # Fix:
   PORT=8000  # ✅ Valid integer
   ```

2. **Verify type annotation:**
   ```python
   # If PORT should be string, don't use int annotation
   PORT: str = env.require("PORT")  # ✅ String
   ```

---

### "Validation failed: Pattern mismatch"

**Problem:** Value doesn't match regex pattern.

**Solutions:**

1. **Check pattern:**
   ```python
   # Ensure pattern is correct
   API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")
   ```

2. **Check .env value:**
   ```bash
   # .env
   API_KEY=invalid-key  # ❌ Doesn't match pattern

   # Fix:
   API_KEY=sk-1234567890abcdef1234567890abcd  # ✅ Matches
   ```

3. **Test pattern separately:**
   ```python
   import re
   pattern = r"^sk-[a-zA-Z0-9]{32}$"
   value = "sk-test123"
   print(bool(re.match(pattern, value)))
   ```

---

## Type Inference Issues

### Type Not Inferred (Falls Back to str)

**Problem:** Type annotation not detected.

**Solutions:**

1. **Use typed methods:**
   ```python
   # ❌ No annotation in dict
   config = {
       "port": env.require("PORT")  # Falls back to str
   }

   # ✅ Use typed method
   config = {
       "port": env.require_int("PORT")
   }
   ```

2. **Add explicit type:**
   ```python
   # ✅ Explicit type parameter
   PORT = env.require("PORT", type=int)
   ```

---

### "Optional[T] not handled correctly"

**Problem:** Optional type not extracted properly.

**Solution:**

```python
from typing import Optional

# ✅ TripWire extracts 'int' from Optional[int]
MAX_RETRIES: Optional[int] = env.optional("MAX_RETRIES", default=None)

# If value is set: coerced to int
# If not set: None
```

---

## File Loading Issues

### ".env file not found"

**Problem:** TripWire can't locate .env file.

**Solutions:**

1. **Verify file exists:**
   ```bash
   ls -la .env
   ```

2. **Check working directory:**
   ```python
   import os
   print(os.getcwd())
   # Ensure .env is in this directory
   ```

3. **Specify absolute path:**
   ```python
   env.load("/absolute/path/to/.env")
   ```

4. **Use silent mode for optional files:**
   ```python
   env.load(".env.local", override=True, silent=True)
   ```

---

### "Values not loaded from .env"

**Problem:** Values in .env ignored.

**Solutions:**

1. **Ensure env.load() called before require():**
   ```python
   # ✅ Correct order
   from tripwire import env
   env.load(".env")  # Load first
   PORT: int = env.require("PORT")  # Then require

   # ❌ Wrong order
   PORT: int = env.require("PORT")  # Fails before load!
   env.load(".env")
   ```

2. **Use override=True for multi-file loading:**
   ```python
   env.load(".env")
   env.load(".env.local", override=True)  # Override base values
   ```

---

## Git Audit Issues

### "No git repository found"

**Problem:** Not in a git repository.

**Solution:**

```bash
# Initialize git if needed
git init
git add .
git commit -m "Initial commit"

# Then run audit
tripwire audit --all
```

---

### "Secret not found in git history"

**Problem:** Audit doesn't find known secret.

**Solutions:**

1. **Provide exact value:**
   ```bash
   tripwire audit API_KEY --value "actual-secret-value"
   ```

2. **Increase commit depth:**
   ```bash
   tripwire audit API_KEY --max-commits 5000
   ```

3. **Check secret is in .env:**
   ```bash
   grep "API_KEY" .env
   ```

---

### "git log command failed"

**Problem:** Git command errors.

**Solutions:**

1. **Ensure git is installed:**
   ```bash
   git --version
   ```

2. **Check git configuration:**
   ```bash
   git config user.name
   git config user.email
   ```

3. **Run git fetch:**
   ```bash
   git fetch --all
   ```

---

## Schema Validation Issues

### "Schema file not found"

**Problem:** `.tripwire.toml` missing.

**Solutions:**

1. **Create schema:**
   ```bash
   tripwire schema init
   ```

2. **Specify custom location:**
   ```bash
   tripwire schema validate --schema-file custom.toml
   ```

---

### "TOML syntax error"

**Problem:** Invalid TOML syntax.

**Solutions:**

1. **Validate syntax:**
   ```bash
   tripwire schema check
   ```

2. **Common TOML errors:**
   ```toml
   # ❌ Single quotes don't work for strings
   name = 'my-app'

   # ✅ Use double quotes
   name = "my-app"

   # ❌ Missing quotes around string values
   type = string

   # ✅ Quote string values
   type = "string"
   ```

3. **Use online TOML validator:**
   https://www.toml-lint.com/

---

## Performance Issues

### Slow Import Time

**Problem:** App takes long to start.

**Solutions:**

1. **Reduce file scans:**
   ```python
   # ❌ Scans all files
   tripwire generate

   # ✅ Cache results
   # Run generate once, commit .env.example
   ```

2. **Use typed methods instead of inference:**
   ```python
   # ❌ Slower (frame inspection)
   for i in range(1000):
       value: int = env.require(f"VAR_{i}")

   # ✅ Faster (no frame inspection)
   for i in range(1000):
       value = env.require_int(f"VAR_{i}")
   ```

---

### Git Audit Takes Too Long

**Problem:** Audit scans entire history.

**Solutions:**

1. **Reduce commit depth:**
   ```bash
   tripwire audit API_KEY --max-commits 100
   ```

2. **Configure default in pyproject.toml:**
   ```toml
   [tool.tripwire]
   max_commits = 500
   ```

---

## CI/CD Issues

### "generate --check fails in CI"

**Problem:** .env.example out of sync.

**Solutions:**

1. **Regenerate locally:**
   ```bash
   tripwire generate --force
   git add .env.example
   git commit -m "Update .env.example"
   ```

2. **Add to pre-commit hook:**
   ```yaml
   # .pre-commit-config.yaml
   - id: tripwire-generate
     entry: tripwire generate --check
   ```

---

### "scan --strict fails in CI"

**Problem:** Secrets detected in .env.

**Solutions:**

1. **Ensure .env is gitignored:**
   ```bash
   echo ".env" >> .gitignore
   git rm --cached .env
   ```

2. **Use environment variables in CI:**
   ```yaml
   # GitHub Actions
   env:
     DATABASE_URL: ${{ secrets.DATABASE_URL }}
     API_KEY: ${{ secrets.API_KEY }}
   ```

---

## Debug Mode

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from tripwire import env

# Now see detailed logs
DATABASE_URL: str = env.require("DATABASE_URL")
```

**Output:**
```
DEBUG: Loading .env file
DEBUG: Inferred type 'str' for DATABASE_URL
DEBUG: Validating DATABASE_URL with format=postgresql
DEBUG: Validation passed for DATABASE_URL
```

---

## Getting Help

### Check Documentation

- [API Reference](../reference/api.md)
- [Validators](../reference/validators.md)
- [Type System](type-system.md)

### Search Issues

https://github.com/Daily-Nerd/TripWire/issues

### Report a Bug

https://github.com/Daily-Nerd/TripWire/issues/new

**Include:**
- TripWire version: `tripwire --version`
- Python version: `python --version`
- OS: `uname -a` (Linux/Mac) or `systeminfo` (Windows)
- Minimal reproducible example
- Full error message

---

**[Back to Advanced](README.md)**
