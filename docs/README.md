# TripWire Documentation

Welcome to the TripWire documentation! Find everything you need to master environment variable management with TripWire.

---

## Quick Links

- 🚀 **[Quick Start](getting-started/quick-start.md)** - Get started in 5 minutes
- 📖 **[Installation](getting-started/installation.md)** - Install TripWire
- 🎓 **[Your First Project](getting-started/your-first-project.md)** - Step-by-step tutorial
- 📚 **[Main README](../README.md)** - Project overview

---

## Getting Started

New to TripWire? Start here:

- **[Installation](getting-started/installation.md)** - Install and verify setup
- **[Quick Start](getting-started/quick-start.md)** - 5-minute introduction
- **[Your First Project](getting-started/your-first-project.md)** - Complete tutorial

---

## Guides

### Essential Workflows

- **[CLI Reference](guides/cli-reference.md)** - Complete CLI command reference
  - Core commands (init, generate, check, sync, diff)
  - Secret management (scan, audit)
  - Schema commands (init, validate, check, import, generate-example)
  - Migration tools (schema from-example)

- **[Configuration as Code](guides/configuration-as-code.md)** - Schema-based configuration
  - `.tripwire.toml` schemas
  - Environment-specific defaults
  - CI/CD integration
  - Auto-generate .env.example

- **[Secret Management](guides/secret-management.md)** - Detect and audit secrets
  - 45+ secret type detection
  - Git history scanning
  - Timeline and blast radius analysis
  - Remediation workflows

### Integration Guides

- **[Framework Integration](guides/framework-integration.md)** - Use with popular frameworks
  - FastAPI
  - Django
  - Flask
  - Starlette, Quart

- **[Multi-Environment](guides/multi-environment.md)** - Manage dev/staging/production
  - File structure recommendations
  - Loading strategies
  - CI/CD secrets management

- **[CI/CD Integration](guides/ci-cd-integration.md)** - Automate validation
  - GitHub Actions
  - GitLab CI
  - CircleCI, Travis CI, Jenkins
  - Pre-commit hooks

---

## Reference

Technical API and feature documentation:

- **[Python API](reference/api.md)** - Complete TripWire API
  - Core methods (`require`, `optional`)
  - Typed methods (`require_int`, `optional_bool`, etc.)
  - Configuration methods (`load`, `load_files`)
  - Custom validators (`@validator` decorator)

- **[Validators](reference/validators.md)** - Built-in and custom validators
  - Format validators (email, url, postgresql, uuid, ipv4)
  - Type validators (str, int, float, bool, list, dict)
  - Constraint validators (range, length, pattern, choices)
  - Custom validator examples

- **[Type Inference](reference/type-inference.md)** - Automatic type detection (v0.4.0+)
  - How type inference works
  - Supported types
  - Optional[T] handling
  - Fallback behavior

- **[Configuration](reference/configuration.md)** - `[tool.tripwire]` settings (v0.4.1+)
  - All configuration options
  - Environment-specific overrides
  - Command-line precedence

---

## Advanced Topics

Deep dives for power users:

- **[Custom Validators](advanced/custom-validators.md)** - Write your own validation logic
  - Basic and complex validators
  - Error messages and testing
  - Reusable validator libraries

- **[Git Audit Deep Dive](advanced/git-audit.md)** - Secret leak detection internals
  - How git audit works
  - Timeline construction
  - Branch impact analysis
  - Remediation strategies

- **[Type System](advanced/type-system.md)** - Type inference deep dive
  - Frame inspection details
  - Type coercion rules
  - Performance considerations
  - Edge cases

- **[Troubleshooting](advanced/troubleshooting.md)** - Common issues and solutions
  - Installation problems
  - Validation errors
  - Type inference issues
  - Performance optimization

---

## Documentation by Feature

### Import-Time Validation

- [Quick Start - Basic Usage](getting-started/quick-start.md#core-concepts)
- [API Reference - require() method](reference/api.md#envrequire)
- [Your First Project - Testing Validation](getting-started/your-first-project.md#step-7-test-validation-break-something)

### Type Coercion

- [Type System Deep Dive](advanced/type-system.md)
- [Type Inference](reference/type-inference.md)
- [Validators Reference](reference/validators.md#built-in-type-validators)

### Secret Detection

- [Secret Management Guide](guides/secret-management.md)
- [Git Audit Deep Dive](advanced/git-audit.md)
- [CLI Reference - security scan command](guides/cli-reference.md#tripwire-scan)
- [CLI Reference - security audit command](guides/cli-reference.md#tripwire-audit)

### Schema-Based Configuration

- [Configuration as Code](guides/configuration-as-code.md)
- [CLI Reference - Schema Commands](guides/cli-reference.md#schema-commands)

### Multi-Environment Support

- [Multi-Environment Guide](guides/multi-environment.md)
- [Framework Integration](guides/framework-integration.md#environment-specific-configs)

---

## Documentation by Use Case

### "I want to get started"
→ [Installation](getting-started/installation.md) → [Quick Start](getting-started/quick-start.md) → [Your First Project](getting-started/your-first-project.md)

### "I need to integrate with my framework"
→ [Framework Integration](guides/framework-integration.md) → [Multi-Environment](guides/multi-environment.md)

### "I found a secret in git history"
→ [Secret Management](guides/secret-management.md) → [Git Audit](advanced/git-audit.md)

### "I want to automate validation in CI"
→ [CI/CD Integration](guides/ci-cd-integration.md) → [CLI Reference](guides/cli-reference.md)

### "I need custom validation logic"
→ [Custom Validators](advanced/custom-validators.md) → [Validators Reference](reference/validators.md)

### "Something's not working"
→ [Troubleshooting](advanced/troubleshooting.md)

---

## Version-Specific Documentation

### What's New

- **[v0.10.1](../CHANGELOG.md#0101)** - Advanced URL and DateTime validation features
- **[v0.10.0](../CHANGELOG.md#0100)** - Plugin system for cloud secret managers (Vault, AWS, Azure, Remote)
- **[v0.9.0](../CHANGELOG.md#090)** - TripWireV2 modern architecture (22% faster)
- **[v0.8.0](../CHANGELOG.md#080)** - Security command group reorganization
- **[v0.4.1](../CHANGELOG.md#041)** - Tool configuration, schema from-example command
- **[v0.4.0](../CHANGELOG.md#040)** - Type inference, diff command, unified config abstraction
- **[v0.3.0](../CHANGELOG.md#030)** - Configuration as Code (TOML schemas)
- **[v0.2.0](../CHANGELOG.md#020)** - Git audit with timeline and remediation

### Migration Guides

- [Migrate to v0.4.1](guides/cli-reference.md#tripwire-schema from-example) - Legacy `.env.example` to schema
- [Type Inference Migration](reference/type-inference.md) - Adopting automatic type inference

---

## External Resources

### Project Links

- **GitHub:** [Daily-Nerd/TripWire](https://github.com/Daily-Nerd/TripWire)
- **PyPI:** [tripwire-py](https://pypi.org/project/tripwire-py/)
- **Changelog:** [CHANGELOG.md](../CHANGELOG.md)
- **Contributing:** [CONTRIBUTING.md](../CONTRIBUTING.md)

### Support

- **Issues:** [Report a bug](https://github.com/Daily-Nerd/TripWire/issues/new)
- **Discussions:** [Community discussions](https://github.com/Daily-Nerd/TripWire/discussions)

---

## Documentation Metrics

**Last Updated:** 2025-10-14

| Section | Files | Status |
|---------|-------|--------|
| Getting Started | 4 files | ✅ Complete |
| Guides | 7 files | ✅ Complete |
| Reference | 5 files | ✅ Complete |
| Advanced | 5 files | ✅ Complete |
| **Total** | **21 files** | **✅ Complete** |

---

## Contributing to Documentation

Want to improve TripWire's documentation?

### Quick Fixes

For typos or small improvements:
1. Edit the file directly on GitHub
2. Submit a pull request

### Major Changes

For restructuring or new content:
1. Open an issue first to discuss
2. See [CONTRIBUTING.md](../CONTRIBUTING.md)
3. Follow the [documentation style guide](#documentation-style-guide)

### Documentation Style Guide

**Writing Style:**
- Use active voice
- Write in present tense
- Keep sentences short and scannable
- Explain "why" not just "what"
- Include code examples for every concept

**Code Examples:**
- Must be syntactically correct
- Should be copy-pasteable
- Use type annotations
- Include comments for clarity

**Structure:**
- Start with overview/purpose
- Provide quick example
- Deep dive into details
- End with next steps/related topics

---

## Search Tips

Can't find what you need? Try these strategies:

### By Topic
- **Installation:** [Getting Started](getting-started/)
- **CLI Commands:** [CLI Reference](guides/cli-reference.md)
- **Python API:** [API Reference](reference/api.md)
- **Validators:** [Validators Reference](reference/validators.md)
- **Secrets:** [Secret Management](guides/secret-management.md)
- **Types:** [Type System](advanced/type-system.md)

### By Error Message
- "EnvironmentError" → [Troubleshooting](advanced/troubleshooting.md#validation-errors)
- "Type coercion failed" → [Type System](advanced/type-system.md#type-coercion)
- "Pattern mismatch" → [Validators Reference](reference/validators.md#pattern-validation-regex)
- "command not found" → [Troubleshooting](advanced/troubleshooting.md#installation-issues)

### By Feature Version
- Type inference → [Type Inference (v0.4.0)](reference/type-inference.md)
- Diff command → [CLI Reference - diff (v0.4.0)](guides/cli-reference.md#tripwire-diff)
- Tool configuration → [Configuration (v0.4.1)](reference/configuration.md)
- Schema migration → [CLI Reference - schema from-example (v0.4.1)](guides/cli-reference.md#tripwire-schema from-example)

---

**TripWire** - Environment variables that just work. 🎯

*Stop debugging production crashes. Start shipping with confidence.*
