[Home](../README.md) / [Reference](README.md) / Configuration

# Tool Configuration Reference

Configure TripWire behavior via `pyproject.toml` **NEW in v0.4.1**.

---

## `[tool.tripwire]` Section

Add this section to your `pyproject.toml`:

```toml
[tool.tripwire]
default_format = "table"
strict_mode = false
schema_file = ".tripwire.toml"
scan_git_history = true
max_commits = 1000
default_environment = "development"
```

---

## Configuration Options

### `default_format`

**Type:** `str`
**Default:** `"table"`
**Choices:** `"table"`, `"summary"`, `"json"`

Default output format for CLI commands.

**Example:**
```toml
[tool.tripwire]
default_format = "json"
```

**Effect:**
```bash
# With default_format = "json"
tripwire diff .env .env.prod
# Outputs JSON without needing --format=json flag
```

---

### `strict_mode`

**Type:** `bool`
**Default:** `false`

Exit with code 1 on warnings.

**Example:**
```toml
[tool.tripwire]
strict_mode = true
```

**Effect:**
```bash
# With strict_mode = true
tripwire check
# Exits 1 if any differences found (even if not errors)
```

---

### `schema_file`

**Type:** `str`
**Default:** `".tripwire.toml"`

Path to schema file.

**Example:**
```toml
[tool.tripwire]
schema_file = "config/schema.toml"
```

**Effect:**
```bash
# With custom schema_file
tripwire schema validate
# Uses config/schema.toml instead of .tripwire.toml
```

---

### `scan_git_history`

**Type:** `bool`
**Default:** `true`

Enable git history scanning for secrets.

**Example:**
```toml
[tool.tripwire]
scan_git_history = false
```

**Effect:**
```bash
# With scan_git_history = false
tripwire scan
# Only scans .env file, skips git history
```

---

### `max_commits`

**Type:** `int`
**Default:** `1000`

Maximum git commits to scan.

**Example:**
```toml
[tool.tripwire]
max_commits = 5000
```

**Effect:**
```bash
# With max_commits = 5000
tripwire audit --all
# Scans up to 5000 commits instead of 1000
```

---

### `default_environment`

**Type:** `str`
**Default:** `"development"`

Default environment name.

**Example:**
```toml
[tool.tripwire]
default_environment = "production"
```

**Effect:**
```bash
# With default_environment = "production"
tripwire schema validate
# Validates using production environment rules
```

---

## Complete Example

```toml
# pyproject.toml
[project]
name = "my-app"
version = "1.0.0"

[tool.tripwire]
# CLI defaults
default_format = "table"
strict_mode = false

# Schema configuration
schema_file = ".tripwire.toml"
default_environment = "development"

# Git scanning
scan_git_history = true
max_commits = 1000
```

---

## Environment-Specific Overrides

Override defaults per environment:

```toml
[tool.tripwire]
default_environment = "development"

[tool.tripwire.environments.development]
strict_mode = false
scan_git_history = false

[tool.tripwire.environments.staging]
strict_mode = true
scan_git_history = true
max_commits = 5000

[tool.tripwire.environments.production]
strict_mode = true
scan_git_history = true
max_commits = 10000
```

---

## Command-Line Overrides

CLI flags always override configuration:

```bash
# Even with strict_mode = false in config
tripwire check --strict  # Uses strict mode

# Even with default_format = "table" in config
tripwire diff .env .env.prod --format=json  # Outputs JSON
```

---

**[Back to Reference](README.md)**
