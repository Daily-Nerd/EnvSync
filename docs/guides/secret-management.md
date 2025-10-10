[Home](../README.md) / [Guides](README.md) / Secret Management

# Secret Management Guide

Learn how to detect, audit, and remediate secret leaks with TripWire.

---

## Table of Contents

- [Overview](#overview)
- [Secret Detection](#secret-detection)
- [Git History Scanning](#git-history-scanning)
- [Git Audit with Timeline](#git-audit-with-timeline)
- [Remediation Workflows](#remediation-workflows)
- [Best Practices](#best-practices)
- [Supported Secret Types](#supported-secret-types)

---

## Overview

TripWire provides comprehensive secret management capabilities:

1. **Detection** - Identify 45+ types of secrets in `.env` files
2. **Scanning** - Search git history for leaked secrets
3. **Auditing** - Generate timeline and impact analysis
4. **Remediation** - Step-by-step instructions to fix leaks

---

## Secret Detection

### Quick Scan

Check your `.env` file for secrets:

```bash
tripwire scan
```

Output if secrets found:

```
Scanning for secrets...

Scanning .env file...
⚠️  Found 3 potential secret(s) in .env

┌───────────────────┬─────────────────┬──────────┐
│ Variable          │ Type            │ Severity │
├───────────────────┼─────────────────┼──────────┤
│ AWS_SECRET_ACCESS_│ AWS Secret Key  │ CRITICAL │
│ KEY               │                 │          │
│ STRIPE_SECRET_KEY │ Stripe API Key  │ CRITICAL │
│ DATABASE_PASSWORD │ Generic Password│ CRITICAL │
└───────────────────┴─────────────────┴──────────┘

✓ .env is in .gitignore (safe)
```

### Detection Patterns

TripWire uses two detection methods:

**1. Pattern Matching** - 45+ platform-specific patterns:
```python
# AWS
AWS_SECRET_ACCESS_KEY=your-aws-secret-key-here

# GitHub
GITHUB_TOKEN=your-github-token-here

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret-key-here
```

**2. Entropy Analysis** - Detects unknown high-entropy strings:
```python
# Generic secrets with high randomness
CUSTOM_TOKEN=kH9d3L2mP7nQ4rT8vW1xY5zA3bC6eF9g
```

---

## Git History Scanning

### Basic Scan

Scan last 100 commits for secrets:

```bash
tripwire scan
```

### Deep Scan

Scan more commits for thorough check:

```bash
tripwire scan --depth 1000
```

### CI/CD Integration

Fail build if secrets found:

```bash
tripwire scan --strict
```

Example GitHub Actions workflow:

```yaml
name: Secret Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history

      - name: Install TripWire
        run: pip install tripwire-py

      - name: Scan for secrets
        run: tripwire scan --strict --depth 1000
```

---

## Git Audit with Timeline

The flagship feature - comprehensive secret leak analysis.

### Audit Specific Secret

```bash
tripwire audit AWS_SECRET_ACCESS_KEY
```

Output:

```
Secret Leak Timeline for: AWS_SECRET_ACCESS_KEY
══════════════════════════════════════════════════════════════════════

Timeline:

📅 2024-09-15
   Commit: abc123de - Initial setup
   Author: @alice <alice@company.com>
   📁 .env:15

📅 2024-09-20
   Commit: def456gh - Update config
   Author: @bob <bob@company.com>
   📁 config/.env.prod:22

⚠️  Still in git history (as of HEAD)
   Affects 47 commit(s)
   Found in 2 file(s)
   Branches: origin/main, origin/develop

╭──────────────── 🚨 Security Impact ────────────────╮
│ Severity: CRITICAL                                 │
│ Exposure: PUBLIC repository                        │
│ Duration: 16 days                                  │
│ Commits affected: 47                               │
│ Files affected: 2                                  │
│ Branches affected: 2                               │
╰────────────────────────────────────────────────────╯

🔧 Remediation Steps:

1. Rotate the secret IMMEDIATELY
   Urgency: CRITICAL
   Generate a new secret and update all systems.

   aws iam create-access-key --user-name <username>

   ⚠️  Do not skip this step - the secret is exposed!

2. Remove from git history (using git-filter-repo)
   Urgency: HIGH
   Rewrite git history to remove the secret from 47 commit(s).

   git filter-repo --path .env --invert-paths --force

   ⚠️  This will rewrite git history. Coordinate with your team!

3. Notify team about git history rewrite
   Urgency: HIGH
   Everyone needs to re-clone or reset their repositories.

4. Update all systems using the old secret
   Urgency: CRITICAL
   The old secret must be revoked after rotation.

5. Review access logs for unauthorized usage
   Urgency: HIGH
   Check if the leaked secret was used maliciously.
```

### Auto-Detect All Secrets

Automatically detect and audit all secrets in `.env`:

```bash
tripwire audit --all
```

Output:

```
🔍 Auto-detecting secrets in .env file...

⚠️  Found 3 potential secret(s) in .env file

Detected Secrets
┌──────────────────────┬─────────────────┬──────────┐
│ Variable             │ Type            │ Severity │
├──────────────────────┼─────────────────┼──────────┤
│ AWS_SECRET_ACCESS_KEY│ AWS Secret Key  │ CRITICAL │
│ STRIPE_SECRET_KEY    │ Stripe API Key  │ CRITICAL │
│ DATABASE_PASSWORD    │ Generic Password│ CRITICAL │
└──────────────────────┴─────────────────┴──────────┘

════════════════════════════════════════════════════════════
Auditing: AWS_SECRET_ACCESS_KEY
════════════════════════════════════════════════════════════

[... full audit for AWS_SECRET_ACCESS_KEY ...]

════════════════════════════════════════════════════════════
Auditing: STRIPE_SECRET_KEY
════════════════════════════════════════════════════════════

[... full audit for STRIPE_SECRET_KEY ...]

════════════════════════════════════════════════════════════
Auditing: DATABASE_PASSWORD
════════════════════════════════════════════════════════════

[... full audit for DATABASE_PASSWORD ...]

📊 Secret Leak Blast Radius
═════════════════════════════════════════════

🔍 Repository Secret Exposure
├─ 🔴 🚨 AWS_SECRET_ACCESS_KEY (47 occurrence(s))
│  ├─ Branches affected:
│  │  ├─ origin/main (47 total commits)
│  │  └─ origin/develop (47 total commits)
│  └─ Files affected:
│     ├─ .env (15 commits)
│     └─ config/.env.prod (32 commits)
├─ 🟡 ⚠️ STRIPE_SECRET_KEY (12 occurrence(s))
│  ├─ Branches affected:
│  │  └─ origin/main (12 total commits)
│  └─ Files affected:
│     └─ .env (12 commits)
└─ 🟢 DATABASE_PASSWORD (0 occurrence(s))
   └─ ✓ Never committed to git

📈 Summary
╭────────────────────────────────────────╮
│ Leaked: 2                              │
│ Clean: 1                               │
│ Total commits affected: 59             │
│ Remediation urgency: CRITICAL          │
╰────────────────────────────────────────╯
```

### Exact Value Matching

For more accurate results, provide the actual secret value:

```bash
tripwire audit API_KEY --value "sk-proj-1234567890abcdef"
```

This searches for the exact value rather than just the variable name.

### JSON Output

For integration with security tools:

```bash
tripwire audit --all --json > audit_results.json
```

---

## Remediation Workflows

### Workflow 1: Secret Never Committed

**Situation:** Secret detected in `.env` but not in git history.

**Steps:**

1. Verify `.env` is gitignored:
   ```bash
   git check-ignore .env
   ```

2. If not gitignored, add immediately:
   ```bash
   echo ".env" >> .gitignore
   git add .gitignore
   git commit -m "Add .env to gitignore"
   ```

3. No rotation needed - secret never exposed.

---

### Workflow 2: Secret Committed Recently

**Situation:** Secret in last few commits on feature branch.

**Steps:**

1. **Rotate the secret immediately:**
   ```bash
   # Example for AWS
   aws iam create-access-key --user-name your-username
   ```

2. **Remove from recent commits (if not pushed to main):**
   ```bash
   # Interactive rebase to remove commits
   git rebase -i HEAD~5

   # Or amend if just last commit
   git commit --amend
   ```

3. **Force push (coordinate with team):**
   ```bash
   git push --force-with-lease
   ```

4. **Update `.env` with new secret.**

---

### Workflow 3: Secret in Main Branch History

**Situation:** Secret in main branch, multiple commits affected.

**Steps:**

1. **Rotate the secret IMMEDIATELY:**
   ```bash
   # Generate new secret
   # Update all systems to use new secret
   ```

2. **Coordinate with team:**
   ```
   Send notification:
   - Git history will be rewritten
   - Everyone must re-clone or reset
   - Provide timeline
   ```

3. **Rewrite git history:**

   **Option A: Using git-filter-repo (recommended):**
   ```bash
   # Install git-filter-repo
   pip install git-filter-repo

   # Remove file from history
   git filter-repo --path .env --invert-paths --force
   ```

   **Option B: Using BFG Repo-Cleaner:**
   ```bash
   # Download BFG
   # Run BFG
   java -jar bfg.jar --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```

4. **Force push to remote:**
   ```bash
   git push --force --all
   git push --force --tags
   ```

5. **Notify team to re-clone:**
   ```bash
   # All team members must:
   cd ..
   rm -rf project-name
   git clone git@github.com:org/project-name.git
   ```

6. **Revoke old secret:**
   ```bash
   # Example for AWS
   aws iam delete-access-key --access-key-id OLD_KEY_ID --user-name your-username
   ```

7. **Review access logs:**
   - Check for unauthorized usage of leaked secret
   - Audit access patterns during exposure period

---

### Workflow 4: Public Repository Exposure

**Situation:** Secret exposed in public GitHub repository.

**Steps:**

1. **IMMEDIATELY rotate the secret** - assume compromised.

2. **Make repository private temporarily** (if possible):
   ```
   GitHub → Settings → Danger Zone → Change visibility
   ```

3. **Follow Workflow 3** to clean git history.

4. **Review security:**
   - Check AWS CloudTrail / equivalent logs
   - Look for suspicious API calls
   - Review billing for unexpected usage

5. **Incident response:**
   - Document the incident
   - Assess impact
   - Implement preventive measures

6. **Re-publish repository** only after:
   - Secret rotated
   - History cleaned
   - Logs reviewed
   - No suspicious activity detected

---

## Best Practices

### Prevention

**1. Use `.gitignore` from the start:**
```bash
tripwire init  # Automatically sets up .gitignore
```

**2. Pre-commit hooks:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tripwire-scan
        name: Scan for secrets
        entry: tripwire scan --strict
        language: system
        pass_filenames: false
```

**3. CI/CD validation:**
```yaml
# GitHub Actions
- name: Secret scan
  run: tripwire scan --strict --depth 1000
```

**4. Mark secrets in code:**
```python
API_KEY: str = env.require("API_KEY", secret=True)
```

### Detection

**1. Regular audits:**
```bash
# Weekly security check
tripwire audit --all
```

**2. Automated monitoring:**
```bash
# Scheduled job
tripwire audit --all --json > audit_$(date +%Y%m%d).json
```

**3. New repository checks:**
```bash
# When cloning/forking
tripwire scan --depth 0  # Scan all history
```

### Response

**1. Have rotation procedures documented:**
- AWS: How to rotate access keys
- Stripe: How to roll API keys
- Database: Password change procedure

**2. Emergency contacts:**
- Security team
- DevOps team
- Service providers (AWS support, etc.)

**3. Communication templates:**
- Team notification about history rewrite
- Incident report format
- Post-mortem template

---

## Supported Secret Types

### Cloud Providers (9)
- AWS (Access Key ID, Secret Access Key)
- Azure (Subscription Key, Storage Account Key)
- Google Cloud (API Key, Service Account)
- DigitalOcean (Access Token, Spaces Key)
- Heroku (API Key)
- Alibaba Cloud (Access Key)
- IBM Cloud (API Key)
- Oracle Cloud (Auth Token)

### CI/CD Platforms (10)
- GitHub (Personal Access Token, OAuth Token)
- GitLab (Personal Access Token, Runner Token)
- CircleCI (API Token)
- Travis CI (API Token)
- Jenkins (API Token)
- Bitbucket (App Password)
- Docker Hub (Access Token)
- Terraform Cloud (API Token)
- Azure DevOps (PAT)
- JFrog (API Key)

### Communication (6)
- Slack (Webhook URL, Bot Token, User Token)
- Discord (Bot Token, Webhook)
- Twilio (Account SID, Auth Token)
- SendGrid (API Key)
- Mailgun (API Key)
- Postmark (Server Token)

### Payment Providers (6)
- Stripe (Secret Key, Publishable Key)
- PayPal (Client ID, Client Secret)
- Square (Access Token)
- Shopify (API Key, Password)
- Coinbase (API Key)
- Braintree (Access Token)

### Databases (3)
- MongoDB (Connection String)
- Redis (Connection String)
- Firebase (Admin SDK Key)

### Monitoring & Services (11)
- Datadog (API Key, App Key)
- New Relic (License Key, API Key)
- PagerDuty (API Key, Integration Key)
- Sentry (DSN, Auth Token)
- Algolia (API Key, Admin Key)
- Cloudflare (API Token, Global API Key)
- Mapbox (Access Token)
- Auth0 (Client Secret)
- Segment (Write Key)
- Mixpanel (API Secret)
- Amplitude (API Key)

### Package Managers (2)
- NPM (Auth Token)
- PyPI (API Token)

### Generic Patterns (10)
- PASSWORD / PASS
- SECRET / SECRET_KEY
- TOKEN / AUTH_TOKEN
- API_KEY / APIKEY
- ENCRYPTION_KEY
- PRIVATE_KEY
- CREDENTIALS
- JWT_SECRET
- OAUTH_TOKEN
- ACCESS_TOKEN

### Entropy-Based Detection
- High-entropy strings (>4.5 bits/char)
- Base64-encoded secrets
- Hex-encoded secrets
- Custom tokens

**Total: 45+ secret types detected**

---

## Advanced Topics

For more in-depth information, see:

- **[Git Audit Deep Dive](../advanced/git-audit.md)** - Technical details of audit feature
- **[Custom Validators](../advanced/custom-validators.md)** - Create custom secret patterns
- **[CI/CD Integration](ci-cd-integration.md)** - Automated secret scanning

---

**[Back to Guides](README.md)**
