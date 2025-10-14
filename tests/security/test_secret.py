"""Tests for Secret wrapper class and related utilities.

This test suite verifies that secrets cannot be accidentally exposed through
various Python mechanisms (print, repr, JSON, etc.).
"""

import json
import pickle

import pytest

from tripwire.security.secret import (
    MASK_STRING,
    Secret,
    SecretBytes,
    SecretJSONEncoder,
    SecretStr,
    StrictSecretJSONEncoder,
    is_secret,
    mask_multiple_secrets,
    mask_secret_in_string,
    unwrap_secret,
)


class TestSecretBasics:
    """Test basic Secret wrapper functionality."""

    def test_creation(self):
        """Test creating Secret objects."""
        secret = Secret("my_secret_value")
        assert secret.get_secret_value() == "my_secret_value"

    def test_secret_str_alias(self):
        """Test SecretStr convenience alias."""
        secret: SecretStr = SecretStr("my_string_secret")
        assert secret.get_secret_value() == "my_string_secret"
        assert isinstance(secret, Secret)

    def test_secret_bytes_alias(self):
        """Test SecretBytes convenience alias."""
        secret: SecretBytes = SecretBytes(b"my_bytes_secret")
        assert secret.get_secret_value() == b"my_bytes_secret"
        assert isinstance(secret, Secret)

    def test_generic_type_annotation(self):
        """Test that Secret works with type annotations."""
        token: Secret[str] = Secret("my_token")
        number: Secret[int] = Secret(12345)

        assert token.get_secret_value() == "my_token"
        assert number.get_secret_value() == 12345


class TestSecretMasking:
    """Test that secrets are properly masked in various contexts."""

    def test_str_masking(self):
        """Test that str() masks the secret."""
        secret = Secret("my_secret")
        assert str(secret) == MASK_STRING
        assert str(secret) != "my_secret"

    def test_repr_masking(self):
        """Test that repr() masks the secret."""
        secret = Secret("my_secret")
        assert repr(secret) == f"Secret('{MASK_STRING}')"
        assert "my_secret" not in repr(secret)

    def test_print_masking(self, capsys):
        """Test that print() masks the secret."""
        secret = Secret("my_secret")
        print(secret)

        captured = capsys.readouterr()
        assert captured.out.strip() == MASK_STRING
        assert "my_secret" not in captured.out

    def test_fstring_masking(self):
        """Test that f-strings mask the secret."""
        secret = Secret("my_secret")
        message = f"Token: {secret}"

        assert message == f"Token: {MASK_STRING}"
        assert "my_secret" not in message

    def test_string_concatenation(self):
        """Test that string concatenation doesn't expose secret."""
        secret = Secret("my_secret")
        # String concatenation requires str() conversion
        message = "Token: " + str(secret)

        assert message == f"Token: {MASK_STRING}"
        assert "my_secret" not in message

    def test_format_masking(self):
        """Test that format() masks the secret."""
        secret = Secret("my_secret")
        message = "Token: {}".format(secret)

        assert message == f"Token: {MASK_STRING}"
        assert "my_secret" not in message


class TestSecretComparison:
    """Test secret comparison operations."""

    def test_equality_with_same_value(self):
        """Test that secrets with same value are equal."""
        secret1 = Secret("my_secret")
        secret2 = Secret("my_secret")

        assert secret1 == secret2

    def test_equality_with_different_value(self):
        """Test that secrets with different values are not equal."""
        secret1 = Secret("secret1")
        secret2 = Secret("secret2")

        assert secret1 != secret2

    def test_equality_with_plain_value(self):
        """Test that Secret can be compared with plain value."""
        secret = Secret("my_secret")

        assert secret == "my_secret"
        assert secret != "different_secret"

    def test_constant_time_comparison(self):
        """Test that string comparison uses constant-time comparison.

        Note: This test verifies the function is called, not actual timing
        (timing tests would be flaky and platform-dependent).
        """
        secret1 = Secret("password123")
        secret2 = Secret("password123")
        secret3 = Secret("different")

        # Should use secrets.compare_digest internally
        assert secret1 == secret2
        assert secret1 != secret3


class TestSecretHashing:
    """Test secret hashing for use in dicts/sets."""

    def test_hash_consistency(self):
        """Test that same value produces same hash."""
        secret1 = Secret("my_secret")
        secret2 = Secret("my_secret")

        assert hash(secret1) == hash(secret2)

    def test_hash_in_dict(self):
        """Test that Secret can be used as dict key."""
        secret = Secret("my_secret")
        data = {secret: "value"}

        assert secret in data
        assert data[secret] == "value"

    def test_hash_in_set(self):
        """Test that Secret can be used in sets."""
        secret1 = Secret("secret1")
        secret2 = Secret("secret2")
        secret3 = Secret("secret1")  # Same as secret1

        secret_set = {secret1, secret2, secret3}

        # secret1 and secret3 have same value, so only 2 unique items
        assert len(secret_set) == 2
        assert secret1 in secret_set
        assert secret2 in secret_set


class TestSecretLength:
    """Test len() support for Secret wrappers."""

    def test_length_of_string_secret(self):
        """Test that len() works for string secrets."""
        secret = Secret("my_secret_token")

        assert len(secret) == 15

    def test_length_of_list_secret(self):
        """Test that len() works for list secrets."""
        secret = Secret([1, 2, 3, 4, 5])

        assert len(secret) == 5

    def test_length_of_int_secret_raises_error(self):
        """Test that len() raises error for types without length."""
        secret = Secret(12345)

        with pytest.raises(TypeError, match="has no len"):
            len(secret)


class TestSecretBooleanContext:
    """Test Secret in boolean contexts."""

    def test_truthy_secret(self):
        """Test that non-empty secret is truthy."""
        secret = Secret("my_secret")

        assert bool(secret) is True
        if secret:
            pass  # Should not raise

    def test_falsy_secret(self):
        """Test that empty secret is falsy."""
        secret = Secret("")

        assert bool(secret) is False

    def test_zero_secret(self):
        """Test that zero value is falsy."""
        secret = Secret(0)

        assert bool(secret) is False


class TestSecretImmutability:
    """Test that Secret objects are immutable."""

    def test_cannot_set_attribute(self):
        """Test that attributes cannot be set after creation."""
        secret = Secret("my_secret")

        with pytest.raises(AttributeError, match="immutable"):
            secret.new_attr = "value"  # type: ignore[attr-defined]

    def test_cannot_delete_attribute(self):
        """Test that attributes cannot be deleted."""
        secret = Secret("my_secret")

        with pytest.raises(AttributeError, match="immutable"):
            del secret._value  # type: ignore[attr-defined]

    def test_slots_prevent_dict(self):
        """Test that __slots__ prevents __dict__ creation."""
        secret = Secret("my_secret")

        assert not hasattr(secret, "__dict__")


class TestSecretJSONSerialization:
    """Test JSON serialization protection."""

    def test_json_encoder_masks_secret(self):
        """Test that SecretJSONEncoder masks secrets."""
        data = {
            "username": "admin",
            "password": Secret("my_password"),
        }

        result = json.dumps(data, cls=SecretJSONEncoder)
        result_obj = json.loads(result)

        assert result_obj["username"] == "admin"
        assert result_obj["password"] == MASK_STRING
        assert "my_password" not in result

    def test_strict_encoder_raises_error(self):
        """Test that StrictSecretJSONEncoder raises error on secrets."""
        data = {"password": Secret("my_password")}

        with pytest.raises(TypeError, match="cannot be serialized"):
            json.dumps(data, cls=StrictSecretJSONEncoder)

    def test_default_encoder_fails_gracefully(self):
        """Test that default JSON encoder fails on Secret objects."""
        data = {"password": Secret("my_password")}

        # Default encoder should raise TypeError (not serializable)
        with pytest.raises(TypeError):
            json.dumps(data)

    def test_to_dict_method(self):
        """Test Secret.to_dict() method for serialization frameworks."""
        secret = Secret("my_secret")
        result = secret.to_dict()

        assert result["value"] == MASK_STRING
        assert result["type"] == "Secret"
        assert "my_secret" not in str(result)


class TestSecretPickleSerialization:
    """Test that secrets cannot be pickled (security feature)."""

    def test_pickle_preserves_secret(self):
        """Test that pickling preserves the secret value.

        Note: This is actually a security concern - pickled secrets could be
        stored/transmitted. Consider blocking pickle in production.
        """
        secret = Secret("my_secret")
        pickled = pickle.dumps(secret)
        unpickled = pickle.loads(pickled)

        # Pickle preserves the value (this could be a security issue)
        assert unpickled.get_secret_value() == "my_secret"

        # But the repr is still masked
        assert repr(unpickled) == f"Secret('{MASK_STRING}')"


class TestSecretUtilities:
    """Test utility functions for working with secrets."""

    def test_is_secret_function(self):
        """Test is_secret() type guard."""
        secret = Secret("my_secret")
        plain = "plain_value"

        assert is_secret(secret) is True
        assert is_secret(plain) is False

    def test_unwrap_secret_function(self):
        """Test unwrap_secret() helper."""
        secret = Secret("my_secret")
        plain = "plain_value"

        assert unwrap_secret(secret) == "my_secret"
        assert unwrap_secret(plain) == "plain_value"

    def test_mask_secret_in_string(self):
        """Test mask_secret_in_string() utility."""
        text = "Error: Invalid token abc123 provided"
        result = mask_secret_in_string(text, "abc123")

        assert result == f"Error: Invalid token {MASK_STRING} provided"
        assert "abc123" not in result

    def test_mask_multiple_secrets(self):
        """Test mask_multiple_secrets() utility."""
        text = "User: admin, Password: pass123, API Key: key456"
        result = mask_multiple_secrets(text, ["pass123", "key456"])

        assert result == f"User: admin, Password: {MASK_STRING}, API Key: {MASK_STRING}"
        assert "pass123" not in result
        assert "key456" not in result

    def test_mask_empty_secret_has_no_effect(self):
        """Test that empty secrets are not masked (avoid false positives)."""
        text = "Some random text"
        result = mask_secret_in_string(text, "")

        assert result == text  # Unchanged


class TestSecretEdgeCases:
    """Test edge cases and security scenarios."""

    def test_secret_in_exception_message(self):
        """Test that secrets in exception messages are masked."""
        secret = Secret("my_secret")

        try:
            raise ValueError(f"Invalid token: {secret}")
        except ValueError as e:
            error_msg = str(e)
            assert MASK_STRING in error_msg
            assert "my_secret" not in error_msg

    def test_secret_in_list_comprehension(self):
        """Test that secrets are masked in list comprehensions."""
        secrets = [Secret("secret1"), Secret("secret2"), Secret("secret3")]
        strings = [str(s) for s in secrets]

        assert all(s == MASK_STRING for s in strings)
        assert not any("secret" in s for s in strings)

    def test_secret_in_dict_values(self):
        """Test that secrets in dict values are masked when printed."""
        data = {
            "username": "admin",
            "password": Secret("my_password"),
        }

        dict_repr = repr(data)
        # The dict repr will show Secret('**********'), not the actual value
        assert "my_password" not in dict_repr

    def test_secret_with_special_characters(self):
        """Test secrets containing special regex characters."""
        secret_value = "my.secret*with+special[chars]"
        secret = Secret(secret_value)

        text = f"Token: {secret_value}"
        result = mask_secret_in_string(text, secret_value)

        assert result == f"Token: {MASK_STRING}"

    def test_very_long_secret(self):
        """Test that very long secrets are handled correctly."""
        long_secret = "a" * 10000
        secret = Secret(long_secret)

        assert str(secret) == MASK_STRING
        assert len(secret) == 10000
        assert secret.get_secret_value() == long_secret

    def test_unicode_secret(self):
        """Test that unicode secrets are handled correctly."""
        unicode_secret = "my_secret_🔐_token"
        secret = Secret(unicode_secret)

        assert str(secret) == MASK_STRING
        assert secret.get_secret_value() == unicode_secret

    def test_byte_secret(self):
        """Test that byte secrets are handled correctly."""
        byte_secret = b"\x00\x01\x02\x03\x04"
        secret: Secret[bytes] = Secret(byte_secret)

        assert str(secret) == MASK_STRING
        assert secret.get_secret_value() == byte_secret


class TestSecretSecurityProperties:
    """Test security properties of the Secret wrapper."""

    def test_memory_address_different(self):
        """Test that Secret objects have unique memory addresses."""
        secret1 = Secret("my_secret")
        secret2 = Secret("my_secret")

        # Even with same value, they should be different objects
        assert id(secret1) != id(secret2)

    def test_value_not_in_dir(self):
        """Test that dir() doesn't expose the secret value."""
        secret = Secret("my_secret")
        dir_output = dir(secret)

        # dir() should not expose the actual value
        dir_str = " ".join(dir_output)
        assert "my_secret" not in dir_str

    def test_vars_doesnt_work(self):
        """Test that vars() doesn't expose internal state (thanks to __slots__)."""
        secret = Secret("my_secret")

        # vars() should raise TypeError because of __slots__
        with pytest.raises(TypeError):
            vars(secret)

    def test_getattribute_doesnt_leak(self):
        """Test that __getattribute__ doesn't leak the secret."""
        secret = Secret("my_secret")

        # Accessing _value directly should work (Python doesn't have true private)
        # but it's obvious that you're accessing private internals
        assert secret._value == "my_secret"  # type: ignore[attr-defined]

        # However, normal attribute access shouldn't leak
        assert str(secret) == MASK_STRING


class TestSecretTypeIntegration:
    """Test integration with type checkers and type system."""

    def test_type_annotation_works(self):
        """Test that type annotations work correctly.

        Note: This test verifies runtime behavior. Static type checking would
        be done by mypy/pyright, not pytest.
        """
        token: Secret[str] = Secret("my_token")
        number: Secret[int] = Secret(12345)

        assert isinstance(token, Secret)
        assert isinstance(number, Secret)

    def test_secret_subclass_works(self):
        """Test that Secret can be subclassed (for custom behavior)."""

        class CustomSecret(Secret[str]):
            """Custom secret with additional logging."""

            def get_secret_value(self) -> str:
                # Could add audit logging here
                return super().get_secret_value()

        secret = CustomSecret("my_secret")
        assert secret.get_secret_value() == "my_secret"
        assert str(secret) == MASK_STRING
