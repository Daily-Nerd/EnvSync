# EnvSync Examples

Welcome to EnvSync examples! This directory contains practical examples to help you get started with environment variable management.

## Getting Started (Start Here! 👇)

### Step 1: Setup Your Environment

```bash
# Copy the example environment file
cp examples/.env.example examples/.env

# Edit .env and add at minimum your DATABASE_URL
# DATABASE_URL=postgresql://localhost:5432/mydb
```

### Step 2: Run Quickstart (Recommended First!)

The quickstart example uses only 3 variables and is perfect for learning the basics:

```bash
python examples/quickstart.py
```

**Too lazy to setup .env?** Try demo mode:

```bash
python examples/quickstart.py --demo
```

### Step 3: Explore Full Examples

Once comfortable with quickstart, explore all features:

```bash
# Make sure you've filled in ALL variables in .env first!
python examples/basic_usage.py
```

Or use demo mode:

```bash
python examples/basic_usage.py --demo
```

## Available Examples

### 1. **quickstart.py** - START HERE!

**What it demonstrates:**
- Required variables with `env.require()`
- Optional variables with `env.optional()`
- Fail-fast validation at import time
- Type coercion (bool, int)
- Minimal setup (only 3 variables)

**Variables needed:**
- `DATABASE_URL` (required)
- `DEBUG` (optional, default: false)
- `PORT` (optional, default: 8000)

**Perfect for:**
- First-time users
- Quick prototypes
- Understanding core concepts

---

### 2. **basic_usage.py** - Complete Feature Tour

**What it demonstrates:**
- All EnvSync features in action
- Format validators (email, postgresql, etc.)
- Pattern validation with regex
- Custom validators
- Choices/enum validation
- Range validation for numbers
- Secret marking
- List type coercion

**Variables needed:**
- See `.env.example` for the full list (13 variables total)

**Perfect for:**
- Learning advanced features
- Reference implementation
- Production-ready patterns

---

## Testing Fail-Fast Behavior

Want to see EnvSync's validation in action? Try these experiments:

### Experiment 1: Missing Required Variable

```bash
# Remove .env temporarily
mv examples/.env examples/.env.backup

# Run quickstart - you'll see a helpful error!
python examples/quickstart.py

# You'll see exactly what's missing and how to fix it

# Restore .env
mv examples/.env.backup examples/.env
```

### Experiment 2: Invalid Value

```bash
# Edit .env and set PORT to an invalid value
echo "PORT=99999" >> examples/.env

# Run quickstart - validation catches it!
python examples/quickstart.py

# Fix it by setting PORT to a valid value (1-65535)
```

### Experiment 3: Demo Mode (No Setup Required)

```bash
# Run without any .env file
python examples/quickstart.py --demo

# All examples work in demo mode!
python examples/basic_usage.py --demo
```

---

## Common Issues & Solutions

### ❌ Error: Missing required environment variable

**What it means:** EnvSync is working correctly! It's enforcing that required variables must be set.

**How to fix:**
1. Copy `.env.example` to `.env`
2. Fill in the missing variable value
3. Run again

### ❌ Import errors or ModuleNotFoundError

**What it means:** EnvSync isn't installed in your environment.

**How to fix:**
```bash
# Make sure you've installed dependencies
uv sync

# Or if using pip
pip install -e .
```

### ❌ ValidationError: Format validation failed

**What it means:** The variable value doesn't match the expected format.

**How to fix:**
- Check the error message for expected format
- Look at `.env.example` for examples
- Fix the value in your `.env` file

### ❌ Examples directory vs root directory confusion

**Important:** The `.env` file should be in the `examples/` directory when running these examples:

```bash
# Correct structure:
examples/
  ├── .env          ← Your actual config (git-ignored)
  ├── .env.example  ← Template with documentation
  ├── quickstart.py
  └── basic_usage.py
```

---

## Quick Reference

### Running Examples

```bash
# From project root
python examples/quickstart.py
python examples/basic_usage.py

# With demo mode (no .env needed)
python examples/quickstart.py --demo
python examples/basic_usage.py --demo
```

### Setup Commands

```bash
# Copy template
cp examples/.env.example examples/.env

# Initialize new project (from root)
uv run envsync init

# Check for missing variables
uv run envsync check

# Generate documentation
uv run envsync docs
```

---

## Next Steps

1. ✅ Run `quickstart.py` successfully
2. ✅ Understand required vs optional variables
3. ✅ Explore `basic_usage.py` for advanced features
4. ✅ Read the main [README.md](../README.md) for full documentation
5. ✅ Integrate EnvSync into your own project

---

## Need Help?

- **Documentation:** See [README.md](../README.md)
- **Issues:** Check for validation error messages - they're designed to be helpful!
- **Examples:** All examples include detailed comments explaining each feature

---

**Pro Tip:** Start with `quickstart.py --demo` to see everything work immediately, then gradually customize your own `.env` file! 🚀
