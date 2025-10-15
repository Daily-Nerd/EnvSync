# Documentation Review Process

This document outlines TripWire's formal process for reviewing and approving documentation changes. Following this process ensures documentation remains accurate, testable, and trustworthy.

## Philosophy

**Empirical Validation Over Assumptions**

All technical claims in TripWire documentation must be empirically validated. We don't guess at error types, example outputs, or behavior - we verify everything in a live Python environment.

**Key Principles:**
- Every code example must be executable and tested
- Error types must match actual Python runtime behavior
- Complex examples should be runnable scripts in `examples/`
- Tests should verify documentation accuracy
- Technical claims require REPL or test verification

---

## When Documentation Review is Required

Documentation review is required for:

1. **README.md changes** - Primary user-facing documentation
2. **New code examples** - Any code block added to docs
3. **Error type claims** - Statements about exceptions or error behavior
4. **API documentation** - Changes to function/class signatures
5. **CLI documentation** - Changes to command behavior or output
6. **Framework integration examples** - FastAPI, Django, Flask examples
7. **Security documentation** - SECURITY.md changes
8. **Tutorial content** - Any step-by-step guides

---

## Review Checklist for Documentation PRs

### 1. Code Example Validation

**Required for all code examples:**

- [ ] **Executable Test**: Code example has corresponding test in `tests/test_readme_examples.py` or similar
- [ ] **Runnable Script**: For complex examples (3+ lines), create script in `examples/` directory
- [ ] **Link from Docs**: README or docs link to the executable script
- [ ] **Demo Mode**: Example supports `--demo` flag for testing without real credentials (if applicable)
- [ ] **Output Documented**: Expected output or behavior is clearly documented in comments

**Example:**


<!-- Good: Linked to verified example -->
```python
from tripwire import env
DATABASE_URL = env.require("DATABASE_URL", format="postgresql")
```
See [examples/basic/01_simple_require.py](examples/basic/01_simple_require.py)

<!-- Bad: Inline code with no verification -->
```python
from tripwire import env
# ... complex code with no test
```

### 2. Error Type Verification

**Required for all error/exception claims:**

- [ ] **REPL Verified**: Error type tested in Python REPL or pytest
- [ ] **Test Coverage**: Test case exists demonstrating the error
- [ ] **Accurate Message**: Error message matches actual Python output
- [ ] **Context Included**: Explanation of when/why error occurs

**Verification Process:**

```bash
# Verify in Python REPL
python3
>>> import os
>>> int(os.getenv("NONEXISTENT"))
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
```

**Document exactly:**
```markdown
Raises `TypeError: int() argument must be... not 'NoneType'`
```

### 3. Technical Accuracy Verification

**Required for all technical claims:**

- [ ] **Source Code Confirmed**: Claim matches actual implementation in `src/tripwire/`
- [ ] **Version Checked**: Feature availability matches version documentation
- [ ] **Behavior Tested**: Runtime behavior verified through tests
- [ ] **Edge Cases Considered**: Documented limitations or special cases

**High-Risk Areas (require extra scrutiny):**
- Type coercion behavior (int, bool, float conversions)
- Format validator patterns (regex, URL parsing)
- Import-time vs runtime behavior claims
- Thread safety guarantees
- Performance claims

### 4. Framework Integration Examples

**Required for FastAPI, Django, Flask examples:**

- [ ] **Minimal Dependencies**: Example only requires framework + TripWire
- [ ] **Copy-Paste Ready**: User can copy example and it works
- [ ] **Best Practices**: Follows framework conventions
- [ ] **Error Handling**: Shows proper error handling patterns
- [ ] **Commented**: Explains TripWire-specific patterns

### 5. CLI Documentation

**Required for CLI command documentation:**

- [ ] **Output Verified**: Command output matches actual CLI behavior
- [ ] **Flags Documented**: All flags and options listed correctly
- [ ] **Exit Codes**: Success/failure behavior documented
- [ ] **Examples Tested**: Command examples actually work

**Verification:**
```bash
# Test command and capture output
python -m tripwire.cli --help > cli_output.txt
# Compare against documentation
```

### 6. Links and References

**Required for all documentation links:**

- [ ] **Links Valid**: All internal links point to existing files
- [ ] **Paths Correct**: Relative paths work from document location
- [ ] **Anchors Exist**: Anchor links point to actual headings
- [ ] **External Links**: External links return 200 status (spot check)

---

## Review Process Steps

### Step 1: Initial Self-Review (Author)

**Before submitting PR:**

1. Run all code examples manually
2. Verify error types in Python REPL
3. Check that tests pass: `pytest tests/test_readme_examples.py`
4. Validate links: `make check-links` (if available)
5. Spell check with IDE tools
6. Read documentation as if you're a first-time user

### Step 2: Automated Validation (CI)

**Automated checks run on every PR:**

1. **Test Suite**: `pytest tests/test_readme_examples.py` - Validates all README examples
2. **Linting**: Ruff checks Python code in examples
3. **Type Checking**: Mypy validates type annotations
4. **Link Checking**: Validates internal documentation links (if configured)

### Step 3: Peer Review (Reviewer)

**Reviewer responsibilities:**

1. **Run Examples**: Execute 2-3 major code examples locally
2. **Verify Claims**: Spot-check technical claims against source code
3. **Check Tests**: Ensure tests actually validate what docs claim
4. **User Perspective**: Read as if unfamiliar with TripWire
5. **Ask Questions**: If anything is unclear, ask for clarification

**Review Focus Areas:**

- **Accuracy**: Do examples work as described?
- **Clarity**: Is explanation clear to target audience?
- **Completeness**: Are edge cases or limitations mentioned?
- **Consistency**: Does style match existing docs?

### Step 4: Approval Criteria

**Documentation PR can be approved when:**

- [ ] All code examples have tests
- [ ] Error types are verified
- [ ] Complex examples link to runnable scripts
- [ ] Links are valid
- [ ] Automated checks pass
- [ ] At least one reviewer has manually tested examples
- [ ] Technical accuracy is verified against source code

---

## Who Reviews Documentation Changes?

### Review Responsibility Matrix

| Change Type | Primary Reviewer | Secondary Reviewer |
|-------------|------------------|-------------------|
| README.md core sections | Maintainer | Any contributor |
| Code examples | Contributor with Python expertise | Maintainer |
| CLI documentation | CLI subsystem owner | Maintainer |
| Security documentation | Security-focused reviewer | Maintainer |
| Plugin documentation | Plugin system owner | Maintainer |
| Tutorial content | Documentation lead | Technical reviewer |

### Minimum Review Requirements

- **Minor fixes** (typos, grammar): 1 reviewer
- **New examples**: 2 reviewers (one must test examples)
- **Major sections**: 2 reviewers + maintainer approval
- **Security docs**: 2 reviewers (one security-focused)

---

## Common Documentation Issues

### Issue 1: Untested Code Examples

**Problem:**
```markdown
```python
# Example that looks plausible but has never been run
from tripwire import TripWire
env = TripWire()
DATABASE = env.require("DB_URL")  # Oops, wrong variable name
```
```

**Solution:**
- Add test to `tests/test_readme_examples.py`
- Create runnable script in `examples/`
- Link from README

### Issue 2: Incorrect Error Types

**Problem:**
```markdown
Raises `ValueError` when port is invalid
```

**Reality:**
```python
# Actually raises ValidationError, not ValueError
```

**Solution:**
- Verify in Python REPL or pytest
- Update documentation to match reality
- Add test case demonstrating the error

### Issue 3: Stale Examples

**Problem:**
- API changed but examples not updated
- Deprecated patterns still shown
- Version-specific features not marked

**Solution:**
- Run example against current codebase
- Update to use current API
- Mark version-specific features: `(v0.10.0+)`

### Issue 4: Missing Context

**Problem:**
```markdown
Use `env.require()` for required variables.
```

**Better:**
```markdown
Use `env.require()` for required variables. This validates at import time,
ensuring your app won't start if the variable is missing. See [example](examples/basic/01_simple_require.py).
```

---

## Adding Documentation Tests

### For README Examples

Add to `tests/test_readme_examples.py`:

```python
def test_readme_example_basic_require(monkeypatch, tmp_path):
    """Test README example: basic env.require() usage."""
    # Setup
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/mydb")

    # Act - Import and use as shown in README
    from tripwire import env
    DATABASE_URL = env.require("DATABASE_URL", format="postgresql")

    # Assert
    assert DATABASE_URL == "postgresql://localhost/mydb"

def test_readme_example_missing_variable():
    """Test README claim: Missing variable raises exception at import."""
    # Clear environment
    import os
    os.environ.pop("REQUIRED_VAR", None)

    # This should raise immediately
    with pytest.raises(ValidationError, match="Missing required.*REQUIRED_VAR"):
        from tripwire import env
        value = env.require("REQUIRED_VAR")
```

### For Examples Directory Scripts

Ensure scripts are importable and testable:

```python
# examples/basic/01_simple_require.py
def main():
    """Main function for testing."""
    from tripwire import env
    DATABASE_URL = env.require("DATABASE_URL")
    return DATABASE_URL

if __name__ == "__main__":
    result = main()
    print(f"Success: {result}")
```

Test file:
```python
# tests/examples/test_basic_examples.py
def test_simple_require_example(monkeypatch):
    """Test examples/basic/01_simple_require.py"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/mydb")
    from examples.basic.01_simple_require import main
    result = main()
    assert result == "postgresql://localhost/mydb"
```

---

## Documentation Style Guide

### Code Examples

**Preferred:**
```python
# Clear, minimal example with comments
from tripwire import env

# Validate at import time - app won't start if missing
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
```

**Avoid:**
```python
# Overly complex example with too many concepts
from tripwire import TripWire, ValidationError, SecretDetector
env = TripWire(auto_load=True, strict_mode=True, validate_secrets=True)
try:
    DATABASE_URL = env.require("DATABASE_URL", format="postgresql",
                               min_length=10, max_length=200,
                               pattern=r"^postgresql://.*")
except ValidationError as e:
    # ... complex error handling
```

### Error Documentation

**Preferred:**
```markdown
**Raises:**
- `ValidationError` - When variable is missing or invalid
- `TypeError` - When type coercion fails

**Example:**
```python
# Missing variable
>>> env.require("MISSING")
ValidationError: Missing required environment variable: MISSING
```
```

### Linking Examples

**Preferred:**
```markdown
```python
DATABASE_URL = env.require("DATABASE_URL", format="postgresql")
```

See full example: [examples/basic/01_simple_require.py](examples/basic/01_simple_require.py)
```

---

## Quality Gates

Documentation PRs must pass these gates:

### Gate 1: Automated Tests
- [ ] `pytest tests/test_readme_examples.py` passes
- [ ] All CI checks pass
- [ ] Code style checks pass

### Gate 2: Manual Verification
- [ ] At least 2 code examples tested manually by reviewer
- [ ] Error types verified in REPL (if applicable)
- [ ] Links clicked and verified

### Gate 3: Technical Accuracy
- [ ] Claims match source code implementation
- [ ] Version markers are correct
- [ ] No misleading or ambiguous statements

### Gate 4: User Experience
- [ ] Examples are clear and copy-paste ready
- [ ] Target audience can understand without prior knowledge
- [ ] Troubleshooting guidance provided for common issues

---

## Emergency Documentation Fixes

For urgent documentation bugs (incorrect error types, broken examples):

1. **Create issue** with `docs` and `bug` labels
2. **Fast-track review**: Single reviewer can approve
3. **Fix forward**: Don't let perfect be enemy of good
4. **Add test**: Ensure issue doesn't recur

---

## Continuous Improvement

### Monthly Documentation Audit

Review team should:
- Run all examples from scratch
- Check for stale examples
- Verify external links
- Update version-specific markers
- Add missing tests

### Documentation Metrics

Track:
- Test coverage of README examples (target: 100%)
- Number of runnable scripts in `examples/` (target: 15+)
- Documentation bug reports (target: <5 per quarter)
- Time to fix documentation bugs (target: <24 hours)

---

## Resources

- **Test Suite**: `tests/test_readme_examples.py`
- **Examples**: `examples/` directory
- **Style Guide**: This document
- **PR Template**: `.github/pull_request_template.md`
- **Contributing**: `CONTRIBUTING.md`

---

## Questions?

If you're unsure whether documentation meets quality standards:

1. Ask in PR comments
2. Request review from documentation lead
3. Check existing examples in `examples/` directory
4. Review recent PRs with `docs` label

---

**Remember:** Documentation is code. Test it like code. Review it like code. Maintain it like code.
