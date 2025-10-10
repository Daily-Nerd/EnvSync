# Changelog

All notable changes to TripWire will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2025-10-10

### Changed

- **Schema Command Reorganization**: Renamed commands for better clarity and consistency
  - `migrate-to-schema` → `schema from-example` (moved to schema group)
  - `schema generate-example` → `schema to-example` (clearer directionality)
  - `schema import` → `schema from-code` (explicit about source)
  - All schema operations now use clear `from-*/to-*` naming pattern

### Documentation

- Updated all documentation and examples to reflect new command names
- Enhanced CLI help text with improved user guidance
- Updated README, guides, and API reference

### Technical Details

- Comprehensive test updates for new command structure
- Maintains backward compatibility through command aliases
- 12 files updated across codebase

## [0.4.2] - 2025-10-10

### Added

- **PyYAML Dependency**: Added PyYAML as a project dependency for enhanced YAML support

### Changed

- **Enhanced Security in `migrate-to-schema`**: Improved security checks when migrating from real .env files
  - Warns users when source appears to be a real environment file (not .env.example)
  - Provides clear recommendations to create .env.example first with placeholder values
  - Requires explicit confirmation to continue with real .env files
  - Prevents accidental secret exposure in schema files committed to git

### Removed

- Removed legacy EnvSync.md documentation file

### Technical Details

- Added 33 new tests for scanner validation
- Enhanced CLI error handling and user prompts during migration
- All tests passing with improved security coverage

## [0.4.1] - 2025-10-09

### Added

- **Tool Configuration System**: TripWire now supports configuration via `pyproject.toml [tool.tripwire]`
  - `default_format`: Set default output format for CLI commands
  - `strict_mode`: Exit 1 on warnings
  - `schema_file`: Specify custom .tripwire.toml location
  - `scan_git_history`: Enable/disable git scanning
  - `max_commits`: Configure git scan depth
  - `default_environment`: Set default environment name

- **`tripwire migrate-to-schema` Command**: Migrate legacy .env.example to modern .tripwire.toml schema
  - Automatic type inference (int, float, bool, string)
  - Secret detection based on variable names
  - Format detection (postgresql, url, email, ipv4)
  - Placeholder detection (your-*-here, change-me)
  - Statistics output showing migration results

- **Enhanced `tripwire generate` Command**: New `--from-schema` flag
  - Generate .env.example from .tripwire.toml schema
  - Complements existing code-scanning functionality
  - Example: `tripwire generate --from-schema`

### Changed

- Fixed broken link in README.md (audit documentation reference)
- Clarified roadmap to distinguish implemented vs planned TOML features

### Technical Details

- Added `src/tripwire/tool_config.py` module for configuration management
- Added 24 new tests (833 total tests, all passing)
- 100% test coverage on new features
- Maintains backward compatibility with existing workflows

## [0.4.0] - 2025-10-09

### Added

- **Type Inference from Annotations**: TripWire now automatically infers types from variable annotations - no need to specify `type=` twice!
  ```python
  # Before (still works)
  PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)

  # Now (recommended)
  PORT: int = env.require("PORT", min_val=1, max_val=65535)
  ```
  - Supports `int`, `float`, `bool`, `str`, `list`, `dict`
  - Handles `Optional[T]` annotations (extracts `T`)
  - Works with module-level and function-level variables
  - Falls back to `str` if type cannot be inferred

- **`tripwire diff` Command**: Compare configuration files across environments
  - Compare .env files (`.env` vs `.env.prod`)
  - Compare TOML files (`pyproject.toml` vs `config.toml`)
  - Cross-format comparison (`.env` vs `pyproject.toml`)
  - Categorizes changes as Added/Removed/Modified/Unchanged
  - Automatic secret masking for security
  - Multiple output formats (table, summary, JSON)
  - Use cases: environment comparison, deployment verification, drift auditing

- **Unified Config Abstraction Layer**: Repository + Adapter pattern for format-agnostic configuration management
  - `ConfigRepository` facade for unified access to multiple formats
  - `EnvFileSource` adapter for .env files with comment preservation
  - `TOMLSource` adapter for TOML files (supports nested sections)
  - `ConfigValue` model with metadata (source type, file path, line numbers, secret detection)
  - `ConfigDiff` model for structured comparison results
  - Auto-format detection from file extensions
  - Multiple source support with configurable merge strategies (LAST_WINS, FIRST_WINS, STRICT)

- **Multi-Format Support**: .env and TOML formats supported throughout the library
  - TOML format support via `tomli`/`tomli-w` libraries
  - Cross-format operations (load from .env, save to TOML, and vice versa)
  - Preserves format-specific features (comments in .env, nested structures in TOML)

### Changed

- Type specification via `type=` parameter is now optional when using type annotations (backward compatible - old API still works)
- Enhanced type inference now uses dynamic frame search instead of fixed depth for better reliability

### Fixed

- Fixed type inference bug where `optional()` method failed to infer types (frame depth issue)
- Fixed mypy type errors in config module with proper type narrowing and annotations

### Technical Details

- Added 80 comprehensive tests for config abstraction layer (100% pass rate)
- All 809 tests passing across the entire codebase
- Strict mypy type checking maintained throughout
- Repository pattern allows future format support via plugin system (v0.5.0+)

### Design Decisions

- **Why .env + TOML only?** Covers 95% of Python projects. YAML has security risks, JSON has poor UX for env vars. Cloud secrets deferred to plugin system in v0.5.0.
- **Why Repository + Adapter pattern?** New commands automatically work with all formats without code duplication. Extensible for future formats via plugins.

## [0.3.0] - Previous Release

### Added

- Configuration as Code (TOML schemas)
- Schema validation
- Environment-specific defaults
- Schema import from code
- Schema-based .env.example generation

## [0.2.0] - Previous Release

### Added

- Git audit with timeline and remediation (`audit` command)
- Auto-detect and audit all secrets (`audit --all`)
- 45+ platform-specific secret patterns
- Secret detection and scanning
- Git history analysis

## [0.1.0] - Initial Release

### Added

- Import-time validation
- Type coercion (str, int, bool, float, list, dict)
- Format validators (email, url, uuid, ipv4, postgresql)
- Custom validators
- `.env.example` generation from code
- Drift detection (`check` command)
- Team sync (`sync` command)
- Multi-environment support
- Documentation generation (`docs` command)
- CLI implementation with rich output
- Project initialization (`init` command)

[Unreleased]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Daily-Nerd/TripWire/releases/tag/v0.1.0
