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

## Pickle Serialization Security

### Overview

TripWire's `Secret` objects support pickle serialization to enable distributed systems and caching. This is an intentional design decision to support production use cases like:

- Distributed task queues (Celery, RQ, Dask)
- Caching systems (Redis, Memcached with pickle serialization)
- Multiprocessing (Python's multiprocessing.Pool)
- RPC systems (gRPC, Pyro)

### Security Model

**Pickle is not the vulnerability** - the vulnerability is where pickled data is stored or transmitted.

Think of pickle like `get_secret_value()`:
- `get_secret_value()` exposes the secret, but it's needed for legitimate use
- Pickle exposes the secret in serialized form, but it's needed for distributed systems
- Both require secure infrastructure to be safe

### Safe Usage Patterns

✓ **SAFE**: Encrypted message broker
```python
# Celery with RabbitMQ over TLS
@celery.task
def process_payment(api_key: Secret[str]):
    stripe.api_key = api_key.get_secret_value()

# Safe because: RabbitMQ uses TLS, message broker is trusted
process_payment.delay(api_key=Secret("sk_live_123"))
```

✓ **SAFE**: Encrypted cache backend
```python
# Redis with encryption at rest
cache_data = {"api_key": Secret("sk_live_123")}
redis.set("config", pickle.dumps(cache_data))

# Safe because: Redis has encryption at rest enabled
```

✓ **SAFE**: Local multiprocessing
```python
# Local multiprocessing pool
def worker(secret: Secret[str]):
    # Process data with secret
    pass

with multiprocessing.Pool(4) as pool:
    pool.map(worker, [Secret("token1"), Secret("token2")])

# Safe because: Processes are local, shared memory is secure
```

### Unsafe Usage Patterns

✗ **UNSAFE**: File storage without encryption
```python
# DON'T DO THIS
secret = Secret("my_password")
with open("secrets.pkl", "wb") as f:
    pickle.dump(secret, f)  # ✗ Unencrypted file on disk
```

✗ **UNSAFE**: Network transmission without TLS
```python
# DON'T DO THIS
import socket
secret = Secret("api_key")
sock.send(pickle.dumps(secret))  # ✗ Plaintext over network
```

✗ **UNSAFE**: Shared cache without encryption
```python
# DON'T DO THIS
memcached.set("secret", pickle.dumps(Secret("key")))  # ✗ Plaintext cache
```

### Alternative Pattern: Avoid Pickle

If your infrastructure doesn't support encrypted pickle transport, pass unwrapped values instead:

```python
# Instead of pickling Secret objects
@celery.task
def process(secret: Secret[str]):
    api_key = secret.get_secret_value()

process.delay(secret=Secret("sk_live_123"))  # Pickles Secret object

# Pass plain values instead
@celery.task
def process(secret_value: str):
    secret = Secret(secret_value)  # Wrap in worker
    api_key = secret.get_secret_value()

process.delay(secret_value="sk_live_123")  # Pickles plain string
```

### Infrastructure Checklist

When using pickle with Secret objects, ensure:

- [ ] Message broker uses TLS/encryption (RabbitMQ, Kafka, AWS SQS)
- [ ] Cache backend has encryption at rest (Redis, ElastiCache)
- [ ] Network channels are secured (VPN, TLS, private network)
- [ ] Temporary files are encrypted (if using file-based queues)
- [ ] Crash dumps exclude pickled secrets (configure debugger)

### Why We Support Pickle

**Precedent**: Pydantic's `SecretStr` supports pickle for the same reasons.

**Use Cases**:
- Celery/RQ tasks that accept Secret arguments
- Redis caching of configuration objects with secrets
- Multiprocessing pools that need Secret objects
- Distributed computing frameworks (Dask, Ray)

**Philosophy**: Blocking pickle would force users to work around the restriction, often in less secure ways (e.g., passing secrets as environment variables, storing in global state, etc.). Instead, we support pickle with clear security guidance.

### Reporting Issues

If you discover a security issue related to pickle serialization, please report it via our vulnerability disclosure process (see above).

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
