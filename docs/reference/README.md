[Home](../README.md) / Reference

# Reference Documentation

Technical reference for TripWire's APIs and features.

---

## API Documentation

- **[Python API](api.md)** - Complete TripWire Python API
  - Core methods (`require`, `optional`)
  - Typed methods (`require_int`, `optional_bool`, etc.)
  - Configuration methods
  - Custom validators

- **[Validators](validators.md)** - All built-in and custom validators
  - Format validators (email, url, postgresql, uuid, ipv4)
  - Type validators (str, int, float, bool, list, dict)
  - Constraint validators (range, length, pattern, choices)
  - Custom validator examples

- **[Type Inference](type-inference.md)** - Automatic type detection (v0.4.0+)
  - How type inference works
  - Supported types
  - Optional[T] handling
  - Fallback behavior

- **[Configuration](configuration.md)** - `[tool.tripwire]` settings (v0.4.1+)
  - All configuration options
  - Environment-specific overrides
  - Command-line precedence

---

**[Back to Documentation Home](../README.md)**
