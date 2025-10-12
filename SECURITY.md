# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.10.x  | ✅ (Latest - Plugin system with security hardening) |
| 0.9.x   | ✅ (TripWireV2 architecture) |
| 0.8.x   | ✅ (Security command group, thread-safe caching) |
| 0.7.x   | ⚠️ (upgrade to 0.10.0 - missing critical security fixes) |
| < 0.7   | ❌ (unsupported - critical vulnerabilities) |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

### Preferred: GitHub Security Advisories

Report security vulnerabilities using GitHub Security Advisories:
https://github.com/Daily-Nerd/TripWire/security/advisories/new

## Threat Model

### Trust Boundaries

TripWire trusts:
- Python runtime environment
- Operating system
- Git binary and git repository integrity
- Project dependencies (python-dotenv, click, rich, etc.)

TripWire does NOT trust:
- .env file contents (may contain malicious patterns)
- Git repository history (may contain malicious data)
- User-provided regex patterns (may cause ReDoS)
- File system paths (may contain path traversal)

### Attack Surface

1. **Environment Variable Parsing** (user input)
   - Type coercion with malformed data
   - Validation bypass attempts
   - Resource exhaustion via large inputs

2. **Git Command Execution** (command injection risk)
   - File paths with shell metacharacters
   - Git command injection via arguments
   - Process resource exhaustion

3. **Regular Expressions** (ReDoS risk)
   - Secret detection patterns
   - User-provided validation patterns
   - Email/URL format validators

4. **File System Operations** (path traversal risk)
   - .env file loading
   - Scanner directory traversal
   - Git audit file access

### Adversarial Scenarios

- **Malicious .env file**: Compromised developer or supply chain attack
- **Malicious git repository**: Cloned from untrusted source
- **Adversarial inputs**: Fuzzing and exploitation attempts
- **Resource exhaustion**: DOS via large files or complex patterns
- **Malicious plugins** (v0.10.0+): Compromised plugin from unofficial source
- **Plugin API abuse** (v0.10.0+): HTTP downgrade, domain spoofing, SSRF attacks

## Security Features

### ReDoS Protection (v0.5.2+)
All regex patterns have bounded quantifiers to prevent catastrophic backtracking:
- Email validator: Limited to RFC-compliant lengths (64/255/24 chars)
- Secret patterns: Max 1024 char limits
- Custom patterns: Validation and warnings

### Command Injection Protection (v0.5.2+)
Git commands use list form with path validation:
- All file paths validated with `_is_valid_git_path()`
- Rejects shell metacharacters (`;`, `&`, `|`, etc.)
- Commands executed with `subprocess.run(shell=False)`

### Thread Safety (v0.5.2+, v0.8.1+)
Frame inspection and type inference protected with locks:
- `_FRAME_INFERENCE_LOCK` for concurrent `require()` calls
- Thread-safe LRU cache prevents race conditions (v0.8.1)
- Prevents race conditions in web servers
- Safe for multi-threaded applications

### Resource Limits (v0.5.2+)
Default limits prevent DOS attacks:
- Max files to scan: 1,000
- Max file size: 1MB
- Max string lengths: 10KB
- Max commits (git audit): 100

### Plugin Security (v0.10.0+)
Comprehensive protection for plugin system:
- **HTTPS Enforcement**: Azure Key Vault URLs must use HTTPS (prevents downgrade attacks)
- **Domain Validation**: Validates cloud provider domains (e.g., `.vault.azure.net`)
- **SSRF Protection**: URL scheme whitelist prevents internal network access
- **Path Traversal Protection**: Sanitizes file paths in plugin installation
- **Plugin Sandboxing**: Isolates plugin execution from core TripWire
- **Official Registry**: Verified plugins with security audits

## Security Testing

### Automated Security Checks

Run before each release:
```bash
# Static analysis
bandit -r src/tripwire/

# Dependency vulnerabilities
pip-audit

# Security regression tests
pytest tests/test_security*.py -v
```

### Fuzzing Strategy

Key areas to fuzz:
1. **Regex patterns**: Test with 100k+ character strings
2. **Type coercion**: Test with malformed JSON, numbers, booleans
3. **Git commands**: Test with special characters in file paths
4. **File operations**: Test with path traversal sequences

### Security Regression Tests

All security fixes include permanent regression tests:
- `tests/test_security_secrets.py` - False positives/negatives
- `tests/test_security_git_audit.py` - Command injection attempts
- `tests/test_security_validation.py` - ReDoS and limit bypasses

## Security Advisories

| Advisory ID | Date | Severity | CVE | Description | Fixed In |
|------------|------|----------|-----|-------------|----------|
| TW-2025-001 | 2025-10-10 | HIGH | Pending | ReDoS in email validator | v0.5.2 |
| TW-2025-002 | 2025-10-10 | HIGH | Pending | Command injection in git audit | v0.5.2 |
| TW-2025-003 | 2025-10-10 | MEDIUM | Pending | Race condition in type inference | v0.5.2 |
| TW-2025-004 | 2025-10-12 | HIGH | Pending | Azure Key Vault HTTPS enforcement | v0.10.0 |
| TW-2025-005 | 2025-10-12 | MEDIUM | Pending | Plugin registry SSRF protection | v0.10.0 |
| TW-2025-006 | 2025-10-12 | HIGH | Pending | Plugin path traversal protection | v0.10.0 |

## Disclosure Policy

When we receive a security bug report, we will:

1. **Acknowledge** (within 48 hours): Confirm receipt and assign severity
2. **Investigate** (3-7 days): Confirm vulnerability and assess impact
3. **Develop Fix** (7-14 days): Create patch and comprehensive tests
4. **Coordinate Disclosure** (90 days): Work with reporter on timeline
5. **Release** (as soon as ready): Ship fix in new version
6. **Announce** (after release): Public disclosure with credit

### Disclosure Timeline

- **Day 0**: Vulnerability reported
- **Day 2**: Acknowledgment sent
- **Day 7**: Initial assessment complete
- **Day 14**: Fix developed and tested
- **Day 21**: Security patch released
- **Day 90**: Full public disclosure (if not released sooner)

## Security Best Practices

### For Users

1. **Keep TripWire Updated**: Always use latest version
   ```bash
   pip install --upgrade tripwire-py
   ```

2. **Use Schema Validation**: Enable `.tripwire.toml` schemas
   ```bash
   tripwire schema from-code
   ```

3. **Scan for Secrets**: Before committing (v0.8.0+)
   ```bash
   tripwire security scan --strict
   ```

4. **Audit Git History**: On new projects (v0.8.0+)
   ```bash
   tripwire security audit --all
   ```

5. **Use Official Plugins Only** (v0.10.0+): Install from verified registry
   ```bash
   tripwire plugin install vault  # ✅ Official registry
   # Verify plugin metadata before use
   tripwire plugin list
   ```

6. **Enforce HTTPS for Cloud Services** (v0.10.0+): Never use HTTP
   ```python
   # ✅ GOOD - HTTPS enforced
   from tripwire.plugins.sources import AzureKeyVaultSource
   azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

   # ❌ BAD - Will be rejected in v0.10.0+
   # azure = AzureKeyVaultSource(vault_url="http://mykeyvault.vault.azure.net")
   ```

7. **Set Resource Limits**: In production
   ```python
   # Adjust limits for your environment
   from tripwire import scanner
   scanner.MAX_FILES_TO_SCAN = 500
   scanner.MAX_FILE_SIZE = 500_000
   ```

### For Contributors

1. **Run Security Tests**: Before submitting PR
   ```bash
   pytest tests/test_security*.py -v
   ```

2. **Check Common Vulnerabilities**:
   - Command injection in subprocess calls
   - Path traversal in file operations
   - ReDoS in regex patterns
   - Resource exhaustion in loops

3. **Use Static Analysis**:
   ```bash
   bandit -r src/tripwire/
   mypy src/tripwire --strict
   ```

4. **Review Dependencies**:
   ```bash
   pip-audit
   ```

## Hall of Fame

We deeply appreciate security researchers who responsibly disclose vulnerabilities:

- *[Your name could be here! Report responsibly and get credited]*

## Contact

- **Security Issues**: GitHub Security Advisories (preferred)
- **General Security Questions**: GitHub Discussions

---

*Last Updated: 2025-10-12*
*Document Version: 1.1*
*Latest Security Fixes: v0.10.0 (Azure HTTPS enforcement, SSRF protection, path traversal)*
