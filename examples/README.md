# TripWire Examples

Welcome to TripWire examples! This directory contains runnable, verified examples that demonstrate TripWire's features. Every example in this directory is executable and tested.

## Quick Start

**Fastest way to get started:**

```bash
# Run any example in demo mode (no .env setup needed!)
python examples/basic/01_simple_require.py --demo
python examples/problems/01_os_getenv_none.py
python examples/advanced/01_range_validation.py --demo
```

**With your own configuration:**

```bash
# 1. Create .env file from template
cp examples/.env.template examples/.env

# 2. Edit .env with your values
nano examples/.env  # or your favorite editor

# 3. Run examples
python examples/basic/01_simple_require.py
```

---

## Directory Structure

Examples are organized by complexity and purpose:

```
examples/
├── basic/              # Simple, single-concept examples (START HERE)
│   ├── 01_simple_require.py
│   ├── 02_optional_with_default.py
│   ├── 03_type_coercion.py
│   └── 04_format_validation.py
├── problems/           # Anti-patterns (what NOT to do)
│   ├── 01_os_getenv_none.py
│   ├── 02_int_conversion_error.py
│   └── 03_boolean_comparison.py
├── advanced/           # Advanced validation features
│   ├── 01_range_validation.py
│   ├── 02_choices_enum.py
│   ├── 03_pattern_matching.py
│   └── 04_custom_validators.py
└── frameworks/         # Framework integrations
    ├── fastapi_integration.py
    ├── flask_integration.py
    └── django_settings.py
```

---

## Basic Examples (Start Here)

### 01_simple_require.py

**What it demonstrates:**
- Basic `env.require()` usage
- Import-time validation
- Fail-fast behavior

**Run it:**
```bash
python examples/basic/01_simple_require.py --demo
```

**README Reference:** [Basic Usage](../README.md#basic-usage)

---

### 02_optional_with_default.py

**What it demonstrates:**
- `env.optional()` with default values
- Type inference from defaults
- Never-fail pattern for non-critical config

**Run it:**
```bash
python examples/basic/02_optional_with_default.py --demo
```

**README Reference:** [Optional Variables](../README.md#optional-variables)

---

### 03_type_coercion.py

**What it demonstrates:**
- Automatic type coercion (int, bool, float)
- Type annotation-driven conversion
- No manual parsing needed

**Run it:**
```bash
python examples/basic/03_type_coercion.py --demo
```

**README Reference:** [Type Inference](../README.md#type-inference)

---

### 04_format_validation.py

**What it demonstrates:**
- Built-in format validators (postgresql, url, email)
- Pattern-based validation
- Helpful error messages

**Run it:**
```bash
python examples/basic/04_format_validation.py --demo
```

**README Reference:** [Format Validators](../README.md#format-validators)

---

## Problems Examples (Anti-Patterns)

These examples show common pitfalls and why TripWire exists.

### 01_os_getenv_none.py

**Demonstrates the problem:**
- `os.getenv()` returns None silently
- Errors happen at runtime, not startup
- Hard to debug in production

**Run it:**
```bash
python examples/problems/01_os_getenv_none.py
```

**README Reference:** [The Problem](../README.md#the-problem)

---

### 02_int_conversion_error.py

**Demonstrates the problem:**
- `int(os.getenv())` raises TypeError
- Shows exact error type from README
- Why type coercion matters

**Run it:**
```bash
python examples/problems/02_int_conversion_error.py
```

**README Reference:** [The Problem](../README.md#the-problem)

---

### 03_boolean_comparison.py

**Demonstrates the problem:**
- String "false" is truthy in Python
- Boolean parsing pitfalls
- TripWire's correct solution

**Run it:**
```bash
python examples/problems/03_boolean_comparison.py
```

**README Reference:** [Type Coercion](../README.md#type-inference)

---

## Advanced Examples

### 01_range_validation.py

**What it demonstrates:**
- min_val and max_val validation
- Numeric constraints
- Port number validation

**Run it:**
```bash
python examples/advanced/01_range_validation.py --demo
```

**README Reference:** [Advanced Validation](../README.md#advanced-usage)

---

### 02_choices_enum.py

**What it demonstrates:**
- choices parameter for enums
- Restricted value sets
- Environment selection patterns

**Run it:**
```bash
python examples/advanced/02_choices_enum.py --demo
```

**README Reference:** [Choices Validation](../README.md#advanced-usage)

---

### 03_pattern_matching.py

**What it demonstrates:**
- Regex pattern validation
- API key format validation
- Semantic versioning checks

**Run it:**
```bash
python examples/advanced/03_pattern_matching.py --demo
```

**README Reference:** [Pattern Validation](../README.md#advanced-usage)

---

### 04_custom_validators.py

**What it demonstrates:**
- Creating custom validators
- Registering validators globally
- Reusable validation logic

**Run it:**
```bash
python examples/advanced/04_custom_validators.py --demo
```

**README Reference:** [Custom Validators](../README.md#custom-validators)

---

## Framework Integration Examples

### fastapi_integration.py

**What it demonstrates:**
- TripWire + FastAPI integration
- Configuration validation before server starts
- Type-safe FastAPI settings

**Run it:**
```bash
python examples/frameworks/fastapi_integration.py --demo
```

**Requirements:**
```bash
pip install fastapi uvicorn
```

**README Reference:** [Framework Integration](../README.md#framework-integration)

---

### flask_integration.py

**What it demonstrates:**
- TripWire + Flask integration
- Validating Flask configuration
- Secret key management

**Run it:**
```bash
python examples/frameworks/flask_integration.py --demo
```

**Requirements:**
```bash
pip install flask
```

**README Reference:** [Framework Integration](../README.md#framework-integration)

---

### django_settings.py

**What it demonstrates:**
- TripWire in Django settings.py
- Django-specific configuration patterns
- Security settings validation

**Run it:**
```bash
python examples/frameworks/django_settings.py --demo
```

**README Reference:** [Framework Integration](../README.md#framework-integration)

---

## Testing Examples

All examples in this directory are tested. To run the test suite:

```bash
# Test basic examples
pytest tests/examples/test_basic_examples.py

# Test advanced examples
pytest tests/examples/test_advanced_examples.py

# Test framework examples
pytest tests/examples/test_framework_examples.py

# Run all example tests
pytest tests/examples/
```

---

## Common Patterns

### Demo Mode

Most examples support `--demo` flag for testing without .env setup:

```bash
python examples/basic/01_simple_require.py --demo
python examples/advanced/01_range_validation.py --demo
python examples/frameworks/fastapi_integration.py --demo
```

### Error Testing

Examples in `problems/` directory are designed to fail (showing anti-patterns):

```bash
# These demonstrate errors you'd encounter without TripWire
python examples/problems/01_os_getenv_none.py
python examples/problems/02_int_conversion_error.py
```

### Framework Examples

Framework examples can run standalone (demo mode) or as actual servers:

```bash
# Demo mode - just validates config
python examples/frameworks/fastapi_integration.py --demo

# Server mode - actually starts the server
export DATABASE_URL="postgresql://localhost/mydb"
export API_KEY="your_api_key"
python examples/frameworks/fastapi_integration.py
```

---

## Adding New Examples

When adding new examples:

1. **Choose the right directory:**
   - `basic/` - Simple, single-concept examples
   - `problems/` - Anti-patterns showing what NOT to do
   - `advanced/` - Advanced validation features
   - `frameworks/` - Integration with web frameworks

2. **Follow the template:**
   ```python
   """Example: [Brief title]

   This example demonstrates [what it shows].

   README Reference: [Section name]

   Expected behavior:
   - [What should happen]

   Run this example:
       export VAR="value"
       python examples/[category]/[number]_[name].py

   Or use demo mode:
       python examples/[category]/[number]_[name].py --demo
   """
   ```

3. **Add to this README:**
   - Document what it demonstrates
   - Link to relevant README section
   - Show how to run it

4. **Add tests:**
   - Create test in `tests/examples/test_[category]_examples.py`
   - Verify expected behavior
   - Test both success and failure cases

5. **Update .env.template:**
   - Add any new environment variables
   - Include helpful comments

---

## Legacy Examples

The root `examples/` directory also contains older examples:

- `quickstart.py` - Original quickstart example (still valid)
- `basic_usage.py` - Original comprehensive example (still valid)
- `advanced_usage.py` - Advanced features demo
- `custom_validators.py` - Custom validator examples

These work but the new organized structure (`basic/`, `advanced/`, etc.) is recommended for new users.

---

## Environment Variables

### Required for Basic Examples:
```bash
DATABASE_URL=postgresql://localhost:5432/mydb
```

### Optional (have defaults):
```bash
DEBUG=true
PORT=8080
LOG_LEVEL=INFO
```

### For Advanced Examples:
```bash
MAX_CONNECTIONS=100
TIMEOUT=30.0
ENVIRONMENT=production
API_KEY=sk_live_abc123xyz789
VERSION=1.2.3
USERNAME=john_doe
WEBHOOK_URL=https://hooks.example.com/webhook
```

### For Framework Examples:
```bash
SECRET_KEY=your-secret-key-minimum-16-chars
DJANGO_SECRET_KEY=your-django-secret-key-must-be-at-least-32-characters-long
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Full template:** See [.env.template](.env.template)

---

## Troubleshooting

### Error: Missing required environment variable

**Solution:**
```bash
# Use demo mode
python examples/basic/01_simple_require.py --demo

# Or set the variable
export DATABASE_URL="postgresql://localhost/mydb"
```

### Import errors

**Solution:**
```bash
# Install TripWire in development mode
pip install -e .

# Or with uv
uv pip install -e .
```

### Examples can't find tripwire module

**Solution:**
All examples add project root to sys.path automatically. If still having issues:

```bash
# Run from project root
cd /path/to/TripWire
python examples/basic/01_simple_require.py
```

---

## Next Steps

1. Run `python examples/basic/01_simple_require.py --demo`
2. Explore other basic examples
3. Check out anti-patterns in `problems/`
4. Try advanced validation in `advanced/`
5. See framework integrations in `frameworks/`
6. Read the main [README.md](../README.md)
7. Integrate TripWire into your project

---

## Contributing

To add new examples:

1. Create the example file in appropriate directory
2. Follow the template format
3. Add tests to `tests/examples/`
4. Update this README
5. Add to `.env.template` if needed
6. Submit PR with `examples` label

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

---

**All examples are verified and tested.** See the test suite in `tests/examples/` for validation.

**Questions?** Check the [main README](../README.md) or open an issue.
