# Contributing to TripWire

Thank you for your interest in contributing to TripWire! We welcome contributions from the community and are grateful for your help in making TripWire better.

This guide will help you get started with contributing to TripWire, whether you're fixing bugs, adding features, improving documentation, or developing plugins.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Development Commands](#development-commands)
- [Areas for Contribution](#areas-for-contribution)
- [Code of Conduct](#code-of-conduct)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - TripWire requires Python 3.11 or higher
- **git** - For version control
- **uv** (optional but recommended) - Fast Python package installer
  ```bash
  # Install uv (optional)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Fork and Clone the Repository

1. **Fork the repository** on GitHub by clicking the "Fork" button at [github.com/Daily-Nerd/TripWire](https://github.com/Daily-Nerd/TripWire)

2. **Clone your fork** to your local machine:
   ```bash
   git clone https://github.com/YOUR_USERNAME/TripWire.git
   cd TripWire
   ```

3. **Add the upstream repository** as a remote:
   ```bash
   git remote add upstream https://github.com/Daily-Nerd/TripWire.git
   ```

---

## Development Setup

### 1. Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

Install TripWire in editable mode with development dependencies:

```bash
# Using uv (recommended - faster)
uv pip install -e ".[dev]"

# OR using pip
pip install -e ".[dev]"
```

This installs:
- TripWire package in editable mode
- Development tools (pytest, black, ruff, mypy)
- Pre-commit hooks
- Code quality tools (bandit, safety, pip-audit)

### 3. Install Pre-commit Hooks

Pre-commit hooks ensure code quality before commits:

```bash
pre-commit install
```

This automatically runs linting, formatting, and validation checks before each commit.

### 4. Verify Installation

```bash
# Test the CLI
tripwire --version

# Run tests
pytest

# Check code style
ruff check .
black . --check
mypy src/tripwire
```

---

## Code Style Guidelines

TripWire follows strict code quality standards to ensure maintainability and consistency.

### Formatting with Black

- **Line length:** 100 characters
- **Target Python version:** 3.11+
- Black is configured in `pyproject.toml`

```bash
# Format code
black .

# Check formatting
black . --check
```

### Linting with Ruff

Ruff enforces code quality rules:

```bash
# Lint code
ruff check .

# Auto-fix issues
ruff check . --fix
```

**Key rules:**
- Import sorting (isort)
- Unused imports/variables
- Complexity checks
- Security patterns (bandit-like)
- Modern Python idioms (pyupgrade)

### Type Checking with Mypy

TripWire uses **strict type checking** with mypy:

```bash
# Type check
mypy src/tripwire
```

**Important:** All new code must include type annotations. Configuration is in `pyproject.toml` under `[tool.mypy]`.

### Docstring Standards

Use Google-style docstrings:

```python
def validate_url(url: str, allow_http: bool = False) -> tuple[bool, str]:
    """Validate URL format and protocol.

    Args:
        url: The URL to validate
        allow_http: Whether to allow HTTP URLs (default: False)

    Returns:
        A tuple of (is_valid, error_message)

    Raises:
        ValueError: If URL is empty

    Examples:
        >>> validate_url("https://example.com")
        (True, "")
        >>> validate_url("http://example.com", allow_http=True)
        (True, "")
    """
```

---

## Testing Requirements

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=tripwire --cov-report=html

# Run specific test file
pytest tests/test_validation.py

# Run specific test function
pytest tests/test_validation.py::test_email_validator

# Exclude slow tests
pytest -m "not slow"

# Run in parallel (faster)
pytest -n auto
```

### Test Coverage Requirements

- **Minimum coverage:** 80%
- **Target coverage:** 90%+
- Coverage report is generated in `htmlcov/index.html`

### Writing Tests

All new features and bug fixes must include tests:

```python
# tests/test_my_feature.py
import pytest
from tripwire import env

def test_new_validator():
    """Test the new validator works correctly."""
    # Arrange
    expected_result = True

    # Act
    result = validate_something("test")

    # Assert
    assert result == expected_result

def test_new_validator_error():
    """Test the validator raises appropriate errors."""
    with pytest.raises(ValueError, match="Invalid input"):
        validate_something("")
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.slow
def test_large_git_repository():
    """Test that takes more than 1 second."""
    pass

@pytest.mark.integration
def test_full_workflow():
    """Test that requires external dependencies."""
    pass
```

---

## Pull Request Process

### 1. Create a Feature Branch

Branch naming conventions:
- **Features:** `feature/description`
- **Bug fixes:** `fix/description`
- **Documentation:** `docs/description`
- **Performance:** `perf/description`

```bash
git checkout -b feature/add-json-validator
```

### 2. Make Your Changes

- Write clean, well-documented code
- Add tests for new features
- Update documentation as needed
- Follow the code style guidelines

### 3. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Run all checks
pre-commit run --all-files

# Or run individually:
pytest                    # Tests
ruff check .             # Linting
black . --check          # Formatting
mypy src/tripwire       # Type checking
```

### 4. Commit Your Changes

Follow **Conventional Commits** format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(validation): add JSON schema validator"
git commit -m "fix(cli): handle missing .env file gracefully"
git commit -m "docs(readme): update installation instructions"
```

### 5. Push to Your Fork

```bash
git push origin feature/add-json-validator
```

### 6. Create a Pull Request

1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. Fill out the PR template with:
   - Clear description of changes
   - Related issue numbers (if any)
   - Testing performed
   - Screenshots (if UI changes)

### 7. Respond to Feedback

- Address review comments promptly
- Push additional commits to the same branch
- Mark conversations as resolved when addressed

### PR Checklist

Before submitting, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Code is linted (`ruff check .`)
- [ ] Type checks pass (`mypy src/tripwire`)
- [ ] Test coverage is maintained or improved
- [ ] Documentation is updated
- [ ] Commit messages follow conventional commits format
- [ ] Pre-commit hooks are passing

---

## Development Commands

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tripwire --cov-report=html

# Run specific test file
pytest tests/test_validation.py

# Run with coverage report in terminal
pytest --cov=tripwire --cov-report=term-missing

# Exclude slow tests
pytest -m "not slow"

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Lint with ruff
ruff check .

# Auto-fix ruff issues
ruff check . --fix

# Format with black
black .

# Check formatting without changing files
black . --check

# Type check with mypy
mypy src/tripwire

# Run all quality checks
pre-commit run --all-files
```

### CLI Testing

Test CLI commands during development:

```bash
# Core commands
python -m tripwire.cli init
python -m tripwire.cli generate
python -m tripwire.cli check
python -m tripwire.cli sync
python -m tripwire.cli diff .env .env.example

# Security commands (v0.8.0+)
python -m tripwire.cli security scan --strict
python -m tripwire.cli security audit --all

# Schema commands (v0.5.0+)
python -m tripwire.cli schema from-code
python -m tripwire.cli schema from-example
python -m tripwire.cli schema to-example
python -m tripwire.cli schema validate

# Plugin commands (v0.10.0+)
python -m tripwire.cli plugin search
python -m tripwire.cli plugin install vault
python -m tripwire.cli plugin list
```

### Building

```bash
# Build package
python -m build

# Install locally to test
pip install -e .

# Create distribution
python -m build --wheel
```

---

## Areas for Contribution

We welcome contributions in many areas:

### 1. Bug Fixes

- Check [open issues](https://github.com/Daily-Nerd/TripWire/issues) labeled `bug`
- Reproduce the bug locally
- Write a failing test
- Fix the bug
- Ensure test passes

### 2. New Features

Popular feature requests:
- New format validators (JSON Schema, XML, etc.)
- Additional secret detection patterns
- Plugin development (cloud secret managers)
- IDE integrations
- Documentation improvements

### 3. New Validators

Add built-in validators in `src/tripwire/validation.py`:

```python
def validate_json_schema(value: str, schema: dict) -> tuple[bool, str]:
    """Validate JSON against a JSON schema."""
    # Implementation
    pass

# Register the validator
register_validator("json_schema", validate_json_schema)
```

### 4. Plugin Development

Create plugins for cloud secret managers:
- GCP Secret Manager
- 1Password Connect
- Bitwarden Secrets Manager
- Doppler
- Infisical

See [Plugin Development Guide](docs/guides/plugin-development.md) for details.

### 5. Documentation Improvements

Documentation is critical:
- Fix typos and grammar
- Add examples and tutorials
- Improve API documentation
- Create video walkthroughs
- Translate documentation

### 6. Test Coverage

Help improve test coverage:
- Add tests for edge cases
- Write integration tests
- Add performance benchmarks
- Test error conditions

### 7. Examples and Tutorials

Create examples for:
- Framework integrations (FastAPI, Django, Flask)
- CI/CD workflows (GitHub Actions, GitLab CI)
- Docker deployments
- Kubernetes configurations
- Real-world use cases

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background, identity, or experience level.

### Expected Behavior

- **Be respectful and inclusive** - Value diverse perspectives
- **Be constructive** - Provide helpful feedback
- **Be patient** - Help others learn and grow
- **Be professional** - Maintain a positive tone
- **Give credit** - Acknowledge contributions

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Personal or political attacks
- Publishing private information without permission
- Unwelcome sexual attention or advances

### Reporting Issues

If you experience or witness unacceptable behavior, please report it to the maintainers at [GitHub Issues](https://github.com/Daily-Nerd/TripWire/issues) or via email.

### Enforcement

Violations of the Code of Conduct may result in:
1. Warning
2. Temporary ban from the project
3. Permanent ban from the project

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) as our Code of Conduct.

---

## Getting Help

### Community

- **Discord**: [discord.gg/eDwuVY68](https://discord.gg/eDwuVY68) - Ask questions and get help
- **GitHub Discussions**: [Discussions](https://github.com/Daily-Nerd/TripWire/discussions) - Longer-form discussions
- **GitHub Issues**: [Issues](https://github.com/Daily-Nerd/TripWire/issues) - Bug reports and feature requests

### Documentation

- **Docs**: [docs/README.md](docs/README.md) - Complete documentation
- **CLI Reference**: [docs/guides/cli-reference.md](docs/guides/cli-reference.md) - All CLI commands
- **API Reference**: [docs/reference/api.md](docs/reference/api.md) - Python API documentation

### Contact

- **GitHub**: [@Daily-Nerd](https://github.com/Daily-Nerd)
- **Project**: [github.com/Daily-Nerd/TripWire](https://github.com/Daily-Nerd/TripWire)

---

## License

By contributing to TripWire, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Recognition

All contributors are recognized in:
- GitHub Contributors list
- CHANGELOG.md for significant contributions
- Release notes

Thank you for contributing to TripWire! 🎯

---

**TripWire** - Environment variables that just work.

*Stop debugging production crashes. Start shipping with confidence.*
