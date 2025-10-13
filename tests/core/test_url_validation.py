"""Tests for URL component validation."""

import pytest

from tripwire.core.validation_orchestrator import (
    URLComponentsValidationRule,
    ValidationContext,
)
from tripwire.exceptions import ValidationError
from tripwire.validation import validate_url_components


class TestValidateURLComponents:
    """Tests for validate_url_components() helper function."""

    def test_valid_url_no_constraints(self):
        """URL passes validation when no constraints specified."""
        valid, error = validate_url_components("https://example.com")
        assert valid is True
        assert error is None

    def test_valid_url_with_all_components(self):
        """URL with all components passes validation."""
        valid, error = validate_url_components(
            "https://api.example.com:443/v1/users?api_key=xxx&version=1",
            protocols=["https"],
            allowed_ports=[443, 8443],
            required_path="^/v[0-9]+/",
            required_params=["api_key", "version"],
            forbidden_params=["debug"],
        )
        assert valid is True
        assert error is None

    # Protocol validation tests
    def test_protocol_whitelist_valid(self):
        """Valid protocol passes whitelist."""
        valid, error = validate_url_components("https://example.com", protocols=["https", "wss"])
        assert valid is True
        assert error is None

    def test_protocol_whitelist_invalid(self):
        """Invalid protocol fails whitelist."""
        valid, error = validate_url_components("http://example.com", protocols=["https"])
        assert valid is False
        assert "Protocol 'http' not allowed" in error
        assert "Allowed protocols: https" in error

    def test_protocol_missing(self):
        """Missing protocol fails validation."""
        valid, error = validate_url_components("//example.com", protocols=["https"])
        assert valid is False
        assert "URL missing protocol/scheme" in error

    def test_multiple_protocols_allowed(self):
        """Multiple protocols in whitelist."""
        for protocol in ["https", "wss", "ftps"]:
            valid, _ = validate_url_components(f"{protocol}://example.com", protocols=["https", "wss", "ftps"])
            assert valid is True

    # Port validation tests
    def test_allowed_ports_valid(self):
        """Valid port passes whitelist."""
        valid, error = validate_url_components("https://example.com:8443", allowed_ports=[443, 8443, 9443])
        assert valid is True
        assert error is None

    def test_allowed_ports_invalid(self):
        """Invalid port fails whitelist."""
        valid, error = validate_url_components("https://example.com:8080", allowed_ports=[443, 8443])
        assert valid is False
        assert "Port 8080 not allowed" in error
        assert "Allowed ports: 443, 8443" in error

    def test_forbidden_ports(self):
        """Forbidden port fails validation."""
        valid, error = validate_url_components("https://example.com:22", forbidden_ports=[22, 23, 3389])
        assert valid is False
        assert "Port 22 is forbidden" in error

    def test_default_port_implicit(self):
        """URL without explicit port passes validation (default ports)."""
        valid, error = validate_url_components("https://example.com", allowed_ports=[443])
        # No explicit port in URL; should pass regardless of allowed_ports constraint
        assert valid is True
        assert error is None

    def test_forbidden_and_allowed_ports(self):
        """Forbidden ports checked before allowed ports."""
        valid, error = validate_url_components(
            "https://example.com:22",
            allowed_ports=[22, 443],
            forbidden_ports=[22],
        )
        assert valid is False
        assert "Port 22 is forbidden" in error

    # Path validation tests
    def test_required_path_valid(self):
        """Valid path matches pattern."""
        valid, error = validate_url_components("https://api.example.com/v1/users", required_path="^/v[0-9]+/")
        assert valid is True
        assert error is None

    def test_required_path_invalid(self):
        """Invalid path fails pattern match."""
        valid, error = validate_url_components("https://api.example.com/users", required_path="^/v[0-9]+/")
        assert valid is False
        assert "URL path '/users' does not match required pattern" in error
        assert "^/v[0-9]+/" in error

    def test_required_path_missing(self):
        """Missing path fails validation."""
        valid, error = validate_url_components("https://api.example.com", required_path="^/api/")
        assert valid is False
        assert "URL path missing" in error

    def test_path_pattern_complex(self):
        """Complex regex patterns work correctly."""
        valid, error = validate_url_components(
            "https://api.example.com/api/v2.1/users/123",
            required_path=r"^/api/v\d+\.\d+/users/\d+$",
        )
        assert valid is True

    # Query parameter validation tests
    def test_required_params_valid(self):
        """All required params present."""
        valid, error = validate_url_components(
            "https://example.com?api_key=xxx&version=1",
            required_params=["api_key", "version"],
        )
        assert valid is True
        assert error is None

    def test_required_params_missing_one(self):
        """Missing one required param fails."""
        valid, error = validate_url_components(
            "https://example.com?api_key=xxx", required_params=["api_key", "version"]
        )
        assert valid is False
        assert "Missing required query parameters: version" in error

    def test_required_params_missing_multiple(self):
        """Missing multiple required params fails."""
        valid, error = validate_url_components("https://example.com", required_params=["api_key", "version", "token"])
        assert valid is False
        assert "Missing required query parameters" in error
        # All three should be in error message
        assert "api_key" in error
        assert "version" in error
        assert "token" in error

    def test_forbidden_params_absent(self):
        """No forbidden params present."""
        valid, error = validate_url_components("https://example.com?api_key=xxx", forbidden_params=["debug", "test"])
        assert valid is True
        assert error is None

    def test_forbidden_params_present(self):
        """Forbidden param present fails."""
        valid, error = validate_url_components("https://example.com?debug=true", forbidden_params=["debug", "test"])
        assert valid is False
        assert "Forbidden query parameters present: debug" in error

    def test_forbidden_params_multiple_present(self):
        """Multiple forbidden params present."""
        valid, error = validate_url_components(
            "https://example.com?debug=true&test=1",
            forbidden_params=["debug", "test"],
        )
        assert valid is False
        assert "Forbidden query parameters present" in error

    def test_required_and_forbidden_params(self):
        """Required and forbidden params work together."""
        valid, error = validate_url_components(
            "https://example.com?api_key=xxx&version=1",
            required_params=["api_key"],
            forbidden_params=["debug"],
        )
        assert valid is True

    # Edge cases
    def test_invalid_url_format(self):
        """Completely invalid URL fails gracefully."""
        valid, error = validate_url_components("not a url at all")
        # urlparse doesn't fail, it just returns empty components
        # This is OK - other validators can check URL format
        assert valid is True  # No constraints specified

    def test_url_with_fragment(self):
        """URL with fragment (#) handled correctly."""
        valid, error = validate_url_components(
            "https://example.com/page#section",
            required_path="^/page",
        )
        assert valid is True

    def test_url_with_username_password(self):
        """URL with credentials handled correctly."""
        valid, error = validate_url_components(
            "https://user:pass@example.com:443/api",
            protocols=["https"],
            allowed_ports=[443],
            required_path="^/api",
        )
        assert valid is True

    def test_empty_query_params(self):
        """Empty query string doesn't fail param validation."""
        valid, error = validate_url_components("https://example.com?", required_params=[])
        assert valid is True

    def test_duplicate_query_params(self):
        """Duplicate query params handled (first value used by parse_qs)."""
        valid, error = validate_url_components(
            "https://example.com?key=value1&key=value2",
            required_params=["key"],
        )
        assert valid is True


class TestURLComponentsValidationRule:
    """Tests for URLComponentsValidationRule class."""

    def test_valid_url_passes(self):
        """Valid URL passes validation rule."""
        rule = URLComponentsValidationRule(protocols=["https"])
        context = ValidationContext(
            name="API_URL",
            raw_value="https://example.com",
            coerced_value="https://example.com",
            expected_type=str,
        )
        # Should not raise
        rule.validate(context)

    def test_invalid_url_raises_validation_error(self):
        """Invalid URL raises ValidationError."""
        rule = URLComponentsValidationRule(protocols=["https"])
        context = ValidationContext(
            name="API_URL",
            raw_value="http://example.com",
            coerced_value="http://example.com",
            expected_type=str,
        )
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)

        assert exc_info.value.variable_name == "API_URL"
        assert "http" in str(exc_info.value.reason)

    def test_custom_error_message(self):
        """Custom error message overrides default."""
        rule = URLComponentsValidationRule(
            protocols=["https"],
            error_message="Only HTTPS URLs are allowed for security",
        )
        context = ValidationContext(
            name="API_URL",
            raw_value="http://example.com",
            coerced_value="http://example.com",
            expected_type=str,
        )
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)

        assert exc_info.value.reason == "Only HTTPS URLs are allowed for security"

    def test_all_parameters(self):
        """All validation parameters work together."""
        rule = URLComponentsValidationRule(
            protocols=["https"],
            allowed_ports=[443, 8443],
            forbidden_ports=[80],
            required_path="^/api/v[0-9]+/",
            required_params=["api_key"],
            forbidden_params=["debug"],
        )

        # Valid URL
        context = ValidationContext(
            name="API_URL",
            raw_value="https://api.example.com:443/api/v1/users?api_key=xxx",
            coerced_value="https://api.example.com:443/api/v1/users?api_key=xxx",
            expected_type=str,
        )
        rule.validate(context)  # Should not raise

        # Invalid protocol
        context.raw_value = "http://api.example.com:443/api/v1/users?api_key=xxx"
        with pytest.raises(ValidationError):
            rule.validate(context)

    def test_non_string_value_skipped(self):
        """Non-string values are skipped (not validated)."""
        rule = URLComponentsValidationRule(protocols=["https"])
        context = ValidationContext(
            name="PORT",
            raw_value="8080",
            coerced_value=8080,
            expected_type=int,
        )
        # Should not raise even though int 8080 is not a valid URL
        rule.validate(context)

    def test_security_example_https_only(self):
        """Real-world security example: HTTPS-only enforcement."""
        rule = URLComponentsValidationRule(
            protocols=["https"],
            error_message="Security policy: Only HTTPS URLs allowed in production",
        )

        # Valid HTTPS URL
        context = ValidationContext(
            name="DATABASE_URL",
            raw_value="https://db.example.com",
            coerced_value="https://db.example.com",
            expected_type=str,
        )
        rule.validate(context)

        # Invalid HTTP URL
        context.raw_value = "http://db.example.com"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "Security policy" in str(exc_info.value.reason)

    def test_security_example_no_privileged_ports(self):
        """Real-world security example: Prevent privileged ports."""
        rule = URLComponentsValidationRule(
            forbidden_ports=[22, 23, 3389, 5900],  # SSH, Telnet, RDP, VNC
            error_message="Privileged ports not allowed in API URLs",
        )

        # Valid URL
        context = ValidationContext(
            name="API_URL",
            raw_value="https://api.example.com:8080",
            coerced_value="https://api.example.com:8080",
            expected_type=str,
        )
        rule.validate(context)

        # SSH port rejected
        context.raw_value = "https://api.example.com:22"
        context.coerced_value = "https://api.example.com:22"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "Privileged ports not allowed" in str(exc_info.value.reason)

    def test_api_example_versioned_endpoints(self):
        """Real-world API example: Enforce versioned endpoints."""
        rule = URLComponentsValidationRule(
            protocols=["https"],
            required_path="^/api/v[0-9]+/",
            required_params=["api_key"],
            forbidden_params=["debug", "test"],
        )

        # Valid API URL
        context = ValidationContext(
            name="API_ENDPOINT",
            raw_value="https://api.example.com/api/v2/users?api_key=xxx",
            coerced_value="https://api.example.com/api/v2/users?api_key=xxx",
            expected_type=str,
        )
        rule.validate(context)

        # Missing version in path
        context.raw_value = "https://api.example.com/api/users?api_key=xxx"
        with pytest.raises(ValidationError):
            rule.validate(context)

        # Debug flag present (forbidden)
        context.raw_value = "https://api.example.com/api/v2/users?api_key=xxx&debug=1"
        with pytest.raises(ValidationError):
            rule.validate(context)

    def test_integration_with_validation_orchestrator(self):
        """URLComponentsValidationRule works in ValidationOrchestrator."""
        from tripwire.core.validation_orchestrator import (
            FormatValidationRule,
            ValidationOrchestrator,
        )

        # Create orchestrator with multiple rules
        orchestrator = (
            ValidationOrchestrator()
            .add_rule(FormatValidationRule("url"))  # Basic format check
            .add_rule(URLComponentsValidationRule(protocols=["https"], required_params=["api_key"]))
        )

        # Valid URL passes both rules
        context = ValidationContext(
            name="API_URL",
            raw_value="https://api.example.com/v1/users?api_key=xxx",
            coerced_value="https://api.example.com/v1/users?api_key=xxx",
            expected_type=str,
        )
        orchestrator.validate(context)

        # Invalid protocol fails second rule
        context.raw_value = "http://api.example.com/v1/users?api_key=xxx"
        context.coerced_value = "http://api.example.com/v1/users?api_key=xxx"
        with pytest.raises(ValidationError) as exc_info:
            orchestrator.validate(context)
        assert "Protocol 'http' not allowed" in str(exc_info.value.reason)

        # Missing API key fails second rule
        context.raw_value = "https://api.example.com/v1/users"
        context.coerced_value = "https://api.example.com/v1/users"
        with pytest.raises(ValidationError) as exc_info:
            orchestrator.validate(context)
        assert "Missing required query parameters: api_key" in str(exc_info.value.reason)
