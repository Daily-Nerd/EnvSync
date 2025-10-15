# README Examples Test Suite Guide

## Purpose

This test suite validates that all code examples in `README.md` are technically accurate and produce the claimed behavior. After Issue #50 (the first external bug report), this automated testing infrastructure was created to prevent future documentation drift.

## Quick Start

```bash
# Run all README example tests
pytest tests/test_readme_examples.py

# Run with verbose output
pytest tests/test_readme_examples.py -v

# Run specific test class
pytest tests/test_readme_examples.py::TestProblemSection

# Run specific test method
pytest tests/test_readme_examples.py::TestProblemSection::test_database_url_none_split_raises_attribute_error
```

## What Gets Tested

### 1. Anti-Pattern Examples ("The Problem" section)
- ✅ `None.split()` raises AttributeError (not TypeError)
- ✅ `int(os.getenv())` raises TypeError when var not set (not ValueError)
- ✅ String comparison pitfalls with `os.getenv() == "true"`

### 2. TripWire Solution Examples ("After TripWire" section)
- ✅ `env.require()` validates at import time
- ✅ Format validators (`postgresql`, `email`, `url`, `ipv4`)
- ✅ Range validation (`min_val`, `max_val`)
- ✅ `env.optional()` with defaults

### 3. Type Inference Examples
- ✅ Integer type coercion and range validation
- ✅ Boolean type coercion (true/false/1/0/yes/no)
- ✅ Float type coercion
- ✅ List type coercion (CSV and JSON formats)
- ✅ Choices/enum validation

### 4. Framework Integration Examples
- ✅ FastAPI patterns
- ✅ Django settings patterns
- ✅ Flask app configuration patterns

### 5. Error Message Quality
- ✅ Missing variable error messages are clear
- ✅ Format validation errors are actionable
- ✅ Range validation errors show limits

## Adding Tests for New README Examples

When adding new code examples to README.md:

### Step 1: Identify the Example

```python
# In README.md
API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")
```

### Step 2: Create Test in Appropriate Section

```python
# In tests/test_readme_examples.py

class TestFormatValidatorsSection:
    """Tests for 'Format Validators' examples (README lines X-Y)."""

    def test_custom_regex_pattern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify custom regex pattern validation (README line X).

        README example:
            API_KEY: str = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")

        This tests that regex patterns are enforced correctly.
        """
        from tripwire import TripWire

        # Set up test environment
        monkeypatch.setenv("API_KEY", "sk-abcdefghijklmnopqrstuvwxyz012345")

        env = TripWire(load_dotenv=False)
        result = env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")

        # Verify behavior matches README claim
        assert result.startswith("sk-")
        assert len(result) == 35  # "sk-" + 32 characters
```

### Step 3: Test Both Success and Failure Paths

```python
def test_custom_regex_pattern_rejects_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify custom regex pattern rejects invalid values."""
    from tripwire import TripWire

    monkeypatch.setenv("API_KEY", "invalid-format")

    env = TripWire(load_dotenv=False)

    with pytest.raises(Exception):  # Should raise validation error
        env.require("API_KEY", pattern=r"^sk-[a-zA-Z0-9]{32}$")
```

### Step 4: Document What You're Testing

Use clear docstrings that:
1. Reference the README section and line numbers
2. Quote the actual example from README
3. Explain what claim is being verified
4. Note any special considerations

## Test Patterns

### Pattern 1: Testing Error Behavior

```python
def test_example_raises_correct_error(self) -> None:
    """Verify example raises AttributeError, not TypeError (README line X)."""
    with pytest.raises(AttributeError, match="expected error message pattern"):
        # Code that should raise error
        pass
```

### Pattern 2: Testing TripWire Features

```python
def test_example_validates_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify TripWire validation works as documented (README line X)."""
    from tripwire import TripWire

    monkeypatch.setenv("VAR_NAME", "value")

    env = TripWire(load_dotenv=False)
    result = env.require("VAR_NAME", format="email")

    assert "@" in result  # Verify expected behavior
```

### Pattern 3: Testing Anti-Patterns

```python
def test_anti_pattern_demonstrates_problem(self) -> None:
    """Demonstrate why os.getenv() pattern is problematic (README line X).

    This is an anti-pattern test showing WHAT NOT TO DO.
    """
    import os

    # Show the problem
    os.environ["DEBUG"] = "True"
    assert os.getenv("DEBUG") == "true" is False  # Fails unexpectedly
```

## Common Pitfalls

### ❌ DON'T: Test implementation details

```python
# BAD - Testing internal implementation
def test_validator_uses_regex_internally():
    from tripwire.validation import validate_email
    # Don't test HOW it works, test THAT it works
```

### ✅ DO: Test documented behavior

```python
# GOOD - Testing documented interface
def test_email_validator_accepts_valid_emails():
    from tripwire import TripWire
    env = TripWire(load_dotenv=False)
    # Test the public API as documented
```

### ❌ DON'T: Make tests brittle with exact error messages

```python
# BAD - Too specific, will break with message changes
with pytest.raises(ValueError, match="Must be exactly 32 characters long"):
```

### ✅ DO: Match essential error patterns

```python
# GOOD - Flexible enough to handle message improvements
with pytest.raises(ValueError, match="32"):  # Just check key detail
```

### ❌ DON'T: Test examples in isolation from README

```python
# BAD - Test doesn't match any README example
def test_obscure_edge_case():
    # Tests something not in README
```

### ✅ DO: Test exactly what's in README

```python
# GOOD - Test matches README example exactly
def test_readme_line_142_example():
    """Test example from README line 142."""
    # Code that matches README example
```

## Maintenance Checklist

Before committing README changes:

- [ ] Identify all new executable code examples
- [ ] Add test(s) to `test_readme_examples.py` for each example
- [ ] Run tests: `pytest tests/test_readme_examples.py -v`
- [ ] Verify all tests pass
- [ ] Update test docstrings with new line numbers if sections moved
- [ ] Add test class if new major section added to README

## CI Integration

These tests run automatically in CI:

```yaml
# .github/workflows/ci.yml
- name: Run README example tests
  run: pytest tests/test_readme_examples.py -v
```

If README tests fail in CI:
1. Check if README example is incorrect (fix README)
2. Check if test expectation is wrong (fix test)
3. Check if TripWire behavior changed (update README AND test)

## Troubleshooting

### Tests fail after TripWire update
- **Cause:** TripWire behavior changed
- **Fix:** Update tests to match new behavior, update README if needed

### Tests fail after README update
- **Cause:** New example added without test
- **Fix:** Add test for new example

### Tests pass but example is still wrong
- **Cause:** Test doesn't actually validate the claim
- **Fix:** Improve test to verify the actual documented behavior

### Can't reproduce error in test
- **Cause:** Example might be incomplete or context-dependent
- **Fix:** Add necessary setup (monkeypatch, fixtures) or mark as integration test

## Background: Why This Matters

### Issue #50: The Wake-Up Call

The first external bug report (Issue #50 from @cleder) revealed two documentation inaccuracies:

1. **F-string example** (removed in fix):
   ```python
   # README claimed this raised TypeError
   token = None
   header = f"Bearer {token}"  # Actually produces "Bearer None"
   ```

2. **int(os.getenv()) example** (fixed in PR #51):
   ```python
   # README claimed ValueError, actually raises TypeError
   PORT = int(os.getenv("PORT"))  # TypeError when PORT not set
   ```

### The Problem

Without automated testing:
- Documentation drift goes unnoticed
- Error types get documented incorrectly
- Examples might not actually work
- Community trust erodes with inaccurate docs

### The Solution

This test suite ensures:
- ✅ Error types match actual Python behavior
- ✅ TripWire features work as documented
- ✅ Examples are runnable and correct
- ✅ Changes are automatically validated in CI

### The Impact

- **Technical Credibility:** Users trust the documentation
- **Developer Experience:** Examples actually work when copy-pasted
- **Maintenance Efficiency:** Catch documentation bugs before users do
- **Community Confidence:** Shows commitment to quality

## Related Documentation

- **Full Audit Report:** `docs/README_AUDIT_REPORT.md`
- **README:** `README.md`
- **Test File:** `tests/test_readme_examples.py`
- **Issue #50:** First external bug report
- **PR #51:** Fixes for Issue #50

## Questions?

- Check existing tests for examples
- Review `docs/README_AUDIT_REPORT.md` for comprehensive analysis
- Open issue if test pattern is unclear
- Ask in Discord: https://discord.gg/eDwuVY68

---

**Remember:** Good documentation is tested documentation. Every README example should have a test proving it works as claimed.
