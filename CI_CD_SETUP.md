# CI/CD Setup for EnvSync

This document explains the complete CI/CD setup for EnvSync, including automated testing, security scanning, and PyPI publishing.

## 🚀 Quick Start

### 1. Set up GitHub Secrets
Follow the instructions in [.github/SECRETS_SETUP.md](.github/SECRETS_SETUP.md) to configure:
- `PYPI_API_TOKEN` - For publishing to PyPI
- `TEST_PYPI_API_TOKEN` - For testing releases
- `CODECOV_TOKEN` - For coverage reporting (optional)

### 2. Set up Development Environment
```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
python scripts/setup-dev.py

# Or manually:
pre-commit install
pre-commit install --hook-type commit-msg
```

### 3. Make Your First Release
```bash
# Test release (prerelease)
python scripts/release.py 0.1.0-rc1 --prerelease

# Production release
python scripts/release.py 0.1.0
```

## 📋 Workflows Overview

### 1. CI Workflow (`.github/workflows/ci.yml`)
**Triggers**: Push to main/develop, Pull Requests

**What it does**:
- Tests on Python 3.9-3.12 across Ubuntu, Windows, macOS
- Runs linting (Ruff, Black, MyPy)
- Type checking with MyPy
- Test coverage reporting
- Integration tests
- Performance tests
- Documentation generation

**Duration**: ~10-15 minutes

### 2. Security Workflow (`.github/workflows/security.yml`)
**Triggers**: Push to main/develop, Pull Requests, Daily schedule

**What it does**:
- Secret detection using EnvSync's own scanner
- Dependency vulnerability scanning (Safety, pip-audit)
- Code security analysis (Bandit, Semgrep)
- License compliance checking
- Generates comprehensive security reports

**Duration**: ~5-10 minutes

### 3. Release Workflow (`.github/workflows/release.yml`)
**Triggers**: Version tags (`v*.*.*`), Manual dispatch

**What it does**:
- Validates version format and git status
- Builds Python package (wheel + source)
- Uploads to Test PyPI for prereleases
- Uploads to PyPI for stable releases
- Creates GitHub releases with changelog
- Uploads release assets

**Duration**: ~5-8 minutes

## 🔧 Development Workflow

### Daily Development
```bash
# 1. Make your changes
git checkout -b feature/my-feature

# 2. Pre-commit hooks run automatically
git add .
git commit -m "feat: add new feature"

# 3. Push triggers CI
git push origin feature/my-feature

# 4. Create PR (triggers CI + Security scans)
# 5. Merge to main (triggers all workflows)
```

### Release Process
```bash
# 1. Ensure you're on main branch
git checkout main
git pull origin main

# 2. Run tests locally
pytest
ruff check .
black --check .
mypy src/envsync

# 3. Create release
python scripts/release.py 1.0.0

# 4. GitHub Actions handles the rest:
#    - Builds package
#    - Uploads to PyPI
#    - Creates GitHub release
```

## 🛡️ Security Features

### Automated Security Scanning
- **Secret Detection**: 45+ platform-specific patterns
- **Dependency Scanning**: Safety + pip-audit
- **Code Analysis**: Bandit + Semgrep
- **License Compliance**: pip-licenses
- **Git History Audit**: EnvSync's own audit tools

### Security Reports
All security scans generate reports that are:
- Uploaded as GitHub Actions artifacts
- Available for download from the Actions tab
- Include detailed findings and recommendations

## 📊 Quality Gates

### Required for Merge
- [ ] All tests pass
- [ ] Linting passes (Ruff, Black, MyPy)
- [ ] No security vulnerabilities
- [ ] Code coverage maintained
- [ ] Pre-commit hooks pass

### Required for Release
- [ ] All CI checks pass
- [ ] Security scans clean
- [ ] Version format valid
- [ ] Git working directory clean
- [ ] Package builds successfully

## 🚨 Troubleshooting

### Common Issues

#### 1. Tests Failing
```bash
# Run tests locally
pytest --cov=envsync --cov-report=term-missing

# Check specific test
pytest tests/test_core.py::TestRequireMethod::test_require_existing_variable -v
```

#### 2. Linting Errors
```bash
# Fix automatically
ruff check . --fix
black .

# Check specific file
ruff check src/envsync/core.py
```

#### 3. Type Checking Errors
```bash
# Run mypy
mypy src/envsync

# Check specific file
mypy src/envsync/core.py
```

#### 4. Security Scan Failures
```bash
# Run security scans locally
bandit -r src/envsync
safety check
pip-audit
```

#### 5. Release Failures
- Check GitHub Secrets are set correctly
- Verify version format (must be `X.Y.Z`)
- Ensure tag doesn't already exist
- Check PyPI permissions

### Getting Help
1. Check GitHub Actions logs for detailed error messages
2. Review the specific workflow that failed
3. Run the failing command locally
4. Check the troubleshooting section in [SECRETS_SETUP.md](.github/SECRETS_SETUP.md)

## 🔄 Workflow Customization

### Adding New Tests
1. Add test files to `tests/`
2. Follow naming convention: `test_*.py`
3. Use pytest fixtures from `conftest.py`
4. Tests run automatically in CI

### Adding New Linting Rules
1. Update `.pre-commit-config.yaml`
2. Modify `pyproject.toml` for tool configuration
3. Add to CI workflow if needed

### Adding New Security Scans
1. Add tool to `pyproject.toml` dev dependencies
2. Update security workflow
3. Add to pre-commit hooks if desired

### Customizing Release Process
1. Modify `scripts/release.py`
2. Update release workflow
3. Add new validation steps

## 📈 Monitoring and Metrics

### Coverage Tracking
- Codecov integration for coverage reports
- Coverage badges in README
- Coverage trends over time

### Security Monitoring
- Daily security scans
- Vulnerability alerts
- License compliance tracking

### Performance Monitoring
- Performance tests in CI
- Build time tracking
- Resource usage monitoring

## 🎯 Best Practices

### Code Quality
- Write tests for all new features
- Maintain high test coverage
- Use type hints throughout
- Follow PEP 8 and project style

### Security
- Never commit secrets
- Use pre-commit hooks
- Regular dependency updates
- Security scan all PRs

### Releases
- Use semantic versioning
- Test prereleases first
- Document breaking changes
- Keep changelog updated

### CI/CD
- Keep workflows fast
- Use caching where possible
- Fail fast on errors
- Provide clear error messages

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Publishing Guide](https://packaging.python.org/guides/publishing-package-data-via-github-actions/)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 📞 Support

- GitHub Issues: [Create an issue](https://github.com/Daily-Nerd/EnvSync/issues)
- Discussions: [GitHub Discussions](https://github.com/Daily-Nerd/EnvSync/discussions)
- Documentation: [Read the docs](https://envsync.dev)
