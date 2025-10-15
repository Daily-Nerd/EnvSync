# Custom Validators Demo

This example demonstrates the **correct workflow** for creating and using custom validators with TripWire.

## Directory Structure

```
custom_validators_demo/
├── __init__.py           # Makes directory a Python package
├── custom_validators.py  # Validator definitions (registration happens here)
├── main.py              # Example usage that imports validators
└── README.md            # This file
```

## Key Concepts

### Import-Time Registration

Custom validators are registered **at import-time** when the `custom_validators` module is imported:

```python
# When this line executes, ALL validators are registered
from custom_validators import validate_phone_number
```

This is different from **code execution** that happens when you run a script. The AST scanner used by `tripwire schema from-code` only analyzes code structure WITHOUT executing it, so it won't see validators that haven't been imported yet.

## Usage

### Running the Demo

```bash
# From the project root
python examples/custom_validators_demo/main.py
```

Expected output:
```
All custom validators passed!
Phone: 555-123-4567
ZIP: 94102
Color: #FF5733
Username: admin_user
Version: 1.0.0
Region: us-west-2
Domain: example.com
Token: SGVsbG8gV29ybGQ=
```

### Using Custom Validators in Your Code

**Step 1:** Create your validator definitions (like `custom_validators.py`)

```python
from tripwire.validation import register_validator_decorator

@register_validator_decorator("username")
def validate_username(value: str) -> bool:
    """Validate username format."""
    pattern = r"^[a-zA-Z0-9_-]{3,20}$"
    return bool(re.match(pattern, value))
```

**Step 2:** Import validators in your application code (like `main.py`)

```python
# This import registers all validators
from custom_validators import validate_username

from tripwire import env

# Now you can use the custom format
username = env.require("ADMIN_USERNAME", format="username")
```

## Working with Schema Commands

### Default Behavior (Recommended)

```bash
# Generate schema WITHOUT auto-validation (default behavior)
tripwire schema from-code

# Validators register when your code imports them
# Now validate the schema separately
tripwire schema check
```

This is the **recommended approach** because:
- `schema from-code` uses AST scanning (doesn't execute code)
- Validators aren't registered during AST scanning
- Skipping auto-validation prevents false errors
- You validate separately after validators are registered

### Advanced: Using --validate Flag

```bash
# First, ensure validators are registered
python -c "from examples.custom_validators_demo import custom_validators"

# Then generate WITH validation
tripwire schema from-code --validate
```

Only use `--validate` if you need immediate validation feedback and have already imported the validator registration code.

## Available Custom Validators

This demo includes 8 custom validators:

| Format | Description | Example |
|--------|-------------|---------|
| `phone` | US phone number | `555-123-4567` |
| `zip_code` | US ZIP code | `94102` or `94102-1234` |
| `hex_color` | Hex color code | `#FF5733` or `#F73` |
| `username` | Username format | `admin_user` |
| `semantic_version` | Semantic version | `1.0.0` |
| `aws_region` | AWS region code | `us-west-2` |
| `domain` | Domain name | `example.com` |
| `base64` | Base64 string | `SGVsbG8gV29ybGQ=` |

## Two Registration Methods

### Method 1: Explicit Registration

```python
from tripwire.validation import register_validator

def validate_phone_number(value: str) -> bool:
    pattern = r"^\d{3}-\d{3}-\d{4}$"
    return bool(re.match(pattern, value))

register_validator("phone", validate_phone_number)
```

### Method 2: Decorator Registration (Recommended)

```python
from tripwire.validation import register_validator_decorator

@register_validator_decorator("phone")
def validate_phone_number(value: str) -> bool:
    pattern = r"^\d{3}-\d{3}-\d{4}$"
    return bool(re.match(pattern, value))
```

Both methods are equivalent. The decorator syntax is cleaner and more Pythonic.

## Testing

Verify validators are registered correctly:

```python
from examples.custom_validators_demo import custom_validators
from tripwire.validation import _CUSTOM_VALIDATORS

print("Registered validators:", list(_CUSTOM_VALIDATORS.keys()))
# Output: ['phone', 'zip_code', 'hex_color', 'username',
#          'semantic_version', 'aws_region', 'domain', 'base64']
```

## Common Pitfalls

1. **Don't forget to import validators before using them**
   ```python
   # ❌ WRONG - validators not imported
   from tripwire import env
   username = env.require("USERNAME", format="username")  # ValidationError!

   # ✅ CORRECT - import validators first
   from custom_validators import validate_username
   from tripwire import env
   username = env.require("USERNAME", format="username")
   ```

2. **Don't expect AST scanning to see validators**
   ```bash
   # ❌ WRONG - will fail if validators aren't imported
   tripwire schema from-code --validate

   # ✅ CORRECT - generate without validation, check separately
   tripwire schema from-code
   tripwire schema check
   ```

3. **Don't confuse import-time vs runtime**
   - Validators register when the module is **imported** (import-time)
   - Not when the script is **executed** (runtime)
   - AST scanning doesn't execute code, so it can't see validators

## See Also

- [TripWire Documentation](https://github.com/Daily-Nerd/TripWire)
- [Validation System](../../docs/validation.md)
- [Schema Commands](../../docs/schema.md)
