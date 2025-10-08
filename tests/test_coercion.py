"""Tests for improved list and dict coercion."""

import pytest

from tripwire.exceptions import TypeCoercionError
from tripwire.validation import coerce_dict, coerce_list, coerce_type


class TestCoerceListImproved:
    """Test improved list coercion with smart parsing."""

    def test_simple_csv(self):
        """Test simple comma-separated values."""
        result = coerce_list("apple, banana, cherry")
        assert result == ["apple", "banana", "cherry"]

    def test_simple_csv_no_spaces(self):
        """Test CSV without spaces."""
        result = coerce_list("apple,banana,cherry")
        assert result == ["apple", "banana", "cherry"]

    def test_json_array(self):
        """Test JSON array format."""
        result = coerce_list('["apple", "banana", "cherry"]')
        assert result == ["apple", "banana", "cherry"]

    def test_json_array_with_numbers(self):
        """Test JSON array with mixed types."""
        result = coerce_list('[1, 2, "three", 4]')
        assert result == ["1", "2", "three", "4"]

    def test_json_array_empty(self):
        """Test empty JSON array."""
        result = coerce_list("[]")
        assert result == []

    def test_quoted_csv_double_quotes(self):
        """Test CSV with double-quoted values."""
        result = coerce_list('"hello, world", "foo, bar", "baz"')
        assert result == ["hello, world", "foo, bar", "baz"]

    def test_quoted_csv_single_quotes(self):
        """Test CSV with single-quoted values."""
        result = coerce_list("'hello, world', 'foo, bar', 'baz'")
        assert result == ["hello, world", "foo, bar", "baz"]

    def test_mixed_quoted_unquoted(self):
        """Test mix of quoted and unquoted values."""
        result = coerce_list('"item 1", item2, "item 3"')
        assert result == ["item 1", "item2", "item 3"]

    def test_values_with_spaces(self):
        """Test values containing spaces in quotes."""
        result = coerce_list('"value one", "value two", "value three"')
        assert result == ["value one", "value two", "value three"]

    def test_empty_string(self):
        """Test empty string."""
        result = coerce_list("")
        assert result == []

    def test_single_item(self):
        """Test single item."""
        result = coerce_list("single")
        assert result == ["single"]

    def test_trailing_comma(self):
        """Test trailing comma is handled."""
        result = coerce_list("item1, item2, item3,")
        assert result == ["item1", "item2", "item3"]

    def test_whitespace_only(self):
        """Test whitespace-only string."""
        result = coerce_list("   ")
        assert result == []

    def test_custom_delimiter(self):
        """Test custom delimiter."""
        result = coerce_list("apple|banana|cherry", delimiter="|")
        assert result == ["apple", "banana", "cherry"]

    def test_urls_in_list(self):
        """Test list of URLs."""
        result = coerce_list("https://example.com, https://test.com, https://demo.com")
        assert result == ["https://example.com", "https://test.com", "https://demo.com"]

    def test_paths_in_list(self):
        """Test list of file paths."""
        result = coerce_list("/path/to/file, /another/path, /third/path")
        assert result == ["/path/to/file", "/another/path", "/third/path"]


class TestCoerceDictImproved:
    """Test improved dict coercion with smart parsing."""

    def test_json_object(self):
        """Test JSON object format."""
        result = coerce_dict('{"key1": "value1", "key2": "value2"}')
        assert result == {"key1": "value1", "key2": "value2"}

    def test_json_object_with_types(self):
        """Test JSON object with mixed types."""
        result = coerce_dict('{"str": "text", "num": 42, "bool": true, "null": null}')
        assert result == {"str": "text", "num": 42, "bool": True, "null": None}

    def test_json_object_empty(self):
        """Test empty JSON object."""
        result = coerce_dict("{}")
        assert result == {}

    def test_key_value_pairs(self):
        """Test simple key=value pairs."""
        result = coerce_dict("key1=value1,key2=value2,key3=value3")
        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

    def test_key_value_with_spaces(self):
        """Test key=value pairs with spaces."""
        result = coerce_dict("key1 = value1, key2 = value2")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_quoted_values(self):
        """Test key=value with quoted values."""
        result = coerce_dict('key1="value 1",key2="value 2"')
        assert result == {"key1": "value 1", "key2": "value 2"}

    def test_quoted_values_single_quotes(self):
        """Test key=value with single-quoted values."""
        result = coerce_dict("key1='value 1',key2='value 2'")
        assert result == {"key1": "value 1", "key2": "value 2"}

    def test_mixed_quoted_unquoted(self):
        """Test mix of quoted and unquoted values."""
        result = coerce_dict('key1=simple,key2="with spaces",key3=another')
        assert result == {"key1": "simple", "key2": "with spaces", "key3": "another"}

    def test_numeric_values(self):
        """Test numeric values in key=value format."""
        result = coerce_dict("port=8000,timeout=30,retries=3")
        assert result == {"port": 8000, "timeout": 30, "retries": 3}

    def test_boolean_values(self):
        """Test boolean values in key=value format."""
        result = coerce_dict("debug=true,production=false")
        assert result == {"debug": True, "production": False}

    def test_mixed_value_types(self):
        """Test mixed value types in key=value format."""
        result = coerce_dict('host=localhost,port=8000,debug=true,name="My App"')
        assert result == {"host": "localhost", "port": 8000, "debug": True, "name": "My App"}

    def test_values_with_equals(self):
        """Test values containing equals signs (in quotes)."""
        result = coerce_dict('key1="a=b",key2="x=y"')
        assert result == {"key1": "a=b", "key2": "x=y"}

    def test_values_with_commas(self):
        """Test values containing commas (in quotes)."""
        result = coerce_dict('key1="a,b,c",key2="x,y,z"')
        assert result == {"key1": "a,b,c", "key2": "x,y,z"}

    def test_empty_values(self):
        """Test empty values."""
        result = coerce_dict("key1=,key2=value2")
        assert result == {"key1": "", "key2": "value2"}

    def test_urls_as_values(self):
        """Test URLs as values."""
        result = coerce_dict("api=https://api.example.com,web=https://example.com")
        assert result == {"api": "https://api.example.com", "web": "https://example.com"}

    def test_invalid_no_equals(self):
        """Test error when key=value pair has no equals."""
        with pytest.raises(ValueError, match="Invalid key=value pair"):
            coerce_dict("key1,key2=value2")

    def test_invalid_json(self):
        """Test error on invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            coerce_dict("{invalid json}")

    def test_invalid_empty_string(self):
        """Test error on empty string."""
        with pytest.raises(ValueError, match="No valid key=value pairs"):
            coerce_dict("")


class TestCoerceTypeWithImprovedCoercion:
    """Test coerce_type with improved list/dict coercion."""

    def test_coerce_list_json_format(self):
        """Test type coercion with JSON list."""
        result = coerce_type('["a", "b", "c"]', list, "TEST_VAR")
        assert result == ["a", "b", "c"]

    def test_coerce_list_csv_format(self):
        """Test type coercion with CSV list."""
        result = coerce_type("a, b, c", list, "TEST_VAR")
        assert result == ["a", "b", "c"]

    def test_coerce_dict_json_format(self):
        """Test type coercion with JSON dict."""
        result = coerce_type('{"key": "value"}', dict, "TEST_VAR")
        assert result == {"key": "value"}

    def test_coerce_dict_keyvalue_format(self):
        """Test type coercion with key=value dict."""
        result = coerce_type("key=value,other=test", dict, "TEST_VAR")
        assert result == {"key": "value", "other": "test"}

    def test_coerce_list_error(self):
        """Test error handling in list coercion."""
        # This should work with any string
        result = coerce_type("test", list, "TEST_VAR")
        assert result == ["test"]

    def test_coerce_dict_error(self):
        """Test error handling in dict coercion."""
        with pytest.raises(TypeCoercionError):
            coerce_type("not a dict", dict, "TEST_VAR")


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_allowed_hosts_list(self):
        """Test parsing ALLOWED_HOSTS environment variable."""
        # Django-style ALLOWED_HOSTS
        result = coerce_list("localhost,127.0.0.1,example.com,.example.com")
        assert result == ["localhost", "127.0.0.1", "example.com", ".example.com"]

    def test_cors_origins_list(self):
        """Test parsing CORS origins."""
        result = coerce_list("https://example.com, https://www.example.com, https://api.example.com")
        assert result == [
            "https://example.com",
            "https://www.example.com",
            "https://api.example.com",
        ]

    def test_database_replica_urls(self):
        """Test parsing database replica URLs."""
        result = coerce_list("postgresql://db1:5432/mydb, postgresql://db2:5432/mydb, postgresql://db3:5432/mydb")
        assert len(result) == 3
        assert all("postgresql://" in url for url in result)

    def test_feature_flags_dict(self):
        """Test parsing feature flags."""
        result = coerce_dict("feature_a=true,feature_b=false,feature_c=true")
        assert result == {"feature_a": True, "feature_b": False, "feature_c": True}

    def test_redis_config_dict(self):
        """Test parsing Redis configuration."""
        result = coerce_dict('host=redis.example.com,port=6379,db=0,password="secret123"')
        assert result == {
            "host": "redis.example.com",
            "port": 6379,
            "db": 0,
            "password": "secret123",
        }

    def test_api_endpoints_dict(self):
        """Test parsing API endpoints configuration."""
        result = coerce_dict(
            "users=https://api.example.com/users,"
            "posts=https://api.example.com/posts,"
            "comments=https://api.example.com/comments"
        )
        assert result == {
            "users": "https://api.example.com/users",
            "posts": "https://api.example.com/posts",
            "comments": "https://api.example.com/comments",
        }

    def test_email_recipients_with_commas(self):
        """Test parsing email list with commas in names."""
        result = coerce_list('"Smith, John", "Doe, Jane", "Johnson, Bob"')
        assert result == ["Smith, John", "Doe, Jane", "Johnson, Bob"]

    def test_server_config_with_mixed_types(self):
        """Test server configuration with mixed types."""
        result = coerce_dict('host=0.0.0.0,port=8000,workers=4,reload=true,log_level="info"')
        assert result == {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 4,
            "reload": True,
            "log_level": "info",
        }
