[Home](../README.md) / [Advanced](README.md) / Type System

# Type System Deep Dive

Advanced guide to TripWire's type inference and coercion system.

---

## Type Inference (v0.4.0+)

### How It Works

TripWire inspects the call stack at runtime to extract type annotations:

```python
# Type annotation here ↓
PORT: int = env.require("PORT", min_val=1024)
#              ↑ TripWire inspects the stack to find the 'int' annotation
```

**Technical Details:**
1. `env.require()` is called
2. Frame inspection searches up the stack for variable assignment
3. Type annotation extracted from local/global namespace
4. Type used for coercion and validation

---

## Supported Types

### Primitive Types

```python
# String (default)
API_KEY: str = env.require("API_KEY")

# Integer
PORT: int = env.require("PORT")

# Float
TIMEOUT: float = env.optional("TIMEOUT", default=30.0)

# Boolean
DEBUG: bool = env.optional("DEBUG", default=False)
```

### Collection Types

```python
# List
ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS")

# Dictionary
FEATURE_FLAGS: dict = env.optional("FEATURE_FLAGS", default={})
```

### Optional Types

```python
from typing import Optional

# Optional[int] - extracts 'int'
MAX_RETRIES: Optional[int] = env.optional("MAX_RETRIES", default=None)

# Optional[str] - extracts 'str'
LOG_FILE: Optional[str] = env.optional("LOG_FILE", default=None)
```

---

## Type Coercion

### String → Int

```python
# .env
PORT=8000

# Python
PORT: int = env.require("PORT")  # 8000 (int)
```

**Coercion Rules:**
- Strips whitespace
- Converts to int using `int()`
- Fails on decimals: `"3.14"` → `ValueError`
- Fails on non-numeric: `"abc"` → `ValueError`

### String → Float

```python
# .env
TIMEOUT=30.5

# Python
TIMEOUT: float = env.require("TIMEOUT")  # 30.5 (float)
```

**Coercion Rules:**
- Strips whitespace
- Converts using `float()`
- Accepts integers: `"30"` → `30.0`
- Accepts scientific notation: `"1e-3"` → `0.001`

### String → Bool

```python
# .env
DEBUG=true
MAINTENANCE=yes
STRICT=1

# Python
DEBUG: bool = env.optional("DEBUG", default=False)  # True
MAINTENANCE: bool = env.optional("MAINTENANCE", default=False)  # True
STRICT: bool = env.optional("STRICT", default=False)  # True
```

**Truthy Values:** `"true"`, `"True"`, `"TRUE"`, `"yes"`, `"Yes"`, `"YES"`, `"on"`, `"On"`, `"ON"`, `"1"`

**Falsy Values:** `"false"`, `"False"`, `"FALSE"`, `"no"`, `"No"`, `"NO"`, `"off"`, `"Off"`, `"OFF"`, `"0"`, `""`

### String → List

```python
# .env
# Comma-separated
HOSTS=localhost,example.com,api.example.com

# JSON array
TAGS=["python", "web", "api"]

# Python
HOSTS: list = env.require("HOSTS")  # ["localhost", "example.com", "api.example.com"]
TAGS: list = env.require("TAGS")    # ["python", "web", "api"]
```

**Parsing Strategy:**
1. Try JSON parsing (`json.loads()`)
2. If JSON fails, split by comma
3. Strip whitespace from each element

### String → Dict

```python
# .env
# JSON object
CONFIG={"debug": true, "timeout": 30}

# Key=value pairs
FEATURES=new_ui=true,beta=false,analytics=true

# Python
CONFIG: dict = env.require("CONFIG")     # {"debug": True, "timeout": 30}
FEATURES: dict = env.require("FEATURES") # {"new_ui": "true", "beta": "false", ...}
```

**Parsing Strategy:**
1. Try JSON parsing (`json.loads()`)
2. If JSON fails, parse key=value pairs

---

## Frame Inspection

### How Stack Inspection Works

```python
import inspect

def require(name: str, **kwargs):
    # Get current frame
    frame = inspect.currentframe()

    # Search up stack for variable assignment
    for i in range(1, 10):  # Check up to 10 frames
        caller_frame = inspect.stack()[i].frame

        # Get local and global variables
        locals_dict = caller_frame.f_locals
        globals_dict = caller_frame.f_globals

        # Search for annotations
        if "__annotations__" in locals_dict:
            annotations = locals_dict["__annotations__"]
            # Extract type...
```

### Supported Contexts

**✅ Module-level:**
```python
# config.py
DATABASE_URL: str = env.require("DATABASE_URL")  # ✅ Works
```

**✅ Function-level:**
```python
def get_config():
    PORT: int = env.require("PORT")  # ✅ Works
    return PORT
```

**✅ Class-level:**
```python
class Config:
    DEBUG: bool = env.optional("DEBUG", default=False)  # ✅ Works
```

**❌ Dictionary (no annotation):**
```python
config = {
    "port": env.require("PORT")  # ❌ No annotation, falls back to str
}

# Solution: Use typed methods
config = {
    "port": env.require_int("PORT")  # ✅ Explicit type
}
```

---

## Fallback Behavior

When type cannot be inferred:

```python
# No annotation
value = env.require("SOME_VAR")  # Falls back to str

# In dictionary
config = {
    "port": env.require("PORT")  # Falls back to str (no annotation)
}

# Lambda/comprehension
ports = [env.require(f"PORT_{i}") for i in range(5)]  # Falls back to str
```

**Solution:** Use typed methods or explicit `type=` parameter:

```python
# Typed methods
config = {
    "port": env.require_int("PORT")
}

# Explicit type
value = env.require("PORT", type=int)
```

---

## Edge Cases

### Optional[T] Handling

```python
from typing import Optional

# Extracts int from Optional[int]
MAX_RETRIES: Optional[int] = env.optional("MAX_RETRIES", default=None)
# If set: coerced to int
# If not set: None
```

### Union Types (Not Supported)

```python
from typing import Union

# ⚠️ Union types not supported - uses first type
VALUE: Union[int, str] = env.require("VALUE")  # Uses int

# Solution: Use one type or custom validator
```

### Generic Types

```python
from typing import List, Dict

# List[str] - uses 'list'
HOSTS: List[str] = env.require("HOSTS")  # Works, but inner type ignored

# Dict[str, int] - uses 'dict'
CONFIG: Dict[str, int] = env.require("CONFIG")  # Works, but inner types ignored
```

---

## Performance Considerations

### Frame Inspection Cost

Frame inspection has minimal overhead (~1-2ms per call):

```python
# Cached after first call
PORT: int = env.require("PORT")  # ~2ms (frame inspection)
PORT2: int = env.require("PORT")  # <0.1ms (cached)
```

### Optimization: Use Typed Methods in Loops

```python
# ❌ Slow: Frame inspection in loop
for i in range(1000):
    value: int = env.require(f"VAR_{i}")

# ✅ Fast: Typed method
for i in range(1000):
    value = env.require_int(f"VAR_{i}")
```

---

## Debugging Type Inference

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# TripWire logs type inference
PORT: int = env.require("PORT")
# DEBUG: Inferred type 'int' for PORT from annotation
```

### Verify Inferred Type

```python
# Check what type was inferred
PORT: int = env.require("PORT")
print(type(PORT))  # <class 'int'>
```

---

## Best Practices

### 1. Always Use Type Annotations

```python
# ✅ DO: Type annotations enable inference
PORT: int = env.require("PORT", min_val=1024)

# ❌ DON'T: No annotation requires explicit type
PORT = env.require("PORT", type=int, min_val=1024)
```

### 2. Use Typed Methods in Collections

```python
# ✅ DO: Typed methods in dicts
config = {
    "port": env.require_int("PORT"),
    "debug": env.optional_bool("DEBUG", default=False)
}

# ❌ DON'T: No type inference in dicts
config = {
    "port": env.require("PORT"),  # Falls back to str!
}
```

### 3. Specify Type for Complex Coercion

```python
# ✅ DO: Explicit type for complex types
HOSTS: list = env.require("HOSTS")  # Clear intent

# ❌ DON'T: Rely on fallback
HOSTS = env.require("HOSTS", type=list)  # Redundant
```

---

**[Back to Advanced](README.md)**
