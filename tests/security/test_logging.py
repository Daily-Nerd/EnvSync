"""Tests for logging integration and automatic secret redaction."""

import logging
import re

import pytest

from tripwire.security.logging import (
    COMMON_SECRET_PATTERNS,
    SecretRedactionFilter,
    SecretRedactionFormatter,
    auto_install,
    auto_uninstall,
    clear_registry,
    register_common_patterns,
    register_pattern,
    register_secret,
    unregister_secret,
)
from tripwire.security.secret import MASK_STRING, Secret


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear secret registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def logger():
    """Create a test logger with a capturing handler."""
    test_logger = logging.getLogger("test_tripwire_logging")
    test_logger.handlers.clear()
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False  # Don't propagate to root logger

    # Create string capture handler
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)

    yield test_logger, log_capture

    # Cleanup
    test_logger.handlers.clear()


class TestSecretRegistration:
    """Test secret registration and unregistration."""

    def test_register_plain_string(self):
        """Test registering a plain string secret."""
        register_secret("my_secret_value")
        # No exception = success
        # Actual redaction tested in filter tests

    def test_register_secret_object(self):
        """Test registering a Secret object."""
        secret = Secret("my_secret_value")
        register_secret(secret)
        # Should automatically unwrap

    def test_unregister_secret(self):
        """Test unregistering a secret."""
        register_secret("my_secret")
        unregister_secret("my_secret")
        # No exception = success

    def test_register_empty_string_ignored(self):
        """Test that empty strings are not registered."""
        register_secret("")
        # Should be ignored silently

    def test_clear_registry(self):
        """Test clearing all registered secrets."""
        register_secret("secret1")
        register_secret("secret2")
        clear_registry()
        # Registry should be empty


class TestPatternRegistration:
    """Test regex pattern registration."""

    def test_register_string_pattern(self):
        """Test registering a pattern as string."""
        register_pattern(r"AKIA[0-9A-Z]{16}")

    def test_register_compiled_pattern(self):
        """Test registering a pre-compiled pattern."""
        pattern = re.compile(r"ghp_[0-9a-zA-Z]{36}")
        register_pattern(pattern)

    def test_register_common_patterns(self):
        """Test registering all common patterns."""
        register_common_patterns()
        # Should register all patterns without error


class TestSecretRedactionFilter:
    """Test the SecretRedactionFilter."""

    def test_filter_redacts_registered_secret(self, logger):
        """Test that registered secrets are redacted in logs."""
        test_logger, log_capture = logger

        # Add filter
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        # Register secret
        register_secret("my_secret_password")

        # Log message containing secret
        test_logger.info("Password: my_secret_password")

        # Check output
        output = log_capture.getvalue()
        assert MASK_STRING in output
        assert "my_secret_password" not in output

    def test_filter_preserves_non_secrets(self, logger):
        """Test that non-secret content is not redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info("This is a normal log message")

        output = log_capture.getvalue()
        assert "This is a normal log message" in output

    def test_filter_redacts_multiple_secrets(self, logger):
        """Test that multiple secrets are all redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("secret1")
        register_secret("secret2")
        register_secret("secret3")

        test_logger.info("Secrets: secret1, secret2, secret3")

        output = log_capture.getvalue()
        assert "secret1" not in output
        assert "secret2" not in output
        assert "secret3" not in output
        assert output.count(MASK_STRING) == 3

    def test_filter_handles_substring_secrets(self, logger):
        """Test that longer secrets are redacted before shorter ones."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        # Register both "abc" and "abc123"
        register_secret("abc")
        register_secret("abc123")

        test_logger.info("Token: abc123")

        output = log_capture.getvalue()
        # Should redact "abc123" first (longer match)
        assert "abc123" not in output
        assert "abc" not in output

    def test_filter_redacts_pattern_matches(self, logger):
        """Test that pattern-matched secrets are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        # Register AWS access key pattern
        register_pattern(r"AKIA[0-9A-Z]{16}")

        test_logger.info("AWS Key: AKIAIOSFODNN7EXAMPLE")

        output = log_capture.getvalue()
        assert "AKIAIOSFODNN7EXAMPLE" not in output
        assert MASK_STRING in output

    def test_filter_with_custom_mask(self, logger):
        """Test using a custom mask string."""
        test_logger, log_capture = logger

        custom_mask = "[REDACTED]"
        test_logger.handlers[0].addFilter(SecretRedactionFilter(mask=custom_mask))

        register_secret("my_secret")

        test_logger.info("Secret: my_secret")

        output = log_capture.getvalue()
        assert custom_mask in output
        assert "my_secret" not in output

    def test_filter_in_fstring(self, logger):
        """Test that secrets in f-strings are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        secret_value = "my_secret_token"
        register_secret(secret_value)

        test_logger.info(f"Token: {secret_value}")

        output = log_capture.getvalue()
        assert "my_secret_token" not in output
        assert MASK_STRING in output

    def test_filter_in_format_string(self, logger):
        """Test that secrets in format strings are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info("Secret: {}".format("my_secret"))

        output = log_capture.getvalue()
        assert "my_secret" not in output
        assert MASK_STRING in output

    def test_filter_in_percent_formatting(self, logger):
        """Test that secrets in %-formatting are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info("Secret: %s", "my_secret")

        output = log_capture.getvalue()
        assert "my_secret" not in output
        assert MASK_STRING in output


class TestSecretRedactionFormatter:
    """Test the SecretRedactionFormatter."""

    def test_formatter_redacts_secrets(self, logger):
        """Test that formatter redacts secrets."""
        test_logger, log_capture = logger

        # Replace handler formatter
        formatter = SecretRedactionFormatter(
            fmt="%(levelname)s - %(message)s",
        )
        test_logger.handlers[0].setFormatter(formatter)

        register_secret("my_secret")

        test_logger.info("Secret: my_secret")

        output = log_capture.getvalue()
        assert "my_secret" not in output
        assert MASK_STRING in output
        assert "INFO -" in output  # Format applied

    def test_formatter_with_custom_mask(self, logger):
        """Test formatter with custom mask."""
        test_logger, log_capture = logger

        custom_mask = "[HIDDEN]"
        formatter = SecretRedactionFormatter(
            fmt="%(message)s",
            mask=custom_mask,
        )
        test_logger.handlers[0].setFormatter(formatter)

        register_secret("my_secret")

        test_logger.info("Secret: my_secret")

        output = log_capture.getvalue()
        assert custom_mask in output
        assert "my_secret" not in output


class TestAutoInstall:
    """Test automatic installation of redaction."""

    def test_auto_install_on_logger(self):
        """Test auto-installing on a specific logger."""
        test_logger = logging.getLogger("test_auto_install")
        test_logger.handlers.clear()

        # Should create handler if none exist
        auto_install("test_auto_install")

        assert len(test_logger.handlers) > 0
        # Check that filter was added
        has_filter = any(isinstance(f, SecretRedactionFilter) for h in test_logger.handlers for f in h.filters)
        assert has_filter

        # Cleanup
        test_logger.handlers.clear()

    def test_auto_install_on_existing_handler(self):
        """Test auto-installing on logger with existing handler."""
        test_logger = logging.getLogger("test_auto_install_2")
        test_logger.handlers.clear()

        # Add a handler first
        handler = logging.StreamHandler()
        test_logger.addHandler(handler)

        # Install filter
        auto_install("test_auto_install_2")

        # Check filter was added to existing handler
        assert any(isinstance(f, SecretRedactionFilter) for f in handler.filters)

        # Cleanup
        test_logger.handlers.clear()

    def test_auto_install_on_root_logger(self):
        """Test auto-installing on root logger."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()

        try:
            # Clear handlers for test
            root_logger.handlers.clear()

            auto_install()  # No logger name = root logger

            # Should add handler and filter
            has_filter = any(isinstance(f, SecretRedactionFilter) for h in root_logger.handlers for f in h.filters)
            assert has_filter
        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers

    def test_auto_uninstall(self):
        """Test auto-uninstalling filters."""
        test_logger = logging.getLogger("test_uninstall")
        test_logger.handlers.clear()

        # Install
        auto_install("test_uninstall")

        # Verify installed
        has_filter = any(isinstance(f, SecretRedactionFilter) for h in test_logger.handlers for f in h.filters)
        assert has_filter

        # Uninstall
        auto_uninstall("test_uninstall")

        # Verify removed
        has_filter = any(isinstance(f, SecretRedactionFilter) for h in test_logger.handlers for f in h.filters)
        assert not has_filter

        # Cleanup
        test_logger.handlers.clear()


class TestCommonPatterns:
    """Test common secret pattern detection."""

    def test_aws_access_key_pattern(self, logger):
        """Test AWS access key pattern detection."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_pattern(COMMON_SECRET_PATTERNS["aws_access_key"])

        test_logger.info("Key: AKIAIOSFODNN7EXAMPLE")

        output = log_capture.getvalue()
        assert "AKIAIOSFODNN7EXAMPLE" not in output

    def test_github_token_pattern(self, logger):
        """Test GitHub token pattern detection."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_pattern(COMMON_SECRET_PATTERNS["github_token"])

        test_logger.info("Token: ghp_" + "A" * 36)

        output = log_capture.getvalue()
        assert "ghp_" + "A" * 36 not in output

    def test_stripe_key_pattern(self, logger):
        """Test Stripe API key pattern detection."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_pattern(COMMON_SECRET_PATTERNS["stripe_key"])

        test_logger.info("Stripe: sk_live_" + "A" * 24)

        output = log_capture.getvalue()
        assert "sk_live_" + "A" * 24 not in output

    def test_register_all_common_patterns(self, logger):
        """Test registering all common patterns at once."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_common_patterns()

        # Test a few different patterns
        test_logger.info("AWS: AKIAIOSFODNN7EXAMPLE")
        test_logger.info("GitHub: ghp_" + "A" * 36)

        output = log_capture.getvalue()
        assert "AKIAIOSFODNN7EXAMPLE" not in output
        assert "ghp_" + "A" * 36 not in output


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_log_message(self, logger):
        """Test that empty log messages don't cause errors."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info("")

        # Should not raise

    def test_none_in_log_message(self, logger):
        """Test that None in log message is handled."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info("Value: %s", None)

        # Should not raise

    def test_exception_logging(self, logger):
        """Test that secrets in exception logs are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret_password")

        try:
            raise ValueError("Invalid password: my_secret_password")
        except ValueError:
            test_logger.exception("An error occurred")

        output = log_capture.getvalue()
        assert "my_secret_password" not in output
        assert MASK_STRING in output

    def test_multiline_log_message(self, logger):
        """Test that secrets in multiline messages are redacted."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        test_logger.info(
            """
        Line 1: Some text
        Line 2: Secret: my_secret
        Line 3: More text
        """
        )

        output = log_capture.getvalue()
        assert "my_secret" not in output
        assert MASK_STRING in output

    def test_unicode_in_secret(self, logger):
        """Test that unicode secrets are handled correctly."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        unicode_secret = "my_secret_🔐_token"
        register_secret(unicode_secret)

        test_logger.info(f"Token: {unicode_secret}")

        output = log_capture.getvalue()
        assert unicode_secret not in output
        assert MASK_STRING in output

    def test_very_long_secret(self, logger):
        """Test that very long secrets are handled efficiently."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        long_secret = "a" * 10000
        register_secret(long_secret)

        test_logger.info(f"Secret: {long_secret}")

        output = log_capture.getvalue()
        assert long_secret not in output
        assert MASK_STRING in output

    def test_special_regex_characters_in_secret(self, logger):
        """Test that secrets with special regex chars are handled."""
        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        special_secret = "my.secret*with+special[chars]"
        register_secret(special_secret)

        test_logger.info(f"Secret: {special_secret}")

        output = log_capture.getvalue()
        assert special_secret not in output
        assert MASK_STRING in output


class TestThreadSafety:
    """Test thread-safety of secret registration."""

    def test_concurrent_registration(self):
        """Test that concurrent secret registration is thread-safe."""
        import threading

        def register_secrets(prefix: str) -> None:
            for i in range(100):
                register_secret(f"{prefix}_secret_{i}")

        threads = [threading.Thread(target=register_secrets, args=(f"thread{i}",)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should not raise, all secrets registered

    def test_concurrent_logging(self, logger):
        """Test that concurrent logging with redaction is thread-safe."""
        import threading

        test_logger, log_capture = logger
        test_logger.handlers[0].addFilter(SecretRedactionFilter())

        register_secret("my_secret")

        def log_messages() -> None:
            for i in range(50):
                test_logger.info(f"Message {i}: my_secret")

        threads = [threading.Thread(target=log_messages) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        output = log_capture.getvalue()
        # All secrets should be redacted
        assert "my_secret" not in output
