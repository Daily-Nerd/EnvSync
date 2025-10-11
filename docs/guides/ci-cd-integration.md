[Home](../README.md) / [Guides](README.md) / CI/CD Integration

# CI/CD Integration Guide

TripWire pre-commit hooks work seamlessly in both local development and CI/CD environments **without any configuration changes**. This guide shows you how to leverage TripWire's intelligent `--strict` mode for zero-config CI/CD integration.

## Quick Start

TripWire's `--strict` flag provides intelligent behavior that adapts to context:

- **CI/CD**: Passes if `.env` missing (correctly not committed) ✅
- **Local dev**: Validates `.env` if present ✅
- **Pre-commit**: Skips `.gitignore`'d files ✅

**One command works everywhere:**

```yaml
# Works in GitHub Actions, GitLab CI, Jenkins, locally, etc.
tripwire schema validate --strict
```

---

## The Problem (Solved)

Traditional pre-commit hooks fail in CI/CD pipelines because `.env` files don't exist there (and shouldn't - they contain real secrets).

**Before TripWire 0.7.2**, you needed workarounds:

```yaml
# Old workaround - DON'T DO THIS
- run: if [ -f .env ]; then tripwire schema validate; fi
```

**With TripWire >= 0.7.2**, just use `--strict`:

```yaml
# New approach - CLEAN & SIMPLE
- run: tripwire schema validate --strict
```

The same command works in local dev, pre-commit hooks, AND all CI/CD platforms.

---

## GitHub Actions

### Basic Validation

```yaml
# .github/workflows/validate-env.yml
name: Validate Environment

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Validate schema (CI/CD compatible)
        run: tripwire schema validate --strict

      - name: Check .env.example is up to date
        run: tripwire schema to-example --check

      - name: Scan for secrets
        run: tripwire security scan --strict
```

### Complete Workflow

```yaml
# .github/workflows/tripwire.yml
name: TripWire Checks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  tripwire-checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for audit

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Validate .env.example is current
        run: tripwire generate --check
        continue-on-error: false

      - name: Validate schema syntax
        run: tripwire schema check
        if: hashFiles('.tripwire.toml') != ''

      - name: Scan for secrets in .env
        run: tripwire scan --strict

      - name: Audit git history for leaks
        run: |
          # Create dummy .env for secret detection
          cat > .env << EOF
          AWS_SECRET_ACCESS_KEY=placeholder
          DATABASE_URL=placeholder
          API_KEY=placeholder
          EOF

          # Run audit
          tripwire audit --all --json > audit_results.json

          # Check for leaks
          if jq -e '.secrets[] | select(.status == "LEAKED")' audit_results.json; then
            echo "::error::Secret leak detected!"
            exit 1
          fi

      - name: Upload audit results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: tripwire-audit
          path: audit_results.json
```

---

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - test
  - deploy

tripwire:validate:
  stage: validate
  image: python:3.11
  before_script:
    - pip install tripwire-py
  script:
    - tripwire generate --check
    - tripwire scan --strict
    - tripwire schema check
  only:
    - merge_requests
    - main
    - develop

tripwire:audit:
  stage: validate
  image: python:3.11
  before_script:
    - pip install tripwire-py
  script:
    - |
      cat > .env << EOF
      AWS_SECRET_ACCESS_KEY=placeholder
      DATABASE_URL=placeholder
      EOF
    - tripwire audit --all --json > audit_results.json
  artifacts:
    reports:
      dotenv: audit_results.json
    expire_in: 1 week
  only:
    - schedules  # Run on schedule
```

---

## CircleCI

```yaml
# .circleci/config.yml
version: 2.1

executors:
  python-executor:
    docker:
      - image: cimg/python:3.11

jobs:
  validate-env:
    executor: python-executor
    steps:
      - checkout
      - run:
          name: Install TripWire
          command: pip install tripwire-py

      - run:
          name: Validate .env.example
          command: tripwire generate --check

      - run:
          name: Scan for secrets
          command: tripwire scan --strict

workflows:
  version: 2
  build-and-test:
    jobs:
      - validate-env
```

---

## Travis CI

```yaml
# .travis.yml
language: python
python:
  - "3.11"

install:
  - pip install tripwire-py

script:
  - tripwire generate --check
  - tripwire scan --strict
  - tripwire validate

notifications:
  email:
    on_failure: always
```

---

## Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'pip install tripwire-py'
            }
        }

        stage('Validate Environment') {
            steps {
                sh 'tripwire generate --check'
                sh 'tripwire validate'
            }
        }

        stage('Security Scan') {
            steps {
                sh 'tripwire scan --strict'
                sh 'tripwire audit --all --json > audit.json'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'audit.json', allowEmptyArchive: true
        }
    }
}
```

---

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tripwire-generate
        name: Update .env.example
        entry: tripwire generate --check
        language: system
        pass_filenames: false
        always_run: true

      - id: tripwire-scan
        name: Scan for secrets
        entry: tripwire scan --strict
        language: system
        pass_filenames: false
        files: '\.env.*$'

      - id: tripwire-schema
        name: Validate schema
        entry: tripwire schema check
        language: system
        pass_filenames: false
        files: '\.tripwire\.toml$'
```

**Install:**
```bash
pip install pre-commit
pre-commit install
```

---

## Best Practices

### 1. Always Use `--strict` in CI

```yaml
# Fail pipeline if issues found
- run: tripwire generate --check  # Fails if .env.example outdated
- run: tripwire scan --strict     # Fails if secrets detected
- run: tripwire validate --strict # Fails if validation errors
```

### 2. Use Full Git History for Audits

```yaml
- uses: actions/checkout@v3
  with:
    fetch-depth: 0  # Clone full history
```

### 3. Cache Dependencies

```yaml
# GitHub Actions
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-tripwire

# GitLab CI
cache:
  paths:
    - .cache/pip
```

### 4. Run on Schedule

```yaml
# GitHub Actions - weekly security audit
on:
  schedule:
    - cron: '0 0 * * 0'  # Sunday midnight
```

### 5. Store Results

```yaml
- name: Upload audit results
  uses: actions/upload-artifact@v3
  with:
    name: tripwire-audit
    path: audit_results.json
    retention-days: 90
```

---

## Common Workflows

### Pre-Deployment Validation

```yaml
deploy:
  stage: deploy
  before_script:
    - pip install tripwire-py
  script:
    # Validate environment before deploying
    - |
      cat > .env << EOF
      DATABASE_URL=$DATABASE_URL
      SECRET_KEY=$SECRET_KEY
      API_KEY=$API_KEY
      EOF
    - tripwire validate --strict
    - tripwire schema validate --environment production --strict

    # Deploy if validation passes
    - ./deploy.sh
```

### Multi-Environment Testing

```yaml
test:
  strategy:
    matrix:
      environment: [development, staging, production]
  steps:
    - name: Test ${{ matrix.environment }}
      run: |
        cp .env.${{ matrix.environment }} .env
        tripwire validate
        pytest
```

---

**[Back to Guides](README.md)**
