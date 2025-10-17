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

## Environment Analysis

TripWire's analyze commands help enforce zero dead code policies in your CI/CD pipeline.

### Dead Code Detection

Prevent unused environment variables from accumulating:

```yaml
# GitHub Actions
- name: Check for dead variables
  run: tripwire analyze deadcode --strict
```

**What happens:**
- Scans codebase for environment variable declarations
- Identifies variables that are never used
- Exits with code 1 if dead code found (fails the build)
- Shows remediation steps in error output

**Exit behavior:**
- `0` - No dead variables found (pass)
- `1` - Dead variables detected (fail)

### GitHub Actions - Comprehensive Analysis

```yaml
# .github/workflows/env-analysis.yml
name: Environment Analysis

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  analyze-env-vars:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Check for dead variables (STRICT)
        run: tripwire analyze deadcode --strict
        id: deadcode
        continue-on-error: true

      - name: Generate usage report on failure
        if: steps.deadcode.outcome == 'failure'
        run: |
          tripwire analyze usage --format json --export usage-report.json
          cat usage-report.json | jq '.summary'

      - name: Upload usage report
        if: steps.deadcode.outcome == 'failure'
        uses: actions/upload-artifact@v3
        with:
          name: usage-report
          path: usage-report.json
          retention-days: 30

      - name: Fail build if dead code found
        if: steps.deadcode.outcome == 'failure'
        run: |
          echo "::error::Dead environment variables detected. See artifact for details."
          exit 1

      - name: Generate dependency diagram
        if: success()
        run: |
          tripwire analyze dependencies --top 15 --format mermaid --export deps.md

      - name: Upload dependency diagram
        if: success()
        uses: actions/upload-artifact@v3
        with:
          name: dependency-graph
          path: deps.md
          retention-days: 90
```

### GitLab CI - Dead Code Check

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - analyze
  - test

analyze:dead-variables:
  stage: analyze
  image: python:3.11

  before_script:
    - pip install tripwire-py

  script:
    # Fail fast on first dead variable
    - tripwire analyze deadcode --strict

  only:
    - merge_requests
    - main
    - develop

  allow_failure: false  # Block merges with dead code

analyze:usage-report:
  stage: analyze
  image: python:3.11

  before_script:
    - pip install tripwire-py

  script:
    # Generate full usage analysis
    - tripwire analyze usage --format json --export usage.json
    - cat usage.json | jq '.summary'

    # Generate dependency graph
    - tripwire analyze dependencies --top 20 --format mermaid --export deps.md

  artifacts:
    paths:
      - usage.json
      - deps.md
    expire_in: 1 month

  only:
    - schedules  # Run weekly on schedule
```

### CircleCI - Analysis Pipeline

```yaml
# .circleci/config.yml
version: 2.1

jobs:
  analyze-dead-code:
    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - run:
          name: Install TripWire
          command: pip install tripwire-py

      - run:
          name: Check for dead variables
          command: tripwire analyze deadcode --strict

      - run:
          name: Generate reports on failure
          command: |
            tripwire analyze usage --format json --export usage-report.json
            tripwire analyze deadcode --export dead-vars.json
          when: on_fail

      - store_artifacts:
          path: usage-report.json
          when: on_fail

      - store_artifacts:
          path: dead-vars.json
          when: on_fail

  generate-dependency-graph:
    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - run:
          name: Install TripWire
          command: pip install tripwire-py

      - run:
          name: Generate Mermaid diagram
          command: |
            tripwire analyze dependencies --top 15 --format mermaid --export deps.md

      - store_artifacts:
          path: deps.md
          destination: dependency-graph.md

workflows:
  version: 2
  analyze:
    jobs:
      - analyze-dead-code
      - generate-dependency-graph:
          requires:
            - analyze-dead-code
```

### Jenkins - Dead Code Gate

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

        stage('Dead Code Check') {
            steps {
                script {
                    def exitCode = sh(
                        script: 'tripwire analyze deadcode --strict',
                        returnStatus: true
                    )

                    if (exitCode != 0) {
                        // Generate detailed report
                        sh '''
                            tripwire analyze usage --format json --export usage-report.json
                            tripwire analyze deadcode --export dead-vars.json
                        '''

                        // Archive reports
                        archiveArtifacts artifacts: 'usage-report.json,dead-vars.json'

                        error("Dead environment variables detected. Check artifacts for details.")
                    }
                }
            }
        }

        stage('Generate Documentation') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    tripwire analyze dependencies --top 20 --format mermaid --export DEPENDENCIES.md
                '''
                archiveArtifacts artifacts: 'DEPENDENCIES.md'
            }
        }
    }

    post {
        success {
            echo "No dead environment variables found."
        }
        failure {
            emailext(
                subject: "Dead Code Detected in ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Dead environment variables were detected. Please review artifacts.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

### Pre-commit Hook - Local Enforcement

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      # Existing hooks...

      - id: tripwire-deadcode
        name: Check for dead environment variables
        entry: tripwire analyze deadcode --strict
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]

      - id: tripwire-usage
        name: Generate usage report
        entry: sh -c 'tripwire analyze usage --format json --export .tripwire-usage.json'
        language: system
        pass_filenames: false
        always_run: false  # Only on manual trigger
        stages: [manual]
```

**Usage:**

```bash
# Regular commits (runs deadcode check)
git commit -m "feat: add new feature"

# Generate usage report manually
pre-commit run tripwire-usage --hook-stage manual
```

---

### Example CI/CD Failure Output

When dead code is detected, developers see clear, actionable errors:

```
Run tripwire analyze deadcode --strict

╭────────────────────────────────────────╮
│ FAILED: Dead variable detected         │
╰────────────────────────────────────────╯

┌───────────────────────────────────────────────────────────┐
│ Variable: OLD_API_URL                                     │
│ Env Var: OLD_API_URL                                      │
│ Location: config.py:47                                    │
│                                                           │
│ Remediation:                                              │
│   1. Delete line 47 from config.py                        │
│   2. Remove OLD_API_URL from .env files                   │
│   3. Run: tripwire schema from-code --exclude-unused      │
│                                                           │
│ Note: 2 additional dead variable(s) found.                │
│       Run without --strict to see all.                    │
└───────────────────────────────────────────────────────────┘

Build failed due to dead code policy violation

Error: Process completed with exit code 1.
```

---

### Advanced: Trend Analysis

Track dead code metrics over time:

```yaml
# GitHub Actions - Monthly Analysis
name: Environment Metrics

on:
  schedule:
    - cron: '0 0 1 * *'  # First day of month

jobs:
  analyze-trends:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Generate monthly metrics
        run: |
          tripwire analyze usage --format json --export monthly-metrics.json

          # Extract summary
          cat monthly-metrics.json | jq '.summary' > summary.json

          # Add timestamp
          echo "{\"date\": \"$(date -I)\", \"metrics\": $(cat summary.json)}" > metrics-$(date -I).json

      - name: Upload metrics
        uses: actions/upload-artifact@v3
        with:
          name: monthly-metrics
          path: metrics-*.json
          retention-days: 365

      - name: Comment on main branch
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const summary = JSON.parse(fs.readFileSync('summary.json', 'utf8'));

            github.rest.repos.createCommitComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              commit_sha: context.sha,
              body: `## Environment Variable Metrics\n\n` +
                    `**Total Variables:** ${summary.total_variables}\n` +
                    `**Used Variables:** ${summary.used_variables}\n` +
                    `**Dead Variables:** ${summary.dead_variables}\n` +
                    `**Coverage:** ${summary.coverage_percentage}%\n\n` +
                    (summary.dead_variables > 0 ?
                      `⚠️ ${summary.dead_variables} dead variable(s) found. Consider cleanup.` :
                      `✅ No dead variables found!`)
            });
```

---

### Best Practices for Analysis in CI/CD

**1. Fail Fast on Dead Code**

```yaml
# Block PRs with dead code
- run: tripwire analyze deadcode --strict
```

**2. Generate Reports on Failure**

```yaml
- run: tripwire analyze deadcode --strict
  continue-on-error: true
  id: deadcode

- run: tripwire analyze usage --export report.json
  if: steps.deadcode.outcome == 'failure'
```

**3. Scheduled Deep Analysis**

```yaml
# Weekly comprehensive analysis
on:
  schedule:
    - cron: '0 0 * * 0'

jobs:
  deep-analysis:
    steps:
      - run: tripwire analyze usage --format json --export weekly.json
      - run: tripwire analyze dependencies --top 20 --format mermaid --export deps.md
```

**4. Documentation Generation**

```yaml
# Auto-update dependency diagrams
- name: Update docs
  if: github.ref == 'refs/heads/main'
  run: |
    tripwire analyze dependencies --top 15 --format mermaid --export docs/DEPENDENCIES.md
    git add docs/DEPENDENCIES.md
    git commit -m "docs: update dependency graph [skip ci]"
    git push
```

**5. Performance Monitoring**

```yaml
# Track analysis time
- name: Benchmark analysis
  run: |
    time tripwire analyze usage > /dev/null
    # Should complete in <5s for typical projects
```

---

### Troubleshooting CI/CD Analysis

**Issue: Analysis too slow**

```yaml
# Solution: Use deadcode command (faster)
- run: tripwire analyze deadcode --strict  # Fast
# Instead of:
# - run: tripwire analyze usage --strict   # Slower
```

**Issue: False positives blocking PRs**

```yaml
# Solution: Use manual review mode
- run: tripwire analyze deadcode --export dead-vars.json
- run: |
    # Review and fail only if count > threshold
    count=$(cat dead-vars.json | jq 'length')
    if [ $count -gt 5 ]; then
      echo "Too many dead variables: $count"
      exit 1
    fi
```

**Issue: Missing dynamic usage**

```yaml
# Solution: Document limitations
- run: |
    echo "Note: Dynamic variable access (getattr, eval) not detected."
    echo "Review dead-vars.json manually before removing."
    tripwire analyze deadcode --export dead-vars.json
```

---

**[Back to Guides](README.md)**
