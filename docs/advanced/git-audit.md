# Git Audit - Secret Leak Timeline

The **Secret Leak Timeline** is TripWire's flagship feature for detecting and remediating secret leaks in git history. It provides a complete forensic timeline showing exactly when, where, and by whom a secret was committed to git.

## Why This Matters

When secrets are accidentally committed to git, simply removing them from the current codebase isn't enough. The secret remains in git history forever, accessible to anyone who clones the repository. This is especially critical for public repositories.

**Real-world impact:**
- GitHub scans for secrets and notifies repository owners
- Attackers actively scrape git history for credentials
- A single leaked AWS key can result in thousands of dollars in fraudulent charges
- Compliance regulations (SOC 2, PCI-DSS) require immediate secret rotation

## Quick Start

```bash
# Auto-detect and audit ALL secrets in .env file (recommended)
tripwire audit --all

# Audit a specific secret by name
tripwire audit AWS_SECRET_ACCESS_KEY

# Audit with the actual secret value (more accurate)
tripwire audit API_KEY --value "sk-proj-abc123..."

# Output as JSON for CI/CD integration
tripwire audit DATABASE_URL --json
tripwire audit --all --json

# Analyze more commits
tripwire audit SECRET_KEY --max-commits 5000
```

## How It Works

The audit feature performs the following analysis:

1. **Git History Scanning**: Uses `git log -G` to efficiently find all commits containing the secret pattern
2. **Timeline Construction**: Builds a chronological timeline of when the secret appeared
3. **File Analysis**: Identifies all files that ever contained the secret
4. **Branch Detection**: Determines which branches are affected
5. **Public Repository Detection**: Checks if the repository has public remotes (GitHub, GitLab, etc.)
6. **Severity Assessment**: Calculates risk level based on exposure context
7. **Remediation Generation**: Provides step-by-step instructions to fix the leak

## Output Format

### Human-Readable Output

The default output provides a beautiful, easy-to-understand timeline:

```
Secret Leak Timeline for: AWS_SECRET_ACCESS_KEY
══════════════════════════════════════════════════════════════════════

Timeline:

📅 2024-09-15
   Commit: abc123de - Initial setup
   Author: @alice <alice@company.com>
   📁 .env:15
   📁 config/settings.py:42

📅 2024-09-18
   Commit: def456gh - Fix configuration bug
   Author: @bob <bob@company.com>
   📁 config/settings.py:42
   📁 backend/config.py:28

⚠️  Still in git history (as of HEAD)
   Affects 47 commit(s)
   Found in 3 file(s)
   Branches: origin/main, origin/develop

╭──────────────── 🚨 Security Impact ────────────────╮
│ Severity: CRITICAL                                 │
│ Exposure: PUBLIC repository                        │
│ Duration: 16 days                                  │
│ Commits affected: 47                               │
│ Files affected: 3                                  │
╰────────────────────────────────────────────────────╯

🔧 Remediation Steps:

1. Rotate the secret IMMEDIATELY
   Urgency: CRITICAL
   The secret is compromised and must be replaced.

   aws iam create-access-key --user-name <username>

   ⚠️  Do not skip this step - the secret is exposed!

2. Remove from git history
   Urgency: HIGH
   Rewrite git history to remove the secret from 47 commit(s).

   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env config/settings.py' HEAD

   ⚠️  This rewrites history - coordinate with your team first!

[... additional steps ...]
```

### JSON Output

For automation and CI/CD integration, use `--json`:

```json
{
  "secret_name": "AWS_SECRET_ACCESS_KEY",
  "status": "LEAKED",
  "first_seen": "2024-09-15T10:30:00Z",
  "last_seen": "2024-10-01T14:22:00Z",
  "exposure_duration_days": 16,
  "commits_affected": 47,
  "files_affected": [".env", "config/settings.py", "backend/config.py"],
  "is_public": true,
  "is_current": true,
  "severity": "CRITICAL",
  "branches_affected": ["origin/main", "origin/develop"],
  "remediation_steps": [...]
}
```

## Command Options

### `--all` - Auto-detect All Secrets (RECOMMENDED)

Automatically detect all secrets in your .env file and audit each one.

```bash
tripwire audit --all
```

**What it does:**
1. Scans your .env file for potential secrets using 45+ detection patterns
2. Detects generic credentials (PASSWORD, TOKEN, SECRET, ENCRYPTION_KEY)
3. Audits git history for each detected secret
4. Generates a combined visual timeline showing blast radius
5. Provides individual detailed audits for each secret

**Example output:**
```bash
$ tripwire audit --all

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

📊 Secret Leak Blast Radius
═════════════════════════════════════════════

🔍 Repository Secret Exposure
├─ 🔴 🚨 AWS_SECRET_ACCESS_KEY (47 occurrence(s))
│  ├─ Branches affected:
│  │  ├─ origin/main (47 total commits)
│  │  └─ origin/develop (47 total commits)
│  └─ Files affected:
│     └─ .env
├─ 🟡 ⚠️ STRIPE_SECRET_KEY (12 occurrence(s))
│  ├─ Branches affected:
│  │  └─ origin/main (12 total commits)
│  └─ Files affected:
│     └─ .env
└─ 🟢 DATABASE_PASSWORD (0 occurrence(s))

📈 Summary
╭────────────────────────────────────────╮
│ Leaked: 2                              │
│ Clean: 1                               │
│ Total commits affected: 59             │
╰────────────────────────────────────────╯

[... followed by detailed audit for each secret ...]
```

**When to use:**
- First time auditing a repository
- Comprehensive security check
- CI/CD pipelines
- After inheriting a project
- Regular security audits

**JSON output:**
```bash
$ tripwire audit --all --json

{
  "total_secrets_found": 3,
  "secrets": [
    {
      "variable_name": "AWS_SECRET_ACCESS_KEY",
      "secret_type": "AWS Secret Key",
      "severity": "critical",
      "status": "LEAKED",
      "first_seen": "2024-09-15T10:30:00Z",
      "last_seen": "2024-10-01T14:22:00Z",
      "commits_affected": 47,
      "files_affected": [".env"],
      "branches_affected": ["origin/main", "origin/develop"],
      "is_public": true,
      "is_current": true
    }
  ]
}
```

### `secret_name` - Audit Specific Secret

The name of the environment variable to search for.

```bash
tripwire audit AWS_SECRET_ACCESS_KEY
```

The tool searches for patterns like:
- `AWS_SECRET_ACCESS_KEY=value`
- `AWS_SECRET_ACCESS_KEY: value`
- `"AWS_SECRET_ACCESS_KEY": "value"`

**When to use:**
- Auditing a specific known secret
- Re-checking after remediation
- Focused investigation

### `--value`

Provide the actual secret value for more accurate detection.

```bash
tripwire audit API_KEY --value "sk-proj-abc123def456"
```

**When to use:**
- When you want pinpoint accuracy
- When the variable name might be generic (e.g., `TOKEN`, `KEY`)
- When you're unsure if the secret was committed

**Security note:** The secret value is never logged or stored. It's only used for pattern matching.

### `--max-commits`

Maximum number of commits to analyze (default: 1000).

```bash
tripwire audit SECRET_KEY --max-commits 5000
```

**Performance notes:**
- 1000 commits typically covers 6-12 months of history
- Analyzing 5000+ commits may take 30+ seconds
- For very large repositories, consider using `--value` for faster searching

### `--json`

Output results as JSON for programmatic processing.

```bash
tripwire audit DATABASE_URL --json
```

**Use cases:**
- CI/CD pipelines
- Security automation
- Custom alerting systems
- Compliance reporting

## Severity Levels

The audit assigns severity based on multiple factors:

### CRITICAL
- Secret found in **public repository** with commits
- Immediate action required
- High risk of exploitation

### HIGH
- Secret currently in git history (HEAD)
- Multiple commits affected
- Active security risk

### MEDIUM
- Secret removed from HEAD but still in history
- Moderate number of commits affected
- Lower immediate risk

### LOW
- Secret found in very few commits
- Private repository only
- Minimal exposure

## Remediation Steps

The audit automatically generates context-aware remediation steps:

### 1. Rotate the Secret (CRITICAL)

**Always the first step.** Generate a new secret and update all systems.

```bash
# AWS Example
aws iam create-access-key --user-name myuser

# GitHub Example
# Visit https://github.com/settings/tokens

# Database Example
# Change password in database and update connection strings
```

**Important:** Rotate BEFORE removing from git history. The old secret is already compromised.

### 2. Remove from Git History (HIGH)

Use git filter-branch to rewrite history:

```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env config/settings.py' HEAD
```

**Warnings:**
- This changes commit hashes
- All team members must re-clone or rebase
- Coordinate with your team first
- Consider using [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) for large repos

### 3. Force Push (HIGH/MEDIUM)

Update remote repositories:

```bash
git push origin --force --all
git push origin --force --tags
```

**Critical steps:**
1. Notify all team members BEFORE force pushing
2. Have team members stash changes
3. Force push
4. Team members re-clone or reset to new history

### 4. Update .gitignore (MEDIUM)

Prevent future accidents:

```bash
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

### 5. Use a Secret Manager (MEDIUM)

Move to proper secret management:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name MySecret \
  --secret-string "my-secret-value"

# HashiCorp Vault
vault kv put secret/myapp/config \
  api_key="my-secret-value"

# Cloud Provider Options
# - AWS Secrets Manager
# - Google Cloud Secret Manager
# - Azure Key Vault
# - HashiCorp Vault
```

### 6. Install Pre-commit Hooks (LOW)

Prevent future leaks:

```bash
# Using detect-secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

## Best Practices

### Before Committing

1. **Never commit `.env` files**
   ```bash
   # Always in .gitignore
   .env
   .env.local
   .env.*.local
   ```

2. **Use environment variable templates**
   ```bash
   # Commit .env.example instead
   cp .env .env.example
   # Remove actual values from .env.example
   ```

3. **Enable pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### After Detection

1. **Act immediately** - Don't wait
2. **Rotate first** - Always rotate before cleaning
3. **Communicate** - Tell your team before force pushing
4. **Verify** - Run `tripwire audit` again after cleanup
5. **Learn** - Update processes to prevent recurrence

### For Organizations

1. **Regular audits** - Run weekly scans
2. **CI/CD integration** - Block PRs with secrets
3. **Secret scanning** - Use GitHub secret scanning
4. **Training** - Educate developers
5. **Secret managers** - Mandate use in production

## CI/CD Integration

### GitHub Actions

```yaml
name: Secret Audit

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Need full history

      - name: Install tripwire
        run: pip install tripwire

      - name: Audit all secrets
        run: |
          # Create temporary .env for auto-detection
          cat > .env << EOF
          AWS_SECRET_ACCESS_KEY=placeholder
          DATABASE_URL=placeholder
          API_KEY=placeholder
          EOF

          # Run comprehensive audit
          tripwire audit --all --json > audit_results.json

          # Check if any secrets leaked
          if jq -e '.secrets[] | select(.status == "LEAKED")' audit_results.json; then
            echo "::error::Secret leak detected in git history!"
            jq . audit_results.json
            exit 1
          fi
```

### GitLab CI

```yaml
secret_audit:
  stage: security
  script:
    - pip install tripwire
    - |
      # Create temporary .env for auto-detection
      cat > .env << EOF
      AWS_SECRET_ACCESS_KEY=placeholder
      DATABASE_URL=placeholder
      API_KEY=placeholder
      EOF

      # Run comprehensive audit
      tripwire audit --all --json | tee audit_all_results.json

      # Check for any leaks
      if jq -e '.secrets[] | select(.status == "LEAKED")' audit_all_results.json; then
        echo "Secret leak detected!"
        exit 1
      fi
  artifacts:
    paths:
      - audit_all_results.json
    when: always
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Secret Audit') {
            steps {
                script {
                    // Create temporary .env for auto-detection
                    sh '''
                        cat > .env << EOF
                        AWS_SECRET_ACCESS_KEY=placeholder
                        DATABASE_URL=placeholder
                        API_KEY=placeholder
                        EOF
                    '''

                    // Run comprehensive audit
                    def result = sh(
                        script: "tripwire audit --all --json",
                        returnStdout: true
                    ).trim()

                    def json = readJSON text: result

                    // Check if any secrets leaked
                    def leaked = json.secrets.findAll { it.status == 'LEAKED' }
                    if (leaked.size() > 0) {
                        error("Secret leak detected: ${leaked*.variable_name.join(', ')}")
                    }
                }
            }
        }
    }
}
```

## Performance Considerations

### For Large Repositories

**Problem:** Repositories with 100,000+ commits can be slow to scan.

**Solutions:**

1. **Use `--value` for faster search**
   ```bash
   # Much faster than name-based search
   tripwire audit SECRET_KEY --value "actual-secret-123"
   ```

2. **Limit commit depth**
   ```bash
   # Only check recent commits
   tripwire audit SECRET_KEY --max-commits 1000
   ```

3. **Use shallow clones in CI/CD**
   ```bash
   # Only clone last 100 commits
   git clone --depth 100 repo.git
   ```

### Memory Usage

- Typical usage: < 100MB RAM
- Large repos (50,000+ commits): < 500MB RAM
- Each occurrence stored: ~500 bytes

### Speed Benchmarks

| Repository Size | Commits Analyzed | Time      |
|----------------|------------------|-----------|
| Small          | 100              | < 1s      |
| Medium         | 1,000            | 2-5s      |
| Large          | 10,000           | 10-30s    |
| Very Large     | 100,000          | 1-3 min   |

## Limitations

### What It Can Find

- Secrets in text files
- Environment variable assignments
- Configuration files
- Source code constants

### What It Cannot Find

- Secrets in binary files (images, executables)
- Encrypted or encoded secrets
- Secrets in git submodules (analyzed separately)
- Secrets in git LFS objects

### Edge Cases

1. **Renamed files**: Tracked correctly via git history
2. **Merge commits**: Analyzed like normal commits
3. **Rebased branches**: History may show duplicates
4. **Squashed commits**: Original history lost

## Troubleshooting

### "Not a git repository" Error

```bash
Error: Not a git repository: /path/to/dir
```

**Solution:** Run from inside a git repository:
```bash
cd /path/to/git/repo
tripwire audit SECRET_KEY
```

### No Secrets Found (False Negative)

```bash
✓ No leaks found for SECRET_KEY
```

**Possible causes:**

1. **Secret name doesn't match**
   ```bash
   # Try different patterns
   tripwire audit SECRET_KEY
   tripwire audit API_KEY
   tripwire audit "SECRET.*KEY"
   ```

2. **Use actual value**
   ```bash
   tripwire audit SECRET_KEY --value "actual-secret-123"
   ```

3. **Check older commits**
   ```bash
   tripwire audit SECRET_KEY --max-commits 10000
   ```

### Too Many Results (False Positives)

```bash
Found in 500 commits
```

**Solutions:**

1. **Use exact value**
   ```bash
   tripwire audit KEY --value "sk-exact-value"
   ```

2. **Check if variable name is too generic**
   - Avoid auditing generic names like `KEY`, `TOKEN`, `VALUE`
   - Use full names like `STRIPE_SECRET_KEY`

### Performance Issues

```bash
# Audit taking > 5 minutes
```

**Solutions:**

1. **Reduce max commits**
   ```bash
   tripwire audit SECRET_KEY --max-commits 500
   ```

2. **Use value-based search**
   ```bash
   tripwire audit SECRET_KEY --value "actual-value"
   ```

3. **Shallow clone in CI/CD**
   ```bash
   git clone --depth 100 repo.git
   ```

## Advanced Usage

### Auditing Multiple Secrets

**Recommended approach - Use `--all` flag:**
```bash
# Automatically detect and audit all secrets
tripwire audit --all --json > audit_results.json
```

**Alternative - Manual specification:**
```bash
#!/bin/bash
# audit_specific_secrets.sh

SECRETS=(
  "AWS_SECRET_ACCESS_KEY"
  "AWS_ACCESS_KEY_ID"
  "DATABASE_URL"
  "STRIPE_SECRET_KEY"
  "GITHUB_TOKEN"
  "OPENAI_API_KEY"
)

for secret in "${SECRETS[@]}"; do
  echo "Auditing $secret..."
  tripwire audit "$secret" --json > "audit_${secret}.json"

  status=$(jq -r '.status' "audit_${secret}.json")
  if [ "$status" == "LEAKED" ]; then
    echo "⚠️  LEAK DETECTED: $secret"
    jq . "audit_${secret}.json"
  else
    echo "✓ Clean: $secret"
  fi
  echo ""
done
```

### Custom Alerting

```python
#!/usr/bin/env python3
"""Custom alerting for secret leaks."""

import json
import subprocess
import sys

def audit_secret(secret_name: str) -> dict:
    """Audit a secret and return results."""
    result = subprocess.run(
        ["tripwire", "audit", secret_name, "--json"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)

def send_alert(secret_name: str, audit_data: dict) -> None:
    """Send alert to Slack/Email/PagerDuty."""
    if audit_data["severity"] == "CRITICAL":
        # Send PagerDuty alert
        print(f"🚨 CRITICAL: {secret_name} leaked!")
    elif audit_data["severity"] == "HIGH":
        # Send Slack alert
        print(f"⚠️  HIGH: {secret_name} leaked!")

if __name__ == "__main__":
    secrets = ["AWS_SECRET_ACCESS_KEY", "DATABASE_URL"]

    for secret in secrets:
        data = audit_secret(secret)
        if data["status"] == "LEAKED":
            send_alert(secret, data)
```

## FAQ

### Q: Does this work with all git hosting providers?

**A:** Yes! The audit works with any git repository, regardless of hosting (GitHub, GitLab, Bitbucket, self-hosted, etc.).

### Q: Will this find secrets in submodules?

**A:** No, git submodules must be audited separately. Navigate to each submodule directory and run `tripwire audit` there.

### Q: Can I audit a remote repository without cloning?

**A:** No, you need a local clone. The tool analyzes local git history.

### Q: Does this scan the remote repository directly?

**A:** No, it only scans your local git history. Make sure to `git fetch` or `git pull` to get the latest remote commits.

### Q: What if I've already force-pushed to remove the secret?

**A:** Run the audit after force-pushing to verify the secret is gone:
```bash
git fetch origin --force
tripwire audit SECRET_KEY
```

### Q: Can this recover the actual secret value?

**A:** The tool can find where secrets were used, but actual values are redacted in output for security. It will show `***REDACTED***` in context.

### Q: Does this send any data to external servers?

**A:** No! All analysis is done locally. Nothing is sent anywhere.

### Q: How is this different from GitHub secret scanning?

**A:**
- **GitHub secret scanning**: Automatic, specific patterns, limited to GitHub
- **TripWire audit**: Manual, custom variables, works anywhere, detailed timeline

Use both for comprehensive security!

## See Also

- [TripWire Documentation](https://tripwire.dev)
- [Secret Management Best Practices](https://tripwire.dev/best-practices)
- [CI/CD Integration Guide](https://tripwire.dev/ci-cd)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) - Alternative for large repos
- [git-filter-repo](https://github.com/newren/git-filter-repo) - Modern alternative to filter-branch

## Contributing

Found a bug or want to improve secret detection? Contributions welcome!

- [GitHub Issues](https://github.com/Daily-Nerd/TripWire/issues)
- [Pull Requests](https://github.com/Daily-Nerd/TripWire/pulls)
- [Discussion Forum](https://github.com/Daily-Nerd/TripWire/discussions)
