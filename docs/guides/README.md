[Home](../README.md) / Guides

# TripWire Guides

Step-by-step guides for common tasks and workflows.

---

## Essential Guides

### CLI & Configuration

- **[CLI Reference](cli-reference.md)** - Complete reference for all TripWire CLI commands
  - Core commands (init, generate, check, sync, diff)
  - Secret management (scan, audit)
  - Schema commands (init, validate, check, import, generate-example)
  - Migration tools

- **[Configuration as Code](configuration-as-code.md)** - Schema-based validation with `.tripwire.toml`
  - Schema creation and management
  - Environment-specific defaults
  - CI/CD integration
  - Auto-generate .env.example from schema

### Security

- **[Secret Management](secret-management.md)** - Detect and audit secret leaks
  - 45+ secret type detection
  - Git history scanning
  - Timeline and impact analysis
  - Remediation workflows

### Integration

- **[Framework Integration](framework-integration.md)** - Use TripWire with popular frameworks
  - FastAPI
  - Django
  - Flask
  - Starlette, Quart
  - Best practices and patterns

- **[Multi-Environment](multi-environment.md)** - Manage dev/staging/production
  - File structure recommendations
  - Loading strategies
  - CI/CD secrets management
  - Best practices

- **[CI/CD Integration](ci-cd-integration.md)** - Automate validation in pipelines
  - GitHub Actions
  - GitLab CI
  - CircleCI, Travis CI, Jenkins
  - Pre-commit hooks

---

## Quick Navigation

**New to TripWire?**
Start with [Getting Started](../getting-started/README.md)

**Need API details?**
See [Reference Documentation](../reference/README.md)

**Advanced topics?**
Check [Advanced Guides](../advanced/README.md)

---

**[Back to Documentation Home](../README.md)**
