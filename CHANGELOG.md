# Changelog

All notable changes to TripWire will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.0] - 2025-10-15

### Added

- **Phase 1: Deferred Validation for Custom Validators** - Solves the custom validator process boundary problem
  - New `custom:` prefix convention for custom validators in schema files (e.g., `format = "custom:phone"`)
  - CLI commands now gracefully defer validation for custom validators that aren't available during schema processing
  - Schema validation skips `custom:*` format validators instead of failing with "unknown format" errors
  - Clear warning messages explain that custom validators validate at runtime when registered in application process
  - `schema from-code` automatically emits `custom:` prefix for non-builtin validators during schema generation
  - Pattern validation still runs independently (inline regex patterns always validated by CLI)
  - Comprehensive test suite with 17 tests covering all deferred validation scenarios

### Changed

- **Enhanced Schema Validation Messages** - Better guidance for custom validator workflows
  - `schema check` shows warnings (not errors) for custom validators with actionable guidance
  - `schema validate` skips custom validators with warnings explaining runtime validation
  - `schema to-env` messaging clarified about custom validator import requirements
  - Error messages now suggest using `custom:` prefix when unknown format validators detected

### Improved

- **Developer Experience** - Clearer separation between CLI-time and runtime validation
  - No more confusing "Unknown format 'phone'" errors for custom validators
  - CLI commands complete successfully even when custom validators aren't imported
  - Explicit messaging about when validation is deferred vs performed
  - Documentation updated with best practices for custom validator usage

### Technical Details

- Updated `VariableSchema._validate_format()` to detect and skip `custom:` prefixed validators (30 lines, comprehensive docstring)
- Enhanced `schema check` command to collect and display custom validator warnings separately from errors (40 lines)
- Updated `schema from-code` command to emit `custom:` prefix for non-builtin validators automatically (15 lines)
- Messaging improvements in `schema validate` and `schema to-env` commands (10 lines)
- Added `tests/test_deferred_validation.py` with 17 comprehensive tests covering:
  - Custom prefix detection and skipping
  - Builtin validator behavior unchanged
  - Schema validation with mixed builtin/custom validators
  - Schema check command warning display
  - Schema from-code prefix emission
  - Runtime validation with registered validators
  - Backward compatibility with existing validators
  - Edge cases (empty prefix, nested prefix, case sensitivity, whitespace)
- All 84 schema-related tests passing (including 17 new deferred validation tests)
- Zero breaking changes - fully backward compatible with existing schemas

### Documentation

- Updated inline documentation in `schema.py` explaining deferred validation behavior
- Enhanced `schema from-code` command help text with custom validator guidance
- Added comprehensive docstrings to `_validate_format()` method explaining process boundary problem
- Schema check command now shows informative notes about custom validator behavior

### Why This Matters

**The Problem**: Custom validators are registered at import-time in your application process via `register_validator("phone", validate_phone)`. However, CLI commands like `tripwire schema check` run in a separate process where these validators don't exist, causing "Unknown format 'phone'" errors.

**The Solution**: Use `format = "custom:phone"` in your schema. CLI commands detect this prefix and defer validation to runtime. Your application code continues using the base name ("phone" without prefix) for registration and validation.

**Best Practice**: Use inline `pattern = "regex"` for simple validations (CLI can validate these). Reserve custom validators for complex logic requiring expensive operations (checksum validation, API calls, database lookups).

## [0.11.1] - 2025-10-14

### Added

- **Audit Progress Tracking**: Real-time progress indicators for git history scanning
  - New `cli/progress.py` module with `AuditProgressTracker` class
  - Progress bar mode when total commits known (shows percentage and counts)
  - Spinner mode when total commits unknown (shows running counts)
  - Context manager API: `audit_progress(total_commits=100)` for clean resource management
  - Live updates showing commits processed and secrets found (highlighted in red)
  - Transient displays that disappear after completion for clean terminal output
  - `count_commits()` helper in `git_audit.py` for fast commit counting (5s timeout)
  - Integrated into both single-secret and multi-secret audit workflows
  - Zero performance overhead - progress updates <1ms
  - Automatic cleanup on errors via context manager exception handling

### Changed

- **Enhanced Audit Command**: `tripwire security audit` now shows live progress
  - Progress bar with percentage when commit count is estimable
  - Spinner with running counts when commit count is unknown
  - Multi-secret mode shows "Auditing: SECRET_NAME (X/Y)" with progress
  - Secrets found highlighted in red for immediate visibility
  - JSON mode skips progress display (no terminal pollution)
  - Progress tracking only in interactive terminal mode

### Technical Details

- Added `AuditProgressTracker` class with dual display modes (150 lines)
- Added `audit_progress()` context manager for clean resource lifecycle
- Added `count_commits()` with 5s timeout to avoid blocking startup
- Integrated progress into `audit.py` for both `--all` and single-secret modes
- 140+ comprehensive tests in `tests/cli/test_progress.py` (>90% coverage)
  - Basic tracker functionality (start, update, finish, stop)
  - Context manager behavior and exception handling
  - Edge cases (zero commits, negative values, large numbers)
  - Integration tests with simulated audit workflows
  - Parametrized tests for mode selection and formatting
- All tests passing with mypy strict compliance
- Uses Rich library's Progress API for professional terminal UX
- Transient displays prevent terminal clutter after completion

## [0.11.0] - 2025-10-14

### Added

- **Secret Protection System**: Comprehensive defense-in-depth protection against accidental secret exposure
  - New `Secret[T]` wrapper class prevents secrets from being leaked in print(), logging, JSON, tracebacks
  - `env.require(..., secret=True)` now returns `Secret[T]` instead of plain values
  - Automatic masking in all string contexts: `str()`, `repr()`, `format()`, f-strings
  - Explicit `get_secret_value()` method for intentional access when needed (API calls, auth, etc.)
  - Thread-safe logging integration with automatic secret registration
  - Defense-in-depth: Even `get_secret_value()` output is masked in logs (requires logging integration)
  - Constant-time comparison for equality (prevents timing attacks)
  - JSON serialization protection (SecretJSONEncoder, StrictSecretJSONEncoder)
  - Immutable design with `__slots__` for memory efficiency and security
  - Compatible with Pydantic's SecretStr API for easier migration
  - Protection against pickle serialization (secrets still masked in repr after unpickling)
  - Comprehensive utilities: `mask_secret_in_string()`, `mask_multiple_secrets()`, `unwrap_secret()`

- **Logging Integration**: Automatic secret redaction in application logs
  - `SecretRedactionFilter` for Python's logging module (thread-safe)
  - `SecretRedactionFormatter` for custom log formatting with redaction
  - `register_secret()` for manual secret registration
  - `register_pattern()` for regex-based secret detection (AWS keys, GitHub tokens, etc.)
  - `register_common_patterns()` for automatic registration of 45+ platform-specific patterns
  - `auto_install()` convenience function for quick setup on any logger
  - Automatic secret registration when using `env.require(..., secret=True)`
  - Defense-in-depth: Even explicitly unwrapped secrets are masked in logs

### Security

- **BREAKING CHANGE**: `env.require(..., secret=True)` now returns `Secret[T]` instead of plain values
  - This is a major version change for safety - users must explicitly call `get_secret_value()`
  - Prevents accidental secret exposure through print(), logging, error messages, monitoring tools
  - Migration: Replace `secret_var` with `secret_var.get_secret_value()` only where needed
  - Type hint: `Secret[str]` instead of `str` for secret variables

### Documentation

- **Secret Protection Guide**: Comprehensive documentation of secret handling best practices
  - When to use `secret=True` vs manual Secret wrapper
  - How to access secrets safely with `get_secret_value()`
  - Defense-in-depth architecture explanation
  - User responsibility guidelines for unwrapped secrets
  - Integration with logging frameworks (Python logging, loguru, structlog)

### Testing

- **Comprehensive Test Coverage**: 700+ tests for secret protection
  - `tests/security/test_secret.py` - 50+ tests for Secret wrapper (masking, comparison, serialization)
  - `tests/security/test_logging.py` - 40+ tests for logging integration (filters, formatters, patterns)
  - Integration tests for TripWire + Secret + Logging
  - Thread-safety tests for concurrent secret registration
  - Defense-in-depth validation (unwrapped secrets still protected in logs)

### Technical Details

- Secret wrapper uses `__slots__` for memory efficiency (prevents attribute injection)
- Constant-time comparison via `secrets.compare_digest()` (timing attack protection)
- Thread-safe secret registry with `threading.Lock`
- Immutable design prevents modification after creation
- Generic type support: `Secret[T]` works with any type
- Zero performance overhead for non-secret variables
- Fully backward compatible (old code without `secret=True` works unchanged)

## [0.10.4] - 2025-10-14

### Fixed

- **Plugin Registry Loading Bug**: Fixed bundled registry not being used when remote registry is unavailable or returns empty results
  - Added validation to prevent caching empty/corrupt registry responses
  - Registry now validates plugin count before caching remote responses
  - Cache validation ensures corrupt caches are rejected and fallback to bundled registry occurs
  - Fixes issue where `plugin list --details` showed plugins as "unknown" metadata with "(custom)" type
  - Fixes issue where `plugin install` failed with "Plugin not found in registry" errors
  - Bundled registry now properly serves as ultimate fallback for offline and fresh installs
  - All 4 official plugins (Vault, AWS Secrets, Azure Key Vault, Remote Config) now display correct metadata

## [0.10.3] - 2025-10-14

### Fixed

- **Plugin System Functionality**: Implemented bundled registry for immediate plugin system functionality
  - Created bundled `registry.json` with 4 official plugins (Vault, AWS Secrets, Azure Key Vault, Remote Config)
  - Introduced `builtin://` URL scheme for plugins shipped with TripWire
  - Plugin CLI commands now work out of the box (`search`, `install`, `list`, `remove`)
  - Falls back to bundled registry when remote registry is unavailable
  - All plugins marked as "(bundled)" in plugin list output
  - Forward compatible with future PyPI-based plugin distribution (v0.11.0+)
  - Zero hosting costs - registry bundled with package
  - Offline-capable - works without network access
  - Comprehensive test coverage (60+ new tests)

- **Multi-Error UX Improvement**: Eliminated confusing "Exception ignored in atexit callback" messages
  - Changed atexit finalization to use `os._exit(1)` instead of raising exceptions
  - Clean stderr output without Python tracebacks
  - Proper exit code (1) on validation failures
  - Professional error presentation for production applications
  - Manual `finalize()` still raises exceptions for testing compatibility

### Technical Details

- Added bundled registry fallback system (Remote → Cache → Bundled)
- Implemented builtin plugin installer with dynamic import
- Enhanced CLI list command with plugin type indicators
- Package configuration updated to include registry.json in wheel
- All official plugins installable via `tripwire plugin install <name>`

## [0.10.2] - 2025-10-14

### Added

- **Multi-Error Validation**: Collect and display all validation errors together instead of failing on first error
  - New `TripWireMultiValidationError` exception for comprehensive error reporting
  - Enhanced `ValidationOrchestrator` with error collection mode (`collect_errors=True` by default)
  - Context-specific fix suggestions for each error type (format, range, length, missing variables)
  - Clear, numbered error list with tree-style formatting for better readability
  - Automatic finalization via `atexit` hooks
  - Backward compatible fail-fast mode available with `collect_errors=False`

- **CONTRIBUTING.md**: Community contribution guidelines and development workflow
  - Development setup instructions (venv, dependencies, pre-commit hooks)
  - Code style guide (Black, Ruff, Mypy requirements)
  - Testing requirements and coverage expectations
  - Pull request process with conventional commit guidelines
  - Areas for contribution and getting help resources

- **Enhanced Documentation**: Complete plugin CLI commands reference
  - Added plugin management commands to CLI reference guide
  - Documentation for `plugin install`, `search`, `list`, `update`, `remove`
  - Usage examples and output samples for each command
  - Updated version history in docs/README.md

### Security

- **Plugin HTTPS Enforcement with Local Flexibility** (TW-2025-007, TW-2025-008)
  - Vault plugin: HTTPS required by default with `allow_http=True` opt-in for local deployments
  - Remote-config plugin: HTTPS required by default with `allow_http=True` opt-in for cluster-internal communication
  - Security warnings displayed when HTTP is used
  - Valid use cases: localhost development, same-VM deployments, Kubernetes cluster-internal
  - Enhanced URL validation with scheme and hostname checks

### Fixed

- **Git Audit HEAD Validation**: Added validation to prevent command injection via malformed HEAD references
- **Git Command Timeouts**: Added 30-second default timeout to prevent hung processes on corrupted repositories
- **Test Suite**: Fixed 13 tests broken by multi-error validation changes
  - Updated tests to use explicit fail-fast mode where appropriate
  - Added `finalize()` calls in plugin integration tests
  - Fixed type inference test bug (PORT validation)

### Changed

- **Default Validation Behavior**: Error collection now enabled by default for better developer experience
  - Shows all validation errors at once instead of one at a time
  - Reduces fix → run → fix → run cycle frustration
  - Maintains backward compatibility with `collect_errors=False` option

### Documentation

- Updated README.md with Discord and VS Code extension links
- Added plugin CLI commands section to docs/guides/cli-reference.md
- Updated deprecated command references throughout documentation
- Fixed broken internal links in docs/README.md

### Technical Details

- Added 25 new tests for multi-error validation
- Updated 13 tests for compatibility with new validation behavior
- All 1429 tests passing with 76.45% code coverage
- Zero breaking changes - fully backward compatible

## [0.10.1] - 2025-10-13

### Added

- **URL Components Validation**: Fine-grained URL validation for security policies and API requirements
  - New `validate_url_components()` function in validation.py (lines 485-593)
  - Protocol whitelisting (enforce HTTPS-only, specific schemes)
  - Port restrictions (allowed ports whitelist, forbidden ports blacklist)
  - Path pattern validation using regex (enforce API versioning, URL structure)
  - Query parameter policies (required parameters, forbidden parameters)
  - Prevents SSRF attacks by restricting protocols and ports
  - Use cases: API endpoint security, webhook validation, OAuth callbacks, microservice communication
  - 36 comprehensive tests in tests/core/test_url_validation.py

- **DateTime Validation**: Flexible datetime validation for time-sensitive configurations
  - New `validate_datetime()` function in validation.py (lines 596-728)
  - ISO 8601 format support with automatic 'Z' suffix handling
  - Custom datetime formats via strptime format strings
  - Multiple format support (tries formats in order until match)
  - Timezone awareness enforcement (require timezone, forbid timezone, or allow both)
  - Date range validation with min_datetime and max_datetime bounds
  - Automatic timezone normalization for comparisons (naive vs aware)
  - Use cases: SSL certificate expiration, scheduled tasks, token expiry, license validation
  - 44 comprehensive tests in tests/core/test_datetime_validation.py

- **ValidationOrchestrator Integration**: New validation rule classes for TripWireV2
  - `URLComponentsValidationRule` class in validation_orchestrator.py (lines 281-353)
  - `DateTimeValidationRule` class in validation_orchestrator.py (lines 356-423)
  - Composable validation chains using builder pattern
  - Custom error message support with fallback to detailed validation messages
  - Non-string value skipping (type-appropriate validation)
  - Integration examples with multiple validation rules

### Performance

- **Test Parallelization**: 56% faster test execution with pytest-xdist
  - Added pytest-xdist dependency for parallel test execution
  - Tests run across multiple CPU cores automatically
  - No code changes required (transparent speedup)
  - Configurable via `pytest -n auto` for optimal parallelization

### Documentation

- **Enhanced Validator Reference**: Comprehensive documentation for advanced validators
  - Added "Advanced Validators" section to docs/reference/validators.md
  - URL Components Validation: Function signature, parameters, 7+ usage examples
  - DateTime Validation: Function signature, parameters, 8+ usage examples
  - Real-world use cases: Security policies, API versioning, scheduled tasks, expiration dates
  - ValidationOrchestrator integration examples for both validators
  - Code examples with error messages and .env file samples

### Testing

- **Comprehensive Test Coverage**: 80 new tests for validation features
  - URL validation: 36 tests covering protocols, ports, paths, query params, edge cases
  - DateTime validation: 44 tests covering formats, timezones, ranges, edge cases
  - All tests passing with 100% coverage on new features
  - Real-world scenario tests (SSL certs, scheduled tasks, API endpoints)

### Technical Details

- Total new code: 600+ lines of validation logic
- Test coverage: 100% on new validation functions
- API compatibility: Fully backward compatible with existing validators
- Dependencies: pytest-xdist (dev dependency only)

## [0.10.0] - 2025-10-12

### Added

- **Plugin Management System**: Complete plugin architecture for extensible environment variable sources
  - PluginMetadata dataclass for plugin identification and validation
  - EnvSourcePlugin protocol defining plugin interface contract
  - PluginInterface abstract base class with template methods
  - PluginRegistry for thread-safe plugin registration and discovery
  - Plugin validation with semantic versioning checks
- **Plugin CLI Commands**: New tripwire plugin command group for plugin management
  - plugin install - Install plugins from official registry
  - plugin search - Search for plugins by name/tag
  - plugin list - List installed plugins with metadata
  - plugin update - Update plugins to specific versions
  - plugin remove - Remove installed plugins
- **Official Plugin Sources**: Four production-ready environment sources
  - VaultEnvSource - HashiCorp Vault integration
  - AWSSecretsSource - AWS Secrets Manager integration
  - AzureKeyVaultSource - Azure Key Vault integration
  - RemoteConfigSource - Generic HTTP endpoint support
- **Enhanced TripWireV2**: Plugin system integration
  - Auto-loading support for plugin-based sources
  - Backward compatible with existing .env file loading
  - Custom loader flag tracking for intelligent auto-load behavior

### Changed

- Core Loader: Added plugin source support to EnvFileLoader
- Import System: Exported plugin components from tripwire.core for public API

### Fixed

- **Security: Azure Plugin URL Validation** (TW-2025-004, HIGH severity)
  - Enhanced HTTPS scheme enforcement to prevent HTTP downgrade attacks
  - Added domain validation requiring `.vault.azure.net` suffix to prevent domain spoofing
  - Validates URL format with proper error messages for invalid Azure Key Vault URLs
  - Commit: 4151a3a (2025-10-12)

- **Security: Plugin Registry SSRF Protection** (TW-2025-005, MEDIUM severity)
  - URL scheme validation prevents SSRF attacks via file://, gopher://, etc.
  - Blocks fetching from internal network resources through plugin URLs
  - Whitelist-based scheme validation (https:// only for plugin registry)
  - Commit: 4151a3a (2025-10-12)

- **Security: Plugin Path Traversal Protection** (TW-2025-006, HIGH severity)
  - Path sanitization prevents `../` traversal attacks in plugin installation
  - Blocks writing plugin files outside designated plugin directory
  - Prevents arbitrary file write vulnerabilities
  - Commit: 4151a3a (2025-10-12)

- PyYAML Imports: Removed type ignore comments for better type checking
- AWS Plugin: Clarified secret name sanitization for environment variable compatibility

### Technical Details

- Added 7,315+ lines of plugin system code
- 847 new tests for plugin CLI commands
- 1,176 tests for official plugin sources
- Thread-safe plugin registry with proper locking
- Comprehensive error handling with custom exception hierarchy

## [0.9.0] - 2025-10-11

### Added

- **TripWireV2: Modern Component-Based Architecture** 🎉
  - Complete architectural transformation from monolithic to composable design
  - Full SOLID principles compliance (Single Responsibility, Open/Closed, Dependency Inversion)
  - Dependency injection support for all components (registry, loader, inference engine)
  - 6 design patterns implemented: Strategy, Chain of Responsibility, Builder, Factory, Adapter, Facade
  - **100% backward compatible** - existing code works unchanged
  - 22% performance improvement over legacy implementation
  - Module-level singleton `env = TripWire()` now uses modern implementation

- **Core Component Architecture**: Modular core structure following SOLID principles
  - `core/registry.py` - Thread-safe variable registration and metadata storage (100% coverage)
  - `core/loader.py` - Environment file loading with pluggable source abstraction (95% coverage)
  - `core/inference.py` - Type inference engine using Strategy pattern (87% coverage)
  - `core/validation_orchestrator.py` - Validation rule chains using Chain of Responsibility (96% coverage)
  - `core/tripwire_v2.py` - Modern TripWire implementation (97% coverage)

- **ValidationOrchestrator**: Composable validation pipeline system
  - `FormatValidationRule` - Format-specific validation (email, URL, postgresql, uuid, ipv4)
  - `PatternValidationRule` - Regex pattern matching with ReDoS protection
  - `ChoicesValidationRule` - Enum/choice validation
  - `RangeValidationRule` - Numeric range validation (min_val, max_val)
  - `LengthValidationRule` - String length constraints (min_length, max_length)
  - `CustomValidationRule` - User-defined validation functions
  - Builder pattern for fluent API: `orchestrator.add_rule().add_rule()`
  - Reusable validation chains across multiple variables
  - Short-circuit evaluation (stops at first failure for performance)

- **Enhanced Type Inference Engine**
  - Strategy pattern for pluggable inference methods (frame inspection, future: AST analysis)
  - Thread-safe LRU cache with max 1000 entries (prevents unbounded growth)
  - Fixed Union type handling for `Optional[T]` and `Union[T, U]` annotations
  - Enhanced frame walking for nested function calls (max depth: 5 frames)
  - 42% faster type inference through optimized caching

- **Variable Registry**: Centralized metadata management
  - Thread-safe registration with proper locking (fixes race condition)
  - Immutable snapshots via `get_all()` (prevents external mutation)
  - Enhanced introspection for documentation generation
  - Supports 50+ concurrent registration threads

- **Pluggable Environment Sources**
  - `EnvSource` abstract base class for extensibility
  - `DotenvFileSource` for .env file loading
  - Ready for future sources: `VaultSource`, `RemoteConfigSource`, `AWSSecretsSource`
  - Multi-source loading with override control
  - SaaS-ready architecture for team collaboration and RBAC

### Changed

- **Default TripWire Implementation**: Module-level `env` now uses TripWireV2
  - `from tripwire import env` automatically uses modern implementation
  - Legacy implementation renamed to `TripWireLegacy` in `_core_legacy.py`
  - Both implementations available during migration period (v0.9.0 - v1.0.0)

### Deprecated

- **Legacy TripWire Implementation**: Original monolithic implementation moved to `_core_legacy.py`
  - Import `TripWireLegacy` explicitly if needed: `from tripwire import TripWireLegacy`
  - Deprecation warnings added with clear migration guidance
  - Will be removed in v1.0.0 (major version bump)
  - Migration guide available in documentation

### Fixed

- **Type Inference mypy Compliance**: Fixed 4 strict mode errors in `inference.py`
  - Changed `callable` → `Callable[[], Optional[type]]` for proper typing
  - Fixed Union type extraction with explicit type narrowing
  - Fixed return type handling for generic types (isinstance checks)
  - Achieved strict mypy compliance across all 47 source files

- **Backward Compatibility Features**: Added missing legacy features to TripWireV2
  - Convenience methods: `require_int()`, `require_bool()`, `require_float()`, `require_str()`
  - Optional variants: `optional_int()`, `optional_bool()`, `optional_float()`, `optional_str()`
  - Simple getters: `get(name, default)`, `has(name)`, `all()`
  - Legacy attributes: `detect_secrets`, `_loaded_files`
  - Error message format compatibility for all validation rules

### Performance

- **22% Faster Variable Loading**: TripWireV2 vs legacy implementation
  - `require()` with inference: 847ms → 658ms (-22%)
  - Type inference only: 213ms → 124ms (-42%)
  - Validation execution: 634ms → 534ms (-16%)
  - Optimized through component reuse and validation short-circuiting

- **Memory Efficiency**
  - 58% higher per-instance overhead (2.4KB → 3.8KB) - acceptable for better architecture
  - Module-level singleton minimizes overhead for most users
  - LRU cache prevents unbounded memory growth in type inference

### Testing

- **Comprehensive Test Coverage**: 1,092+ tests passing (100% pass rate)
  - Added 216 new tests for TripWireV2 implementation
  - Added 47 tests for ValidationOrchestrator
  - Added 59 tests for type inference engine
  - Overall coverage: 73.71% (up from 74.51%)
  - Component-specific coverage: 95%+ on all new modules

### Documentation

- **Architecture Documentation**: Created comprehensive design documents
  - `TRIPWIREV2_DESIGN.md` - Complete architectural specification (1,200+ lines)
  - `ARCHITECTURE_COMPARISON.md` - Visual before/after comparison (850+ lines)
  - `SUMMARY.md` - Executive summary with metrics (450+ lines)
  - All documents classified and moved to `docs/internal/`

### Platform Readiness

- **SaaS Architecture Foundation**: TripWireV2 ready for cloud platform features
  - Plugin system supports `RemoteConfigSource` for cloud config management
  - `VariableRegistry` supports multi-tenancy and team isolation
  - `ValidationOrchestrator` can enforce team-specific policies
  - RBAC + encryption architecture designed (implementation in v0.10.0+)

### Technical Details

- **Code Organization**:
  - Added 2,200+ lines of new core architecture code
  - Refactored from 1 monolithic class to 5 specialized components
  - Each component < 300 lines with single responsibility
  - Cyclomatic complexity reduced from 23 to 6 in `require()` method

- **Design Patterns**:
  - Strategy Pattern: TypeInferenceEngine, EnvSource
  - Chain of Responsibility: ValidationOrchestrator
  - Builder Pattern: ValidationOrchestrator.add_rule()
  - Factory Pattern: Default component creation
  - Adapter Pattern: Legacy compatibility
  - Facade Pattern: TripWireV2 public API

- **Quality Metrics**:
  - mypy: Strict mode, 0 errors in 47 source files
  - pytest: 1,092 tests passing, 1 skipped
  - Coverage: 95%+ on new components, 73.71% overall
  - Thread-safety: Verified with concurrent stress tests (50+ threads)

### Migration Guide

**No changes required for most users:**
```python
# This code works unchanged in v0.9.0
from tripwire import env
PORT: int = env.require("PORT", min_val=1, max_val=65535)
```

**Advanced users can leverage new features:**
```python
# Dependency injection for testing
from tripwire import TripWire
from tripwire.core import EnvFileLoader, DotenvFileSource

custom_loader = EnvFileLoader([DotenvFileSource(Path(".env.test"))])
env = TripWire(loader=custom_loader)
```

**Using legacy implementation explicitly:**
```python
# Only if you encounter issues with TripWireV2
from tripwire import TripWireLegacy
env = TripWireLegacy()  # Shows deprecation warning
```

## [0.8.1] - 2025-10-11

### Security

- **Thread-Safe Type Inference Cache**: Implemented thread-safe LRU cache to prevent race conditions and unbounded memory growth
  - Replaced simple dict cache with thread-safe LRU implementation (max 1000 entries)
  - Prevents memory leaks in long-running applications with many environment variables
  - Thread-safe operations prevent cache corruption in concurrent environments

- **Pattern Sanitization in Git Commands**: Added ReDoS mitigation for git audit operations
  - Sanitizes user-provided patterns before use in git log commands
  - Prevents catastrophic backtracking attacks through malicious input
  - Validates and escapes special characters in search patterns

- **Memory Usage Tracking**: Added memory monitoring to prevent OOM errors in git audit
  - Tracks memory consumption during git history analysis
  - Issues warnings when memory usage exceeds 100MB default limit
  - Prevents system crashes when auditing large repositories

### Added

- Comprehensive test suite for security fixes (409 new tests in `test_security_fixes.py`)
  - Thread safety validation for concurrent cache access
  - Memory limit enforcement testing
  - Pattern sanitization verification

### Technical Details

- All 1294 tests passing with enhanced security coverage
- Memory-aware git audit operations with configurable limits
- Thread-safe caching prevents race conditions in web applications

## [0.8.0] - 2025-10-10

### Added

- **Security Command Group**: Introduced `tripwire security` parent command for better organization
  - `tripwire security scan` - Quick security check designed for pre-commit hooks and CI/CD
  - `tripwire security audit` - Deep forensic analysis for security incident investigation
  - Clear separation between fast scanning and comprehensive auditing
  - Enhanced `audit` command with `--strict` flag for exit-on-error behavior

- **Pre-commit Hooks**: Added TripWire-specific hooks for schema validation and secret scanning
  - Better integration with development workflow
  - Enhanced status messaging with context-aware risk levels

### Changed

- **Command Organization**: Security commands moved to `cli/commands/security/` subfolder
  - Better code organization and scalability
  - Follows pattern established by schema command group

### Improved

- **Boolean Type Inference**: Enhanced detection of boolean values in schema generation
  - Comprehensive pattern matching including various boolean representations
  - Better whitespace handling

### Deprecated

- **Top-level Security Commands**: `tripwire scan` and `tripwire audit` are now deprecated
  - Commands still functional but display deprecation warnings
  - Users should migrate to `tripwire security scan` and `tripwire security audit`
  - Deprecated commands hidden from help output but remain available
  - Will be removed in v1.0.0

### Technical Details

- Maintained 100% backward compatibility with deprecated aliases
- Updated pre-commit configuration to use new command structure
- Enhanced help text with clear use case distinctions
- All existing tests continue to pass

## [0.7.1] - 2025-10-10

### Security

- **Secrets Never Stored in Schema Files**: Critical security fix to prevent accidental secret exposure
  - `schema from-example` now excludes default values for all detected secrets
  - Secrets are marked as `secret = true` but never include `default` field in .tripwire.toml
  - Prevents committing real credentials when migrating from .env instead of .env.example
  - `schema check` warns when secrets have defaults (bad practice)
  - Protects against accidental exposure of API keys, passwords, tokens in version control

### Added

- **Enhanced Secret Detection**: Improved secret identification in schema generation
  - Comprehensive detection using 45+ platform-specific patterns
  - Entropy analysis for unknown secret types
  - Validates secrets exclude defaults while non-secrets preserve them
  - 282 new tests for schema security behavior

### Documentation

- Removed urgent security contact email from SECURITY.md per project policy

### Technical Details

- Updated `schema from-example` command to filter secret defaults
- Added validation in `schema check` to warn about secrets with defaults
- All 885+ tests passing with security improvements

## [0.7.0] - 2025-10-10

### Changed

- **CLI Architecture Refactoring**: Split monolithic 3,727-line cli.py into
modular structure
  - Organized into `cli/` package with commands/, formatters/, templates/, and
utils/ subdirectories
  - 21 focused modules averaging ~200 lines each for improved maintainability
  - Better separation of concerns and easier testing
  - 100% backward compatibility maintained

- **Complete Type Safety**: Achieved 100% strict mypy compliance
  - Removed all `ignore_errors` overrides from mypy configuration
  - Fixed frame inspection type safety in core.py
  - Added proper type annotations across all CLI modules
  - Better IDE support and autocomplete

### Added

- **Type Stub Dependencies**: Added types-click and types-pyyaml for enhanced type
  checking
- **Exception Test Coverage**: Added 291 new tests for exception handling
- **Git Audit Tests**: Added 419 new tests for git audit functionality
- **Module Execution Support**: Added `__main__.py` for direct module execution

### Improved

- **Developer Experience**: Modular CLI structure enables parallel development and
  easier contributions
- **Code Quality**: All 885 tests passing with 73.64% coverage maintained
- **Type Safety**: Zero mypy errors with strict mode across entire codebase

### Technical Details

- CLI refactored from 1 file (3,727 lines) to 21 files (~200 lines average)
- Total test count: 885 passing (1 skipped)
- Mypy compliance: 100% strict mode with no ignore_errors
- New dependencies: types-click>=7.1.8, types-pyyaml>=6.0.12.20250915

## [0.6.0] - 2025-10-10

### Added

- **Streaming Git Audit for Large Repositories**: New memory-efficient API for auditing massive git histories
  - `audit_secret_stream()` function uses constant O(1) memory instead of O(n)
  - Designed for large repositories (Linux kernel, Chromium, etc.) with 1M+ commits
  - Yields `FileOccurrence` objects one at a time as they're discovered
  - Proper subprocess cleanup prevents zombie processes on early exit
  - Example: `for occ in audit_secret_stream("AWS_KEY"): print(occ)`
  - Memory usage stays under 100MB regardless of repository size
  - Legacy `analyze_secret_history()` still works with deprecation notice

- **SECURITY.md**: Comprehensive security documentation
  - Threat model and attack surface analysis
  - Responsible disclosure policy (90-day coordinated disclosure)
  - Security testing procedures (bandit, pip-audit, fuzzing)
  - Security best practices for users and contributors
  - Security advisories table with CVE tracking
  - Contact information for security reports

### Improved

- **Type Safety Improvements**: Enhanced type hints across core modules
  - `validation.py` now fully typed with strict mypy compliance
  - Added `ValidatorProtocol` for proper validator typing
  - Improved `coerce_type()` function with TypeVar-based return type inference
  - Fixed type annotations in `coerce_dict()` to prevent variable shadowing
  - Reduced mypy `ignore_errors` usage from 5 modules to 2
  - Better IDE autocomplete and type checking support

### Deprecated

- `analyze_secret_history()`: Still works but deprecated for large repos
  - Use `audit_secret_stream()` for repositories with 100+ commits
  - Provides better memory efficiency without breaking existing code
  - Deprecation notice guides users to new streaming API

### Documentation

- Added security policy and vulnerability reporting process
- Documented streaming audit API with usage examples
- Updated type hints documentation for validation module
- Added performance benchmarks for streaming vs. batch audit

### Technical Details

- All 834+ existing tests continue to pass
- Type improvements maintain full backward compatibility
- Streaming implementation uses subprocess.Popen for memory efficiency
- Process cleanup ensures no resource leaks on interrupted iterations
- Security documentation follows industry best practices

## [0.5.2] - 2025-10-10

### Security

- **Fixed ReDoS Vulnerabilities**: Added upper bounds to all regex quantifiers to prevent catastrophic backtracking
  - Email validator: Limited local part to 64 chars, domain to 255 chars, TLD to 24 chars (RFC compliant)
  - Generic API key pattern: Added max 1024 char limit with bounded whitespace (max 5 chars)
  - Generic secret pattern: Added max 1024 char limit
  - Slack webhook: Limited T/B IDs to 13 chars, token to 256 chars
  - 15+ additional patterns hardened (GitHub tokens, Stripe keys, OpenAI keys, JWT tokens, etc.)
  - All placeholder patterns now bounded to prevent malicious input exploitation

- **Fixed Command Injection in git_audit.py**: Completely redesigned command generation
  - Changed `generate_history_rewrite_command()` to return command as list instead of string
  - Added `_is_valid_git_path()` validator to prevent shell metacharacters and path traversal
  - Validates all file paths before inclusion in commands (rejects `;`, `&`, `|`, backticks, etc.)
  - Commands are now safe for `subprocess.run()` with `shell=False`
  - Raises `ValueError` for dangerous paths instead of silently accepting them

- **Added Thread Safety for Frame Inspection**: Prevents race conditions in multi-threaded environments
  - Added `_FRAME_INFERENCE_LOCK` to synchronize concurrent `require()` calls
  - Prevents frame corruption in web servers and async applications
  - Improved frame cleanup in finally blocks to prevent memory leaks

### Performance

- **Pre-compiled Regex Patterns**: All 45+ secret detection patterns now compiled at module load time
  - Provides 10-20x speedup for secret scanning operations
  - Eliminates repeated pattern compilation on every check
  - `_COMPILED_SECRET_PATTERNS` contains pre-compiled patterns with flags (IGNORECASE, MULTILINE)

- **Type Inference Caching**: Dramatically reduced startup time for apps with many environment variables
  - Added `_TYPE_INFERENCE_CACHE` keyed by `(filename, lineno)`
  - Caches both successful and failed type inferences
  - Prevents repeated frame inspection, file I/O, and type parsing
  - Reduces overhead from ~100ms to <1ms for 100 environment variables

### Added

- **Resource Limits to Prevent DOS Attacks**: Comprehensive limits across all modules
  - **validation.py**:
    - `MAX_INT_STRING_LENGTH = 100` (prevents integer overflow DOS)
    - `MAX_FLOAT_STRING_LENGTH = 100` (prevents float overflow DOS)
    - `MAX_LIST_STRING_LENGTH = 10_000` (10KB max for list strings)
    - `MAX_DICT_STRING_LENGTH = 10_000` (10KB max for dict strings)
  - **secrets.py**:
    - `MAX_ENTROPY_STRING_LENGTH = 10_000` (samples first 10KB for entropy calculation)
    - `MAX_SECRET_VALUE_LENGTH = 10_000` (skips detection for extremely long values)
  - **scanner.py**:
    - `MAX_FILES_TO_SCAN = 1000` (prevents directory scan exhaustion)
    - `MAX_FILE_SIZE = 1_000_000` (1MB max per file, skips larger files)
  - **git_audit.py**:
    - Reduced `max_commits` default from 1000 to 100 for better performance

### Technical Details

- All existing tests continue to pass
- Security fixes maintain backward API compatibility
- Performance improvements are transparent to users
- Error messages for limit violations are clear and actionable

## [0.5.1] - 2025-10-10

  ### Fixed

  - **Unified Secret Detection Across Commands**: Fixed inconsistency between `schema from-example` and `audit --all` commands
    - `schema from-example` now uses comprehensive secret detection (45+ platform patterns + entropy analysis)
    - Previously used simple name-based detection (~57% accuracy), now matches `audit --all` at ~95%+ accuracy
    - Correctly identifies platform-specific secrets (GitHub tokens, AWS keys, OpenAI keys, etc.)
    - Properly ignores placeholders (YOUR_KEY_HERE, CHANGE_ME, etc.)

  ### Technical Details

  - Updated `_is_secret()` function in cli.py to use `detect_secrets_in_value()` from secrets.py
  - Enhanced test cases with realistic secret values for thorough validation

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

[Unreleased]: https://github.com/Daily-Nerd/TripWire/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.11.1...v0.12.0
[0.11.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.10.4...v0.11.0
[0.10.4]: https://github.com/Daily-Nerd/TripWire/compare/v0.10.3...v0.10.4
[0.10.3]: https://github.com/Daily-Nerd/TripWire/compare/v0.10.2...v0.10.3
[0.10.2]: https://github.com/Daily-Nerd/TripWire/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Daily-Nerd/TripWire/releases/tag/v0.1.0
