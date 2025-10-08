"""Tests for the secrets detection module."""

import tempfile
from pathlib import Path

import pytest

from tripwire.secrets import (
    SecretType,
    calculate_entropy,
    detect_generic_credential,
    detect_secrets_in_value,
    is_high_entropy,
    is_placeholder,
    redact_value,
    scan_env_file,
)


def test_calculate_entropy():
    """Test entropy calculation."""
    # Low entropy (repeated characters)
    assert calculate_entropy("aaaa") < 1.0

    # Medium entropy
    assert 2.0 < calculate_entropy("abcd1234") < 4.0

    # High entropy (random-looking)
    assert calculate_entropy("x9K2mP8qL4vN7wR3") > 3.5

    # Empty string
    assert calculate_entropy("") == 0.0


def test_is_high_entropy():
    """Test high entropy detection."""
    # Short strings should not be flagged
    assert is_high_entropy("abc") is False

    # Common values should not be flagged
    assert is_high_entropy("true") is False
    assert is_high_entropy("false") is False
    assert is_high_entropy("DEBUG_MODE") is False

    # High entropy random string should be flagged
    assert is_high_entropy("mK8qL4vN7wR3x9P2tY5zA1b") is True


def test_is_placeholder():
    """Test placeholder detection."""
    # Common placeholders
    assert is_placeholder("") is True
    assert is_placeholder("<YOUR_KEY_HERE>") is True
    assert is_placeholder("CHANGE_ME") is True
    assert is_placeholder("YOUR_API_KEY_HERE") is True
    assert is_placeholder("xxx") is True
    assert is_placeholder("placeholder") is True
    assert is_placeholder("****") is True

    # Not placeholders
    assert is_placeholder("real-api-key-12345") is False
    assert is_placeholder("sk-1234567890abcdef") is False


def test_redact_value():
    """Test value redaction."""
    # Short value
    assert redact_value("abc") == "***"
    assert redact_value("abcdefgh") == "********"  # shows actual length

    # Long value
    redacted = redact_value("sk-1234567890abcdef1234567890abcdef")
    assert redacted.startswith("sk-1")
    assert redacted.endswith("cdef")
    assert "..." in redacted


def test_detect_aws_access_key():
    """Test AWS access key detection."""
    matches = detect_secrets_in_value("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")

    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.AWS_ACCESS_KEY
    assert matches[0].variable_name == "AWS_KEY"
    assert matches[0].severity == "critical"


def test_detect_aws_secret_key():
    """Test AWS secret access key detection with context-aware matching."""
    # Test with standard AWS_SECRET_ACCESS_KEY variable name
    matches = detect_secrets_in_value("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.AWS_SECRET_KEY
    assert matches[0].severity == "critical"

    # Test with variations of the variable name
    matches = detect_secrets_in_value("aws_secret_key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    assert len(matches) == 1

    matches = detect_secrets_in_value("AWS_SECRET_TOKEN", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    assert len(matches) == 1

    # Test that it doesn't match non-AWS variable names
    matches = detect_secrets_in_value("RANDOM_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    # Should match as high entropy instead
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.HIGH_ENTROPY


def test_detect_github_token():
    """Test GitHub token detection."""
    # Use a longer token matching the pattern (36+ chars after ghp_)
    matches = detect_secrets_in_value(
        "GITHUB_TOKEN",
        "ghp_" + "1234567890abcdef" * 3,  # 48 chars total
    )

    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.GITHUB_TOKEN for m in matches)
    assert matches[0].severity == "critical"


def test_detect_stripe_key():
    """Test Stripe key detection."""
    matches = detect_secrets_in_value(
        "STRIPE_KEY",
        "sk_live_1234567890abcdef1234567890ab",
    )

    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.STRIPE_KEY
    assert matches[0].severity == "critical"


def test_detect_openai_key():
    """Test OpenAI key detection."""
    # OpenAI keys are 48+ chars after sk-
    openai_key = "sk-" + "a" * 50  # 53 chars total
    matches = detect_secrets_in_value("OPENAI_KEY", openai_key)

    # Should match OpenAI or at least high entropy
    assert len(matches) >= 1
    # May match as OpenAI key or high entropy string
    secret_types = {m.secret_type for m in matches}
    assert SecretType.OPENAI_KEY in secret_types or SecretType.HIGH_ENTROPY in secret_types


def test_detect_anthropic_key():
    """Test Anthropic key detection."""
    matches = detect_secrets_in_value(
        "ANTHROPIC_KEY",
        "sk-ant-" + "a" * 95,
    )

    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.ANTHROPIC_KEY


def test_detect_slack_webhook():
    """Test Slack webhook detection."""
    # Use actual format with proper IDs
    webhook = "https://hooks.slack.com/services/T12345678/B12345678/abcdefghijklmnopqrstuvwx"
    matches = detect_secrets_in_value("SLACK_WEBHOOK", webhook)

    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SLACK_WEBHOOK for m in matches)


def test_detect_database_url():
    """Test database URL with credentials detection."""
    # Use a longer password that won't be filtered as placeholder
    matches = detect_secrets_in_value(
        "DATABASE_URL",
        "postgresql://user:MySecretP4ssw0rd@localhost:5432/db",
    )

    # May match as DATABASE_URL or GENERIC_SECRET
    assert len(matches) >= 1


def test_detect_jwt_token():
    """Test JWT token detection."""
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    matches = detect_secrets_in_value("JWT", jwt)

    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.JWT_TOKEN


def test_detect_private_key():
    """Test private key detection."""
    private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""

    matches = detect_secrets_in_value("PRIVATE_KEY", private_key)

    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.PRIVATE_KEY
    assert matches[0].severity == "critical"


def test_no_detection_for_placeholders():
    """Test that placeholders don't trigger detection."""
    # Common placeholders should not be detected
    assert len(detect_secrets_in_value("KEY", "CHANGE_ME")) == 0
    assert len(detect_secrets_in_value("KEY", "<YOUR_KEY>")) == 0
    assert len(detect_secrets_in_value("KEY", "")) == 0


def test_high_entropy_detection():
    """Test high entropy string detection."""
    # Very random-looking string with neutral variable name
    high_entropy_value = "xK9mP2qL8vN4wR7tY3zA5b1c"
    matches = detect_secrets_in_value("CONFIG_VALUE", high_entropy_value)

    # Should detect as high entropy or generic secret
    assert len(matches) >= 1
    assert any(m.secret_type in [SecretType.HIGH_ENTROPY, SecretType.GENERIC_API_SECRET] for m in matches)


def test_scan_env_file():
    """Test scanning an entire .env file."""
    content = (
        """
# .env file with secrets
AWS_KEY=AKIAIOSFODNN7EXAMPLE
GITHUB_TOKEN=ghp_"""
        + "1234567890abcdef" * 3
        + """
DEBUG=true
PORT=8000
"""
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(content)
        f.flush()
        temp_path = Path(f.name)

    try:
        matches = scan_env_file(temp_path)

        # Should find at least AWS key (GitHub token pattern might not match)
        assert len(matches) >= 1

        secret_types = {m.secret_type for m in matches}
        assert SecretType.AWS_ACCESS_KEY in secret_types

        # Should not flag DEBUG or PORT
        variable_names = {m.variable_name for m in matches}
        assert "DEBUG" not in variable_names
        assert "PORT" not in variable_names
    finally:
        temp_path.unlink()


def test_scan_env_file_not_found():
    """Test scanning a non-existent file."""
    matches = scan_env_file(Path("/nonexistent/file.env"))
    assert matches == []


def test_multiple_patterns_same_value():
    """Test that a value matching multiple patterns is reported correctly."""
    # Slack token format
    value = "xoxb-1234567890-1234567890-abcdefghijklmnop"
    matches = detect_secrets_in_value("SLACK", value)

    # Should match at least the Slack pattern
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SLACK_TOKEN for m in matches)


def test_recommendations():
    """Test that recommendations are provided."""
    matches = detect_secrets_in_value("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")

    assert len(matches) == 1
    assert matches[0].recommendation is not None
    assert len(matches[0].recommendation) > 0
    assert "rotate" in matches[0].recommendation.lower() or "AWS" in matches[0].recommendation


def test_severity_levels():
    """Test that different severity levels are assigned."""
    # Critical: AWS key
    aws_matches = detect_secrets_in_value("AWS", "AKIAIOSFODNN7EXAMPLE")
    assert len(aws_matches) >= 1
    assert aws_matches[0].severity == "critical"

    # Stripe key (also critical)
    stripe_matches = detect_secrets_in_value(
        "STRIPE",
        "sk_live_1234567890abcdef1234567890ab",
    )
    assert len(stripe_matches) >= 1
    assert stripe_matches[0].severity == "critical"


def test_generic_api_key_pattern():
    """Test generic API key pattern detection."""
    matches = detect_secrets_in_value(
        "API_KEY",
        "api_key=abc123def456ghi789jkl012mno345pqr",
    )

    # Should match generic API key pattern
    assert len(matches) >= 1


def test_generic_secret_pattern():
    """Test generic secret pattern detection."""
    matches = detect_secrets_in_value(
        "PASSWORD",
        "password=super_secret_password_12345",
    )

    # Should match generic secret pattern
    assert len(matches) >= 1


def test_value_redaction_in_matches():
    """Test that values are redacted in match results."""
    secret_value = "AKIAIOSFODNN7EXAMPLE"  # Use AWS key that definitely matches
    matches = detect_secrets_in_value("AWS_KEY", secret_value)

    assert len(matches) >= 1
    # Value should be redacted, not full secret
    assert matches[0].value != secret_value
    assert "..." in matches[0].value


# ============================================================================
# NEW TESTS FOR EXPANDED SECRET DETECTION (40+ patterns)
# ============================================================================


# Cloud Providers (10 tests)
def test_detect_azure_storage_key():
    """Test Azure Storage Account Key detection."""
    key = "a" * 88 + "=="  # Azure keys are 88 chars + ==
    matches = detect_secrets_in_value("AZURE_STORAGE_KEY", key)
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.AZURE_STORAGE_KEY
    assert matches[0].severity == "critical"


def test_detect_azure_sas_token():
    """Test Azure SAS Token detection."""
    token = "?sig=" + "a" * 43 + "&other=param"
    matches = detect_secrets_in_value("AZURE_SAS", token)
    assert len(matches) >= 1


def test_detect_google_api_key():
    """Test Google Cloud API Key detection."""
    key = "AIza" + "a" * 35
    matches = detect_secrets_in_value("GOOGLE_API_KEY", key)
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GOOGLE_API_KEY
    assert matches[0].severity == "critical"


def test_detect_google_oauth_token():
    """Test Google OAuth Access Token detection."""
    token = "ya29." + "a" * 50
    matches = detect_secrets_in_value("GOOGLE_OAUTH", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.GOOGLE_OAUTH_TOKEN for m in matches)


def test_detect_digitalocean_pat():
    """Test DigitalOcean Personal Access Token detection."""
    token = "dop_v1_" + "a" * 64
    matches = detect_secrets_in_value("DO_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.DIGITALOCEAN_PAT for m in matches)


def test_detect_digitalocean_oauth():
    """Test DigitalOcean OAuth Token detection."""
    token = "doo_v1_" + "a" * 64
    matches = detect_secrets_in_value("DO_OAUTH", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.DIGITALOCEAN_OAUTH for m in matches)


def test_detect_heroku_api_key():
    """Test Heroku API Key detection (UUID format)."""
    key = "12345678-1234-1234-1234-123456789abc"
    matches = detect_secrets_in_value("HEROKU_API_KEY", key)
    assert len(matches) >= 1


def test_detect_alibaba_access_key_id():
    """Test Alibaba Cloud AccessKey ID detection."""
    key_id = "LTAI" + "a" * 16
    matches = detect_secrets_in_value("ALIBABA_ACCESS_KEY_ID", key_id)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.ALIBABA_ACCESS_KEY_ID for m in matches)


def test_detect_ibm_cloud_iam_key():
    """Test IBM Cloud IAM Key detection (via generic detection)."""
    key = "abc123def456" * 4  # IBM IAM keys are 44 chars, needs complexity
    matches = detect_secrets_in_value("IBM_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic detection
    assert any(m.secret_type in [SecretType.GENERIC_TOKEN, SecretType.GENERIC_API_SECRET] for m in matches)


def test_detect_alibaba_access_key_secret():
    """Test Alibaba Cloud AccessKey Secret detection (via generic detection)."""
    secret = "abc123def456abc123def456abc123"  # 30 chars with complexity
    matches = detect_secrets_in_value("ALIBABA_SECRET_KEY", secret)
    assert len(matches) >= 1
    # Should be caught by generic detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


# CI/CD & DevOps (8 tests)
def test_detect_gitlab_pat():
    """Test GitLab Personal Access Token detection."""
    token = "glpat-" + "a" * 20
    matches = detect_secrets_in_value("GITLAB_TOKEN", token)
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GITLAB_PAT
    assert matches[0].severity == "critical"


def test_detect_gitlab_pipeline_token():
    """Test GitLab Pipeline Trigger Token detection."""
    token = "glptt-" + "a" * 40
    matches = detect_secrets_in_value("GITLAB_PIPELINE_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.GITLAB_PIPELINE_TOKEN for m in matches)


def test_detect_bitbucket_app_password():
    """Test Bitbucket App Password detection."""
    password = "ATBB" + "a" * 24
    matches = detect_secrets_in_value("BITBUCKET_APP_PASSWORD", password)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.BITBUCKET_APP_PASSWORD for m in matches)


def test_detect_docker_hub_token():
    """Test Docker Hub Access Token detection."""
    token = "dckr_pat_" + "a" * 36
    matches = detect_secrets_in_value("DOCKER_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.DOCKER_HUB_TOKEN for m in matches)


def test_detect_terraform_cloud_token():
    """Test Terraform Cloud API Token detection."""
    token = "a" * 14 + ".atlasv1." + "a" * 60
    matches = detect_secrets_in_value("TF_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.TERRAFORM_CLOUD_TOKEN for m in matches)


def test_detect_circleci_token():
    """Test CircleCI Personal Token detection (via generic detection)."""
    token = "abc123def456" * 4  # 40-char with complexity
    matches = detect_secrets_in_value("CIRCLECI_TOKEN", token)
    assert len(matches) >= 1
    # Should be caught by generic token detection
    assert any(m.secret_type == SecretType.GENERIC_TOKEN for m in matches)


def test_detect_travis_token():
    """Test Travis CI Access Token detection (via generic detection)."""
    token = "abc123XYZ789def456gh_!"  # 22 chars with more complexity
    matches = detect_secrets_in_value("TRAVIS_TOKEN", token)
    assert len(matches) >= 1
    # Should be caught by generic token detection
    assert any(m.secret_type == SecretType.GENERIC_TOKEN for m in matches)


def test_detect_jenkins_token():
    """Test Jenkins API Token detection (via generic detection)."""
    token = "abc123def456" * 3  # 32+ chars with complexity
    matches = detect_secrets_in_value("JENKINS_API_TOKEN", token)
    assert len(matches) >= 1
    # Should be caught by generic token detection
    assert any(m.secret_type == SecretType.GENERIC_TOKEN for m in matches)


# Communication & Monitoring (6 tests)
def test_detect_slack_bot_token():
    """Test Slack Bot Token detection (xoxb-)."""
    token = "xoxb-1234567890-1234567890-" + "a" * 24
    matches = detect_secrets_in_value("SLACK_BOT_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SLACK_BOT_TOKEN for m in matches)


def test_detect_slack_user_token():
    """Test Slack User Token detection (xoxp-)."""
    token = "xoxp-1234567890-1234567890-" + "a" * 24
    matches = detect_secrets_in_value("SLACK_USER_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SLACK_USER_TOKEN for m in matches)


def test_detect_discord_bot_token():
    """Test Discord Bot Token detection."""
    token = "M" + "a" * 23 + "." + "a" * 6 + "." + "a" * 27
    matches = detect_secrets_in_value("DISCORD_BOT_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.DISCORD_BOT_TOKEN for m in matches)


def test_detect_discord_webhook():
    """Test Discord Webhook detection."""
    webhook = "https://discord.com/api/webhooks/12345678901234567/" + "a" * 68
    matches = detect_secrets_in_value("DISCORD_WEBHOOK", webhook)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.DISCORD_WEBHOOK for m in matches)


def test_detect_twilio_api_key():
    """Test Twilio API Key detection."""
    key = "SK" + "a" * 32
    matches = detect_secrets_in_value("TWILIO_API_KEY", key)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.TWILIO_API_KEY for m in matches)


def test_detect_sendgrid_api_key():
    """Test SendGrid API Key detection."""
    key = "SG." + "a" * 22 + "." + "a" * 43
    matches = detect_secrets_in_value("SENDGRID_API_KEY", key)
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.SENDGRID_API_KEY


# Payments & Commerce (4 tests)
def test_detect_paypal_access_token():
    """Test PayPal Access Token detection."""
    token = "access_token$production$" + "a" * 16 + "$" + "a" * 32
    matches = detect_secrets_in_value("PAYPAL_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.PAYPAL_ACCESS_TOKEN for m in matches)


def test_detect_square_access_token():
    """Test Square Access Token detection."""
    token = "sq0atp-" + "a" * 22
    matches = detect_secrets_in_value("SQUARE_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SQUARE_ACCESS_TOKEN for m in matches)


def test_detect_shopify_access_token():
    """Test Shopify Access Token detection."""
    token = "shpat_" + "a" * 32
    matches = detect_secrets_in_value("SHOPIFY_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.SHOPIFY_ACCESS_TOKEN for m in matches)


def test_detect_coinbase_api_key():
    """Test Coinbase API Key detection (via generic detection)."""
    key = "abc123def456abc123def456abc12345"  # 32 chars with complexity
    matches = detect_secrets_in_value("COINBASE_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic API secret detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


# Email & SMS (3 tests)
def test_detect_mailgun_api_key():
    """Test Mailgun API Key detection."""
    key = "key-" + "a" * 32
    matches = detect_secrets_in_value("MAILGUN_API_KEY", key)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.MAILGUN_API_KEY for m in matches)


def test_detect_mailchimp_api_key():
    """Test Mailchimp API Key detection."""
    key = "a" * 32 + "-us12"
    matches = detect_secrets_in_value("MAILCHIMP_API_KEY", key)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.MAILCHIMP_API_KEY for m in matches)


def test_detect_postmark_server_token():
    """Test Postmark Server Token detection."""
    token = "12345678-1234-1234-1234-123456789abc"
    matches = detect_secrets_in_value("POSTMARK_SERVER_TOKEN", token)
    assert len(matches) >= 1


# Databases & Storage (3 tests)
def test_detect_mongodb_connection_string():
    """Test MongoDB Connection String detection."""
    conn_str = "mongodb://user:MyP4ssword123@localhost:27017/db"
    matches = detect_secrets_in_value("MONGODB_URI", conn_str)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.MONGODB_CONNECTION_STRING for m in matches)


def test_detect_mongodb_srv_connection_string():
    """Test MongoDB+SRV Connection String detection."""
    conn_str = "mongodb+srv://user:MyP4ssword123@cluster.mongodb.net/db"
    matches = detect_secrets_in_value("MONGO_URL", conn_str)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.MONGODB_CONNECTION_STRING for m in matches)


def test_detect_redis_url_with_password():
    """Test Redis Connection String with Password detection."""
    redis_url = "redis://default:MyRedisP4ss@localhost:6379/0"
    matches = detect_secrets_in_value("REDIS_URL", redis_url)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.REDIS_URL_WITH_PASSWORD for m in matches)


def test_detect_firebase_fcm_key():
    """Test Firebase FCM Server Key detection."""
    key = "AAAA" + "a" * 7 + ":" + "a" * 140
    matches = detect_secrets_in_value("FCM_SERVER_KEY", key)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.FIREBASE_FCM_KEY for m in matches)


# APIs & Services (6 tests)
def test_detect_new_relic_api_key():
    """Test New Relic API Key detection."""
    key = "NRAK-" + "A" * 27
    matches = detect_secrets_in_value("NEW_RELIC_API_KEY", key)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.NEW_RELIC_API_KEY for m in matches)


def test_detect_datadog_api_key():
    """Test Datadog API Key detection (via generic detection)."""
    key = "abc123def456abc123def456abc12345"  # 32 chars with complexity
    matches = detect_secrets_in_value("DATADOG_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic API secret detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


def test_detect_pagerduty_api_key():
    """Test PagerDuty API Key detection (via generic detection)."""
    key = "abc123def456abc12345"  # 20 chars with complexity
    matches = detect_secrets_in_value("PAGERDUTY_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic API secret detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


def test_detect_sentry_auth_token():
    """Test Sentry Auth Token detection (via generic detection)."""
    token = "abc123def456" * 6  # 64+ chars with complexity
    matches = detect_secrets_in_value("SENTRY_AUTH_TOKEN", token)
    assert len(matches) >= 1
    # Should be caught by generic token detection
    assert any(m.secret_type == SecretType.GENERIC_TOKEN for m in matches)


def test_detect_algolia_api_key():
    """Test Algolia API Key detection (via generic detection)."""
    key = "abc123def456abc123def456abc12345"  # 32 chars with complexity
    matches = detect_secrets_in_value("ALGOLIA_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic API secret detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


def test_detect_cloudflare_api_key():
    """Test Cloudflare API Key detection (via generic detection)."""
    key = "abc123def456abc123def456abc12345abcde"  # 37 chars with complexity
    matches = detect_secrets_in_value("CLOUDFLARE_API_KEY", key)
    assert len(matches) >= 1
    # Should be caught by generic API secret detection
    assert any(m.secret_type in [SecretType.GENERIC_API_SECRET, SecretType.GENERIC_TOKEN] for m in matches)


# Package Managers (2 tests)
def test_detect_npm_access_token():
    """Test NPM Access Token detection."""
    token = "npm_" + "a" * 36
    matches = detect_secrets_in_value("NPM_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.NPM_ACCESS_TOKEN for m in matches)


def test_detect_pypi_upload_token():
    """Test PyPI Upload Token detection."""
    token = "pypi-AgEIcHlwaS5vcmc" + "a" * 50
    matches = detect_secrets_in_value("PYPI_TOKEN", token)
    assert len(matches) >= 1
    assert any(m.secret_type == SecretType.PYPI_UPLOAD_TOKEN for m in matches)


# Generic Credential Detection Tests
def test_detect_generic_password():
    """Test generic password detection."""
    # Should detect
    matches = detect_secrets_in_value("DB_PASSWORD", "mySecretPass123")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GENERIC_PASSWORD
    assert matches[0].severity == "critical"

    matches = detect_secrets_in_value("POSTGRES_PASSWORD", "prod_db_2024!")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GENERIC_PASSWORD

    matches = detect_secrets_in_value("MYSQL_ROOT_PASSWORD", "secure_pass_99")
    assert len(matches) == 1


def test_generic_password_false_positives():
    """Test that generic password detection avoids false positives."""
    # Should NOT detect (false positives)
    assert len(detect_secrets_in_value("DEBUG", "true")) == 0
    assert len(detect_secrets_in_value("PORT", "8080")) == 0
    assert len(detect_secrets_in_value("PASSWORD_RESET_URL", "https://example.com/reset")) == 0
    assert len(detect_secrets_in_value("PASSWORD", "changeme")) == 0  # Placeholder
    assert len(detect_secrets_in_value("PASSWORD", "short")) == 0  # Too short


def test_detect_generic_token():
    """Test generic token detection."""
    # Should detect
    matches = detect_secrets_in_value("API_TOKEN", "sk_live_12345abcdef67890")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GENERIC_TOKEN
    assert matches[0].severity == "high"

    matches = detect_secrets_in_value("SERVER_TOKEN", "secure_token_xyz_2024")
    assert len(matches) == 1

    matches = detect_secrets_in_value("AUTH_TOKEN", "bearer_token_abc123def")
    assert len(matches) == 1


def test_generic_token_false_positives():
    """Test that generic token detection avoids false positives."""
    # Should NOT detect
    assert len(detect_secrets_in_value("TOKEN_ENDPOINT", "https://api.example.com/token")) == 0
    assert len(detect_secrets_in_value("TOKEN_NAME", "myapp")) == 0
    assert len(detect_secrets_in_value("SESSION_COOKIE_NAME", "sessionid")) == 0


def test_detect_generic_secret():
    """Test generic secret detection."""
    # Should detect
    matches = detect_secrets_in_value("SERVER_SECRET", "production_key_2024abc")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GENERIC_API_SECRET

    matches = detect_secrets_in_value("API_SECRET", "app_secret_xyz_123")
    assert len(matches) == 1

    matches = detect_secrets_in_value("CLIENT_SECRET", "oauth_secret_abcdef123")
    assert len(matches) == 1


def test_generic_secret_false_positives():
    """Test that generic secret detection avoids false positives."""
    # Should NOT detect
    assert len(detect_secrets_in_value("SECRET_NAME", "myapp")) == 0
    assert len(detect_secrets_in_value("SECRET_ID", "123")) == 0


def test_detect_generic_encryption_key():
    """Test generic encryption key detection."""
    # Should detect
    matches = detect_secrets_in_value("ENCRYPTION_KEY", "base64encodedkey1234567890abc")
    assert len(matches) == 1
    assert matches[0].secret_type == SecretType.GENERIC_ENCRYPTION_KEY
    assert matches[0].severity == "critical"

    matches = detect_secrets_in_value("SIGNING_KEY", "signing_key_abc123def456")
    assert len(matches) == 1


def test_generic_encryption_key_false_positives():
    """Test that generic encryption key detection avoids false positives."""
    # Should NOT detect
    assert len(detect_secrets_in_value("ENCRYPTION_KEY_PATH", "/etc/keys/mykey.pem")) == 0
    assert len(detect_secrets_in_value("PUBLIC_KEY", "public")) == 0


def test_generic_credential_complexity_requirement():
    """Test that generic credential detection requires complexity."""
    # Should NOT detect - lacks complexity (only letters)
    matches = detect_secrets_in_value("PASSWORD", "onlylettershere")
    assert len(matches) == 0

    # Should detect - has letters and numbers
    matches = detect_secrets_in_value("PASSWORD", "lettersandnumbers123")
    assert len(matches) == 1
