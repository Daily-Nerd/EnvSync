# TripWire Makefile
# Common development tasks

.PHONY: help install install-dev test test-cov lint format type-check security clean build release setup-dev

# Default target
help:
	@echo "TripWire Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install package in production mode"
	@echo "  install-dev  Install package in development mode with dev dependencies"
	@echo "  setup-dev    Set up complete development environment"
	@echo ""
	@echo "Testing:"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  test-fast    Run tests without coverage (faster)"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         Run linting (ruff)"
	@echo "  format       Format code (black)"
	@echo "  type-check   Run type checking (mypy)"
	@echo "  check-all    Run all quality checks"
	@echo ""
	@echo "Security:"
	@echo "  security     Run security scans"
	@echo "  secret-scan  Run secret detection"
	@echo ""
	@echo "Build & Release:"
	@echo "  build        Build package"
	@echo "  release      Create a release (usage: make release VERSION=1.0.0)"
	@echo "  release-rc   Create a prerelease (usage: make release-rc VERSION=1.0.0-rc1)"
	@echo ""
	@echo "Utilities:"
	@echo "  clean        Clean build artifacts"
	@echo "  docs         Generate documentation"
	@echo "  pre-commit   Run pre-commit hooks on all files"

# Installation
install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

setup-dev:
	python scripts/setup-dev.py

# Testing
test:
	pytest

test-cov:
	pytest --cov=tripwire --cov-report=term-missing --cov-report=html

test-fast:
	pytest --no-cov

# Code Quality
lint:
	ruff check .

format:
	black .

type-check:
	mypy src/tripwire

check-all: lint format type-check test
	@echo "✅ All checks passed!"

# Security
security:
	bandit -r src/tripwire -f json -o bandit-report.json
	safety check --json --output safety-report.json
	pip-audit --format=json --output=pip-audit-report.json
	@echo "Security reports generated: bandit-report.json, safety-report.json, pip-audit-report.json"

secret-scan:
	tripwire scan --strict

# Build & Release
build:
	python -m build

release:
ifndef VERSION
	@echo "Error: VERSION is required. Usage: make release VERSION=1.0.0"
	@exit 1
endif
	python scripts/release.py $(VERSION)

release-rc:
ifndef VERSION
	@echo "Error: VERSION is required. Usage: make release-rc VERSION=1.0.0-rc1"
	@exit 1
endif
	python scripts/release.py $(VERSION) --prerelease

# Utilities
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	tripwire docs --format markdown > docs/generated.md
	tripwire docs --format html > docs/generated.html
	tripwire docs --format json > docs/generated.json
	@echo "Documentation generated in docs/"

pre-commit:
	pre-commit run --all-files

pre-commit-update:
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate

# Development workflow
dev-setup: install-dev setup-dev
	@echo "✅ Development environment ready!"

ci-local: check-all security
	@echo "✅ All CI checks passed locally!"

# Release workflow
release-check: clean check-all security build
	@echo "✅ Ready for release!"

# Quick development cycle
dev: format lint test
	@echo "✅ Development cycle complete!"

# Full test suite (what CI runs)
ci: clean install-dev check-all security build
	@echo "✅ Full CI suite passed locally!"
