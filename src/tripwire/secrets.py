"""Secret detection for environment files.

This module provides pattern-based detection of secrets and sensitive data
in .env files and git history to prevent accidental commits.
"""

import math
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict

# Resource limits to prevent DOS attacks
MAX_ENTROPY_STRING_LENGTH = 10_000  # 10KB max for entropy calculation
MAX_SECRET_VALUE_LENGTH = 10_000  # 10KB max for secret detection


class SecretType(Enum):
    """Types of secrets that can be detected."""

    # Existing patterns
    AWS_ACCESS_KEY = "AWS Access Key"
    AWS_SECRET_KEY = "AWS Secret Key"
    GITHUB_TOKEN = "GitHub Token"
    GITHUB_PAT = "GitHub Personal Access Token"
    SLACK_TOKEN = "Slack Token"
    SLACK_WEBHOOK = "Slack Webhook URL"
    STRIPE_KEY = "Stripe API Key"
    OPENAI_KEY = "OpenAI API Key"
    ANTHROPIC_KEY = "Anthropic API Key"
    PRIVATE_KEY = "Private Key"
    GENERIC_API_KEY = "Generic API Key"
    GENERIC_SECRET = "Generic Secret"
    JWT_TOKEN = "JWT Token"
    DATABASE_URL = "Database URL with Credentials"
    HIGH_ENTROPY = "High Entropy String"

    # Cloud Providers
    AZURE_STORAGE_KEY = "Azure Storage Account Key"
    AZURE_SAS_TOKEN = "Azure SAS Token"
    GOOGLE_API_KEY = "Google Cloud API Key"
    GOOGLE_OAUTH_TOKEN = "Google OAuth Access Token"
    DIGITALOCEAN_PAT = "DigitalOcean Personal Access Token"
    DIGITALOCEAN_OAUTH = "DigitalOcean OAuth Token"
    HEROKU_API_KEY = "Heroku API Key"
    ALIBABA_ACCESS_KEY_ID = "Alibaba Cloud AccessKey ID"
    ALIBABA_ACCESS_KEY_SECRET = "Alibaba Cloud AccessKey Secret"
    IBM_CLOUD_IAM_KEY = "IBM Cloud IAM Key"

    # CI/CD & DevOps
    CIRCLECI_TOKEN = "CircleCI Personal Token"
    TRAVIS_TOKEN = "Travis CI Access Token"
    JENKINS_TOKEN = "Jenkins API Token"
    GITLAB_PAT = "GitLab Personal Access Token"
    GITLAB_PIPELINE_TOKEN = "GitLab Pipeline Trigger Token"
    BITBUCKET_APP_PASSWORD = "Bitbucket App Password"
    DOCKER_HUB_TOKEN = "Docker Hub Access Token"
    TERRAFORM_CLOUD_TOKEN = "Terraform Cloud API Token"

    # Communication & Monitoring
    SLACK_BOT_TOKEN = "Slack Bot Token"
    SLACK_USER_TOKEN = "Slack User Token"
    DISCORD_BOT_TOKEN = "Discord Bot Token"
    DISCORD_WEBHOOK = "Discord Webhook"
    TWILIO_API_KEY = "Twilio API Key"
    SENDGRID_API_KEY = "SendGrid API Key"

    # Payments & Commerce
    PAYPAL_ACCESS_TOKEN = "PayPal Access Token"
    SQUARE_ACCESS_TOKEN = "Square Access Token"
    COINBASE_API_KEY = "Coinbase API Key"
    SHOPIFY_ACCESS_TOKEN = "Shopify Access Token"

    # Email & SMS
    MAILGUN_API_KEY = "Mailgun API Key"
    MAILCHIMP_API_KEY = "Mailchimp API Key"
    POSTMARK_SERVER_TOKEN = "Postmark Server Token"

    # Databases & Storage
    MONGODB_CONNECTION_STRING = "MongoDB Connection String"
    REDIS_URL_WITH_PASSWORD = "Redis Connection String"
    FIREBASE_FCM_KEY = "Firebase Cloud Messaging Server Key"

    # APIs & Services
    DATADOG_API_KEY = "Datadog API Key"
    NEW_RELIC_API_KEY = "New Relic API Key"
    PAGERDUTY_API_KEY = "PagerDuty API Key"
    SENTRY_AUTH_TOKEN = "Sentry Auth Token"
    ALGOLIA_API_KEY = "Algolia API Key"
    CLOUDFLARE_API_KEY = "Cloudflare API Key"

    # Package Managers
    NPM_ACCESS_TOKEN = "NPM Access Token"
    PYPI_UPLOAD_TOKEN = "PyPI Upload Token"

    # Generic Credential Detection
    GENERIC_PASSWORD = "Generic Password"
    GENERIC_TOKEN = "Generic Token"
    GENERIC_API_SECRET = "Generic API Secret"
    GENERIC_ENCRYPTION_KEY = "Generic Encryption Key"


@dataclass
class SecretPattern:
    """Pattern for detecting a specific type of secret.

    Attributes:
        secret_type: Type of secret
        pattern: Regex pattern to match
        description: Human-readable description
        severity: Severity level (critical, high, medium, low)
        min_entropy: Minimum entropy threshold (for entropy-based detection)
    """

    secret_type: SecretType
    pattern: str
    description: str
    severity: str
    min_entropy: Optional[float] = None


@dataclass
class SecretMatch:
    """Information about a detected secret.

    Attributes:
        secret_type: Type of secret detected
        variable_name: Environment variable name
        value: The detected secret value (may be redacted)
        line_number: Line number in file
        severity: Severity level
        recommendation: Remediation recommendation
    """

    secret_type: SecretType
    variable_name: str
    value: str
    line_number: int
    severity: str
    recommendation: str


class CredentialPattern(TypedDict):
    """Type definition for credential pattern dictionaries."""

    type: SecretType
    keywords: List[str]
    min_length: int
    min_entropy: float
    severity: str
    exclude_keywords: List[str]


# Secret detection patterns (patterns as strings for documentation)
SECRET_PATTERNS: List[SecretPattern] = [
    # AWS Keys
    SecretPattern(
        secret_type=SecretType.AWS_ACCESS_KEY,
        pattern=r"AKIA[0-9A-Z]{16}",
        description="AWS Access Key ID",
        severity="critical",
    ),
    # NOTE: AWS_SECRET_KEY detection moved to context-aware detection in detect_secrets_in_value()
    # The pattern below only works for raw file scanning (git history), not parsed .env values
    SecretPattern(
        secret_type=SecretType.AWS_SECRET_KEY,
        pattern=r"aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        description="AWS Secret Access Key (for git history scanning)",
        severity="critical",
    ),
    # GitHub Tokens
    SecretPattern(
        secret_type=SecretType.GITHUB_TOKEN,
        # Fixed ReDoS: Added upper bound (GitHub tokens are typically 36-255 chars)
        pattern=r"gh[pousr]_[0-9a-zA-Z]{36,255}",
        description="GitHub Token (OAuth, Personal, User, etc.)",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.GITHUB_PAT,
        pattern=r"github_pat_[0-9a-zA-Z_]{82}",
        description="GitHub Personal Access Token (Fine-grained)",
        severity="critical",
    ),
    # Slack Tokens
    SecretPattern(
        secret_type=SecretType.SLACK_TOKEN,
        pattern=r"xox[baprs]-[0-9a-zA-Z]{10,72}",
        description="Slack Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.SLACK_WEBHOOK,
        # Fixed ReDoS: Added upper bounds to all quantifiers (max 13 for T/B IDs, max 256 for token)
        pattern=r"https://hooks\.slack\.com/services/T[0-9A-Z]{8,13}/B[0-9A-Z]{8,13}/[0-9a-zA-Z]{24,256}",
        description="Slack Webhook URL",
        severity="high",
    ),
    # Stripe Keys
    SecretPattern(
        secret_type=SecretType.STRIPE_KEY,
        # Fixed ReDoS: Added upper bound (Stripe keys are typically 24-128 chars)
        pattern=r"sk_live_[0-9a-zA-Z]{24,128}",
        description="Stripe Live Secret Key",
        severity="critical",
    ),
    # AI API Keys
    SecretPattern(
        secret_type=SecretType.OPENAI_KEY,
        # Fixed ReDoS: Added upper bound (OpenAI keys are typically 48-256 chars)
        pattern=r"sk-[a-zA-Z0-9]{48,256}",
        description="OpenAI API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.ANTHROPIC_KEY,
        # Fixed ReDoS: Added upper bound (Anthropic keys are typically 95-256 chars)
        pattern=r"sk-ant-[a-zA-Z0-9\-]{95,256}",
        description="Anthropic API Key",
        severity="high",
    ),
    # Private Keys
    SecretPattern(
        secret_type=SecretType.PRIVATE_KEY,
        pattern=r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        description="Private Key",
        severity="critical",
    ),
    # JWT Tokens
    SecretPattern(
        secret_type=SecretType.JWT_TOKEN,
        # Fixed ReDoS: Added upper bounds (JWT segments are typically 10-4096 chars each)
        pattern=r"eyJ[A-Za-z0-9_-]{10,4096}\.[A-Za-z0-9_-]{10,4096}\.[A-Za-z0-9_-]{10,4096}",
        description="JWT Token",
        severity="medium",
    ),
    # Database URLs with credentials
    SecretPattern(
        secret_type=SecretType.DATABASE_URL,
        pattern=r"(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@",
        description="Database URL with embedded credentials",
        severity="high",
    ),
    # Cloud Providers
    SecretPattern(
        secret_type=SecretType.AZURE_STORAGE_KEY,
        pattern=r"[a-zA-Z0-9+/]{88}==",
        description="Azure Storage Account Key",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.AZURE_SAS_TOKEN,
        pattern=r"(\?|&)sig=[a-zA-Z0-9%]{43,53}(&|$)",
        description="Azure SAS Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.GOOGLE_API_KEY,
        pattern=r"AIza[0-9A-Za-z_-]{35}",
        description="Google Cloud API Key",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.GOOGLE_OAUTH_TOKEN,
        pattern=r"ya29\.[0-9A-Za-z_-]+",
        description="Google OAuth Access Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.DIGITALOCEAN_PAT,
        pattern=r"dop_v1_[a-f0-9]{64}",
        description="DigitalOcean Personal Access Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.DIGITALOCEAN_OAUTH,
        pattern=r"doo_v1_[a-f0-9]{64}",
        description="DigitalOcean OAuth Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.HEROKU_API_KEY,
        pattern=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        description="Heroku API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.ALIBABA_ACCESS_KEY_ID,
        pattern=r"LTAI[A-Za-z0-9]{12,20}",
        description="Alibaba Cloud AccessKey ID",
        severity="critical",
    ),
    # NOTE: Alibaba, IBM, CircleCI, Travis, Jenkins patterns are too generic
    # They will be caught by generic credential detection with variable name context
    SecretPattern(
        secret_type=SecretType.GITLAB_PAT,
        # Fixed ReDoS: Added upper bound (GitLab PATs are typically 20-255 chars)
        pattern=r"glpat-[0-9a-zA-Z_-]{20,255}",
        description="GitLab Personal Access Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.GITLAB_PIPELINE_TOKEN,
        pattern=r"glptt-[0-9a-f]{40}",
        description="GitLab Pipeline Trigger Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.BITBUCKET_APP_PASSWORD,
        # Fixed ReDoS: Added upper bound (Bitbucket app passwords are typically 24-128 chars)
        pattern=r"ATBB[a-zA-Z0-9]{24,128}",
        description="Bitbucket App Password",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.DOCKER_HUB_TOKEN,
        # Fixed ReDoS: Added upper bound (Docker Hub PATs are typically 36-255 chars)
        pattern=r"dckr_pat_[a-zA-Z0-9_-]{36,255}",
        description="Docker Hub Access Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.TERRAFORM_CLOUD_TOKEN,
        # Fixed ReDoS: Added upper bound (Terraform tokens are typically 60-255 chars)
        pattern=r"[a-zA-Z0-9]{14}\.atlasv1\.[a-zA-Z0-9_-]{60,255}",
        description="Terraform Cloud API Token",
        severity="high",
    ),
    # Communication & Monitoring
    SecretPattern(
        secret_type=SecretType.SLACK_BOT_TOKEN,
        # Fixed ReDoS: Added upper bound (Slack bot tokens are typically 24-256 chars)
        pattern=r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,256}",
        description="Slack Bot Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.SLACK_USER_TOKEN,
        # Fixed ReDoS: Added upper bound (Slack user tokens are typically 24-256 chars)
        pattern=r"xoxp-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,256}",
        description="Slack User Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.DISCORD_BOT_TOKEN,
        # Fixed ReDoS: Added upper bound (Discord tokens are typically 27-256 chars)
        pattern=r"[MN][A-Za-z\d]{23}\.[A-Za-z\d_-]{6}\.[A-Za-z\d_-]{27,256}",
        description="Discord Bot Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.DISCORD_WEBHOOK,
        pattern=r"https://discord(?:app)?\.com/api/webhooks/[0-9]{17,19}/[a-zA-Z0-9_-]{68}",
        description="Discord Webhook",
        severity="medium",
    ),
    SecretPattern(
        secret_type=SecretType.TWILIO_API_KEY,
        pattern=r"SK[a-z0-9]{32}",
        description="Twilio API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.SENDGRID_API_KEY,
        pattern=r"SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}",
        description="SendGrid API Key",
        severity="high",
    ),
    # Payments & Commerce
    SecretPattern(
        secret_type=SecretType.PAYPAL_ACCESS_TOKEN,
        pattern=r"access_token\$production\$[a-z0-9]{16}\$[a-f0-9]{32}",
        description="PayPal Access Token",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.SQUARE_ACCESS_TOKEN,
        # Fixed ReDoS: Added upper bound (Square tokens are typically 22-128 chars)
        pattern=r"sq0atp-[0-9A-Za-z_-]{22,128}",
        description="Square Access Token",
        severity="critical",
    ),
    # NOTE: Coinbase pattern is too generic - will be caught by generic detection
    SecretPattern(
        secret_type=SecretType.SHOPIFY_ACCESS_TOKEN,
        pattern=r"shpat_[a-fA-F0-9]{32}",
        description="Shopify Access Token",
        severity="critical",
    ),
    # Email & SMS
    SecretPattern(
        secret_type=SecretType.MAILGUN_API_KEY,
        pattern=r"key-[a-z0-9]{32}",
        description="Mailgun API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.MAILCHIMP_API_KEY,
        pattern=r"[a-f0-9]{32}-us[0-9]{1,2}",
        description="Mailchimp API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.POSTMARK_SERVER_TOKEN,
        pattern=r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
        description="Postmark Server Token",
        severity="high",
    ),
    # Databases & Storage
    SecretPattern(
        secret_type=SecretType.MONGODB_CONNECTION_STRING,
        pattern=r"mongodb(\+srv)?://[^:]+:[^@]+@",
        description="MongoDB Connection String",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.REDIS_URL_WITH_PASSWORD,
        pattern=r"redis://[^:]*:[^@]+@",
        description="Redis Connection String with Password",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.FIREBASE_FCM_KEY,
        pattern=r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}",
        description="Firebase Cloud Messaging Server Key",
        severity="high",
    ),
    # APIs & Services
    SecretPattern(
        secret_type=SecretType.NEW_RELIC_API_KEY,
        pattern=r"NRAK-[A-Z0-9]{27}",
        description="New Relic API Key",
        severity="high",
    ),
    # NOTE: Datadog, PagerDuty, Sentry, Algolia, Cloudflare patterns are too generic
    # They will be caught by generic credential detection with variable name context
    # Package Managers
    SecretPattern(
        secret_type=SecretType.NPM_ACCESS_TOKEN,
        pattern=r"npm_[A-Za-z0-9]{36}",
        description="NPM Access Token",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.PYPI_UPLOAD_TOKEN,
        # Fixed ReDoS: Added upper bound (PyPI tokens are typically 50-512 chars)
        pattern=r"pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,512}",
        description="PyPI Upload Token",
        severity="critical",
    ),
    # Generic patterns (lower priority)
    SecretPattern(
        secret_type=SecretType.GENERIC_API_KEY,
        # Fixed ReDoS: Added upper bounds to quantifiers (max 1024 chars for API keys)
        pattern=r"(?i)(api[_-]?key|apikey|api[_-]?secret)\s{0,5}[=:]\s{0,5}['\"]?([0-9a-zA-Z_-]{32,1024})['\"]?",
        description="Generic API Key",
        severity="medium",
    ),
    SecretPattern(
        secret_type=SecretType.GENERIC_SECRET,
        # Fixed ReDoS: Added upper bounds (max 1024 chars for secrets)
        pattern=r"(?i)(secret|password|passwd|pwd)\s{0,5}[=:]\s{0,5}['\"]?([^\s'\"]{16,1024})['\"]?",
        description="Generic Secret or Password",
        severity="medium",
    ),
]

# Performance optimization: Pre-compile all secret patterns at module load time
# This provides 10-20x speedup compared to compiling patterns on every check
_COMPILED_SECRET_PATTERNS: List[Tuple[SecretType, re.Pattern[str], str, str]] = [
    (
        p.secret_type,
        re.compile(p.pattern, re.IGNORECASE | re.MULTILINE),
        p.severity,
        p.description,
    )
    for p in SECRET_PATTERNS
]


def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string.

    Args:
        data: String to analyze

    Returns:
        Entropy value (0.0 to 8.0 for byte data)
    """
    if not data:
        return 0.0

    # Security: Prevent DOS by limiting entropy calculation to first N chars
    # Sample first N chars instead of full string if too long
    if len(data) > MAX_ENTROPY_STRING_LENGTH:
        data = data[:MAX_ENTROPY_STRING_LENGTH]

    # Count frequency of each character
    freq: Dict[str, int] = {}
    for char in data:
        freq[char] = freq.get(char, 0) + 1

    # Calculate entropy
    entropy = 0.0
    length = len(data)

    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def is_high_entropy(value: str, threshold: float = 4.5) -> bool:
    """Check if a value has high entropy (likely random/secret).

    Args:
        value: Value to check
        threshold: Entropy threshold (default: 4.5)

    Returns:
        True if entropy is above threshold
    """
    # Ignore short values
    if len(value) < 20:
        return False

    # Ignore common placeholder patterns
    placeholder_patterns = [
        r"^[A-Z_]+$",  # UPPERCASE_ONLY
        r"^[a-z_]+$",  # lowercase_only
        r"^[0-9]+$",  # numbers only
        r"^(true|false|yes|no|none|null)$",  # common values
    ]

    for pattern in placeholder_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return False

    entropy = calculate_entropy(value)
    return entropy >= threshold


def detect_generic_credential(variable_name: str, value: str, line_number: int) -> Optional[SecretMatch]:
    """Detect generic credentials using smart heuristics.

    Detects credentials like:
    - DB_PASSWORD=mySecretPass123
    - SERVER_SECRET=production_key_2024
    - API_TOKEN=secure_token_xyz
    - ENCRYPTION_KEY=base64encodedkey
    - DB_PASSWORD=password (placeholder detection)
    - CREDENTIALS=your-credentials-here (placeholder detection)

    Uses a multi-factor approach:
    1. Placeholder detection for secret variables (v0.7.1+)
       - Detects common placeholders (password, your-*-here, etc.) when variable name contains secret keywords
       - Bypasses entropy/complexity checks for known placeholder patterns
    2. Variable name matching (PASSWORD, SECRET, TOKEN, KEY, CREDENTIALS, etc.)
    3. Value validation (length, entropy, format)
    4. Dynamic entropy thresholds based on credential type
    5. False positive filtering (DEBUG=true, PORT=8080, etc.)

    Args:
        variable_name: Environment variable name
        value: Environment variable value
        line_number: Line number in file

    Returns:
        SecretMatch if generic credential detected, None otherwise
    """
    # Normalize variable name for comparison
    var_name_upper = variable_name.upper()

    # Define credential type patterns with their characteristics
    credential_patterns: List[CredentialPattern] = [
        {
            "type": SecretType.GENERIC_PASSWORD,
            "keywords": ["PASSWORD", "PASSWD", "PWD"],
            "min_length": 8,
            "min_entropy": 3.0,
            "severity": "critical",
            "exclude_keywords": ["RESET", "PLACEHOLDER", "EXAMPLE"],
        },
        {
            "type": SecretType.GENERIC_TOKEN,
            "keywords": ["TOKEN", "ACCESS_TOKEN", "AUTH_TOKEN", "BEARER"],
            "min_length": 16,
            "min_entropy": 3.5,
            "severity": "high",
            "exclude_keywords": ["ENDPOINT", "URL", "NAME"],
        },
        {
            "type": SecretType.GENERIC_API_SECRET,
            "keywords": [
                "SECRET",
                "API_SECRET",
                "CLIENT_SECRET",
                "APP_SECRET",
                "API_KEY",
                "APIKEY",
                "CREDENTIALS",
                "CREDENTIAL",
            ],
            "min_length": 16,
            "min_entropy": 3.5,
            "severity": "high",
            "exclude_keywords": ["NAME", "ID", "ENDPOINT", "PATH", "FILE"],
        },
        {
            "type": SecretType.GENERIC_ENCRYPTION_KEY,
            "keywords": ["ENCRYPTION_KEY", "ENCRYPT_KEY", "PRIVATE_KEY", "SIGNING_KEY"],
            "min_length": 16,
            "min_entropy": 4.0,
            "severity": "critical",
            "exclude_keywords": ["PUBLIC", "PATH", "FILE"],
        },
    ]

    # Bug fix (v0.7.1): Detect placeholder values for secret variables
    # Common placeholders like "password", "your-api-key-here" have low entropy
    # but should still be marked as secrets based on variable name context

    # Special case: If value is a common placeholder AND variable name has secret keywords,
    # mark as secret regardless of entropy/complexity (these are placeholder values for secrets)
    common_placeholder_values = [
        "password",
        "secret",
        "token",
        "key",
        "credentials",
        "changeme",
        "change_me",
        "example",
        "placeholder",
        "your-password-here",
        "your-secret-here",
        "your-token-here",
        "your-key-here",
        "your-credentials-here",
    ]

    value_lower = value.lower()

    # Check for exact matches or pattern matches
    is_common_placeholder = (
        value_lower in common_placeholder_values
        or re.match(r"^your[-_].+[-_]here$", value_lower)
        or re.match(r"^(password|secret|token|key|credentials?)$", value_lower, re.IGNORECASE)
    )

    if is_common_placeholder:
        # Check if variable name contains ANY secret-related keyword
        all_keywords = [
            "PASSWORD",
            "PASSWD",
            "PWD",
            "TOKEN",
            "ACCESS_TOKEN",
            "AUTH_TOKEN",
            "SECRET",
            "API_SECRET",
            "CLIENT_SECRET",
            "API_KEY",
            "APIKEY",
            "CREDENTIALS",
            "CREDENTIAL",
            "ENCRYPTION_KEY",
            "PRIVATE_KEY",
        ]

        if any(keyword in var_name_upper for keyword in all_keywords):
            # Determine appropriate secret type and severity
            if any(kw in var_name_upper for kw in ["PASSWORD", "PASSWD", "PWD"]):
                secret_type = SecretType.GENERIC_PASSWORD
                severity = "critical"
            elif any(kw in var_name_upper for kw in ["TOKEN", "ACCESS_TOKEN", "AUTH_TOKEN"]):
                secret_type = SecretType.GENERIC_TOKEN
                severity = "high"
            elif any(kw in var_name_upper for kw in ["CREDENTIALS", "CREDENTIAL"]):
                secret_type = SecretType.GENERIC_API_SECRET
                severity = "high"
            elif any(kw in var_name_upper for kw in ["ENCRYPTION_KEY", "PRIVATE_KEY", "SIGNING_KEY"]):
                secret_type = SecretType.GENERIC_ENCRYPTION_KEY
                severity = "critical"
            else:
                secret_type = SecretType.GENERIC_API_SECRET
                severity = "high"

            return SecretMatch(
                secret_type=secret_type,
                variable_name=variable_name,
                value=redact_value(value),
                line_number=line_number,
                severity=severity,
                recommendation=get_recommendation(secret_type),
            )

    # False positive filters - common non-secret variable patterns
    false_positive_patterns = [
        # Boolean values
        r"^(true|false|yes|no|on|off|enabled?|disabled?)$",
        # Numbers only
        r"^[0-9]+$",
        # Common non-secret values
        r"^(debug|development|production|staging|test|local)$",
        # File paths
        r"^[./~].*",
        # URLs/domains (without credentials)
        r"^https?://[^:@]+$",
        r"^[a-z0-9.-]+\.[a-z]{2,}$",
        # Short alphanumeric identifiers
        r"^[a-zA-Z0-9_-]{1,7}$",
    ]

    # Check if value matches false positive patterns
    for pattern in false_positive_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return None

    # Check for placeholder values (more comprehensive)
    if is_placeholder(value):
        return None

    # Try to match credential patterns
    for cred_pattern in credential_patterns:
        # Check if any keyword matches the variable name
        keyword_match = any(keyword in var_name_upper for keyword in cred_pattern["keywords"])

        if not keyword_match:
            continue

        # Check for exclusion keywords
        has_exclusion = any(exclude in var_name_upper for exclude in cred_pattern["exclude_keywords"])
        if has_exclusion:
            continue

        # Check minimum length
        if len(value) < cred_pattern["min_length"]:
            continue

        # Check entropy
        entropy = calculate_entropy(value)
        if entropy < cred_pattern["min_entropy"]:
            continue

        # Additional validation: ensure value has some complexity
        # Must have at least 2 different character types (letters, numbers, special)
        has_letters = bool(re.search(r"[a-zA-Z]", value))
        has_numbers = bool(re.search(r"[0-9]", value))
        has_special = bool(re.search(r"[^a-zA-Z0-9]", value))

        char_type_count = sum([has_letters, has_numbers, has_special])
        if char_type_count < 2:
            continue

        # Matched! Create secret match
        return SecretMatch(
            secret_type=cred_pattern["type"],
            variable_name=variable_name,
            value=redact_value(value),
            line_number=line_number,
            severity=cred_pattern["severity"],
            recommendation=get_recommendation(cred_pattern["type"]),
        )

    # No generic credential detected
    return None


def detect_secrets_in_value(variable_name: str, value: str, line_number: int = 0) -> List[SecretMatch]:
    """Detect secrets in a single environment variable value.

    Detection order:
    1. Skip placeholders
    2. Context-aware detection (AWS secrets, etc.)
    3. Platform-specific pattern matching
    4. Generic credential detection (if no platform pattern matched)
    5. High-entropy detection (fallback)

    Args:
        variable_name: Name of the environment variable
        value: Value to scan
        line_number: Line number in file

    Returns:
        List of detected secrets
    """
    matches: List[SecretMatch] = []

    # Security: Prevent DOS by limiting value length
    if len(value) > MAX_SECRET_VALUE_LENGTH:
        # Skip detection for extremely long values (likely not secrets)
        return matches

    # Skip obvious placeholders
    if is_placeholder(value):
        return matches

    # Special case: AWS Secret Access Key (context-aware detection)
    # The pattern in SECRET_PATTERNS expects the variable name in the value,
    # but when scanning parsed .env files, we only get the value portion.
    # Use variable name as context to detect AWS secrets.
    if re.match(r"(?i)aws.*(secret|access).*(key|token)", variable_name):
        # AWS secret keys are exactly 40 characters: alphanumeric + / + =
        if re.match(r"^[A-Za-z0-9/+=]{40}$", value):
            matches.append(
                SecretMatch(
                    secret_type=SecretType.AWS_SECRET_KEY,
                    variable_name=variable_name,
                    value=redact_value(value),
                    line_number=line_number,
                    severity="critical",
                    recommendation=get_recommendation(SecretType.AWS_SECRET_KEY),
                )
            )
            # Return early to avoid duplicate detection
            return matches

    # Check each platform-specific pattern (using pre-compiled patterns for speed)
    for secret_type, compiled_pattern, severity, description in _COMPILED_SECRET_PATTERNS:
        match = compiled_pattern.search(value)
        if match:
            matches.append(
                SecretMatch(
                    secret_type=secret_type,
                    variable_name=variable_name,
                    value=redact_value(value),
                    line_number=line_number,
                    severity=severity,
                    recommendation=get_recommendation(secret_type),
                )
            )

    # If no platform-specific pattern matched, try generic credential detection
    # This catches credentials like DB_PASSWORD=mypass123, SERVER_TOKEN=abc...
    if not matches:
        generic_match = detect_generic_credential(variable_name, value, line_number)
        if generic_match:
            matches.append(generic_match)
            # Return early to avoid duplicate detection with high-entropy
            return matches

    # Check for high entropy (only if no specific pattern matched)
    if not matches and is_high_entropy(value):
        matches.append(
            SecretMatch(
                secret_type=SecretType.HIGH_ENTROPY,
                variable_name=variable_name,
                value=redact_value(value),
                line_number=line_number,
                severity="medium",
                recommendation="Review this high-entropy value. If it's a secret, rotate it and use a secret manager.",
            )
        )

    return matches


def is_placeholder(value: str) -> bool:
    """Check if a value is likely a placeholder.

    Args:
        value: Value to check

    Returns:
        True if value appears to be a placeholder
    """
    placeholder_patterns = [
        r"^$",  # Empty
        r"^<.{1,100}>$",  # <YOUR_KEY_HERE> - Fixed ReDoS: added upper bound
        r"^CHANGE_?ME",  # CHANGE_ME, CHANGEME
        r"^YOUR_.{1,100}_HERE$",  # YOUR_KEY_HERE - Fixed ReDoS: added upper bound
        r"^(xxx|yyy|zzz|placeholder|example|test|demo|sample)",  # Common placeholders
        r"^[*]{1,100}$",  # **** - Fixed ReDoS: added upper bound
        r"^[.]{1,100}$",  # .... - Fixed ReDoS: added upper bound
    ]

    for pattern in placeholder_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return True

    return False


def redact_value(value: str, show_chars: int = 4) -> str:
    """Redact a secret value for safe display.

    Args:
        value: Value to redact
        show_chars: Number of characters to show at start/end

    Returns:
        Redacted value
    """
    if len(value) <= show_chars * 2:
        return "*" * len(value)

    return f"{value[:show_chars]}...{value[-show_chars:]}"


def get_recommendation(secret_type: SecretType) -> str:
    """Get remediation recommendation for a secret type.

    Args:
        secret_type: Type of secret detected

    Returns:
        Recommendation text
    """
    recommendations = {
        # Existing secrets
        SecretType.AWS_ACCESS_KEY: "Rotate this AWS key immediately via IAM console. Use AWS Secrets Manager or IAM roles instead.",
        SecretType.AWS_SECRET_KEY: "Rotate this AWS secret key immediately. Never commit AWS credentials to version control.",
        SecretType.GITHUB_TOKEN: "Revoke this GitHub token at github.com/settings/tokens and generate a new one.",
        SecretType.GITHUB_PAT: "Revoke this GitHub PAT immediately and generate a new one with minimal required scopes.",
        SecretType.SLACK_TOKEN: "Regenerate this Slack token at api.slack.com/apps and update your application.",
        SecretType.SLACK_WEBHOOK: "Regenerate this Slack webhook URL in your workspace settings.",
        SecretType.STRIPE_KEY: "Roll this Stripe key immediately at dashboard.stripe.com/apikeys.",
        SecretType.OPENAI_KEY: "Rotate this OpenAI API key at platform.openai.com/api-keys.",
        SecretType.ANTHROPIC_KEY: "Rotate this Anthropic API key in your account settings.",
        SecretType.PRIVATE_KEY: "This private key has been exposed. Generate a new key pair immediately.",
        SecretType.DATABASE_URL: "Rotate database credentials and use environment variables without committing to git.",
        SecretType.GENERIC_API_KEY: "Rotate this API key and use a secret manager like Vault or AWS Secrets Manager.",
        SecretType.GENERIC_SECRET: "Rotate this secret immediately and consider using a dedicated secret manager.",
        SecretType.JWT_TOKEN: "This JWT token may be compromised. Invalidate it and issue a new one.",
        SecretType.HIGH_ENTROPY: "Review this high-entropy value. If it's a secret, rotate it and use a secret manager.",
        # Cloud Providers
        SecretType.AZURE_STORAGE_KEY: "Regenerate this Azure Storage key in the Azure Portal. Update all applications using this key.",
        SecretType.AZURE_SAS_TOKEN: "Revoke this Azure SAS token and generate a new one with minimal permissions.",
        SecretType.GOOGLE_API_KEY: "Rotate this Google Cloud API key at console.cloud.google.com/apis/credentials.",
        SecretType.GOOGLE_OAUTH_TOKEN: "Revoke this Google OAuth token and re-authenticate your application.",
        SecretType.DIGITALOCEAN_PAT: "Delete this DigitalOcean token at cloud.digitalocean.com/account/api/tokens and create a new one.",
        SecretType.DIGITALOCEAN_OAUTH: "Revoke this DigitalOcean OAuth token and re-authenticate your application.",
        SecretType.HEROKU_API_KEY: "Regenerate this Heroku API key at dashboard.heroku.com/account.",
        SecretType.ALIBABA_ACCESS_KEY_ID: "Disable this Alibaba Cloud AccessKey in RAM console and create a new one.",
        SecretType.ALIBABA_ACCESS_KEY_SECRET: "Rotate this Alibaba Cloud AccessKey Secret immediately in RAM console.",
        SecretType.IBM_CLOUD_IAM_KEY: "Delete this IBM Cloud IAM key and create a new one with minimal permissions.",
        # CI/CD & DevOps
        SecretType.CIRCLECI_TOKEN: "Revoke this CircleCI token at app.circleci.com/settings/user/tokens and generate a new one.",
        SecretType.TRAVIS_TOKEN: "Regenerate this Travis CI token at travis-ci.com/account/preferences.",
        SecretType.JENKINS_TOKEN: "Revoke this Jenkins API token and generate a new one in user configuration.",
        SecretType.GITLAB_PAT: "Revoke this GitLab PAT at gitlab.com/-/profile/personal_access_tokens and create a new one.",
        SecretType.GITLAB_PIPELINE_TOKEN: "Regenerate this GitLab pipeline trigger token in CI/CD settings.",
        SecretType.BITBUCKET_APP_PASSWORD: "Revoke this Bitbucket app password at bitbucket.org/account/settings/app-passwords/.",
        SecretType.DOCKER_HUB_TOKEN: "Delete this Docker Hub access token at hub.docker.com/settings/security and create a new one.",
        SecretType.TERRAFORM_CLOUD_TOKEN: "Revoke this Terraform Cloud token at app.terraform.io/app/settings/tokens.",
        # Communication & Monitoring
        SecretType.SLACK_BOT_TOKEN: "Regenerate this Slack bot token at api.slack.com/apps and reinstall the app.",
        SecretType.SLACK_USER_TOKEN: "Revoke this Slack user token and re-authenticate your application.",
        SecretType.DISCORD_BOT_TOKEN: "Regenerate this Discord bot token at discord.com/developers/applications.",
        SecretType.DISCORD_WEBHOOK: "Delete this Discord webhook and create a new one in server settings.",
        SecretType.TWILIO_API_KEY: "Delete this Twilio API key at twilio.com/console/project/api-keys and create a new one.",
        SecretType.SENDGRID_API_KEY: "Revoke this SendGrid API key at app.sendgrid.com/settings/api_keys and generate a new one.",
        # Payments & Commerce
        SecretType.PAYPAL_ACCESS_TOKEN: "Rotate this PayPal access token immediately and update your application.",
        SecretType.SQUARE_ACCESS_TOKEN: "Revoke this Square access token at developer.squareup.com and generate a new one.",
        SecretType.COINBASE_API_KEY: "Delete this Coinbase API key at coinbase.com/settings/api and create a new one.",
        SecretType.SHOPIFY_ACCESS_TOKEN: "Regenerate this Shopify access token in your app settings.",
        # Email & SMS
        SecretType.MAILGUN_API_KEY: "Rotate this Mailgun API key at app.mailgun.com/app/account/security/api_keys.",
        SecretType.MAILCHIMP_API_KEY: "Regenerate this Mailchimp API key at admin.mailchimp.com/account/api/.",
        SecretType.POSTMARK_SERVER_TOKEN: "Rotate this Postmark server token at account.postmarkapp.com/servers.",
        # Databases & Storage
        SecretType.MONGODB_CONNECTION_STRING: "Rotate the password in this MongoDB connection string and update the connection string.",
        SecretType.REDIS_URL_WITH_PASSWORD: "Change the Redis password and update all connection strings.",
        SecretType.FIREBASE_FCM_KEY: "Regenerate this Firebase FCM server key in Firebase Console.",
        # APIs & Services
        SecretType.DATADOG_API_KEY: "Revoke this Datadog API key at app.datadoghq.com/organization-settings/api-keys.",
        SecretType.NEW_RELIC_API_KEY: "Delete this New Relic API key at one.newrelic.com/api-keys and create a new one.",
        SecretType.PAGERDUTY_API_KEY: "Regenerate this PagerDuty API key at pagerduty.com/developer/api-keys.",
        SecretType.SENTRY_AUTH_TOKEN: "Revoke this Sentry auth token at sentry.io/settings/account/api/auth-tokens/.",
        SecretType.ALGOLIA_API_KEY: "Regenerate this Algolia API key at dashboard.algolia.com/account/api-keys.",
        SecretType.CLOUDFLARE_API_KEY: "Roll this Cloudflare API key at dash.cloudflare.com/profile/api-tokens.",
        # Package Managers
        SecretType.NPM_ACCESS_TOKEN: "Revoke this NPM token at npmjs.com/settings/tokens and generate a new one.",
        SecretType.PYPI_UPLOAD_TOKEN: "Delete this PyPI token at pypi.org/manage/account/token/ and create a new one.",
        # Generic Credential Detection
        SecretType.GENERIC_PASSWORD: "Rotate this password immediately and use a password manager or secret management solution.",
        SecretType.GENERIC_TOKEN: "Revoke and regenerate this token using the service's dashboard or API.",
        SecretType.GENERIC_API_SECRET: "Rotate this API secret and consider using environment-specific secret management.",
        SecretType.GENERIC_ENCRYPTION_KEY: "Generate a new encryption key and re-encrypt all data. Store keys in a secure vault.",
    }

    return recommendations.get(
        secret_type,
        "Rotate this secret and use a secret management solution.",
    )


def scan_env_file(file_path: Path) -> List[SecretMatch]:
    """Scan a .env file for secrets.

    Args:
        file_path: Path to .env file

    Returns:
        List of detected secrets
    """
    from tripwire.parser import EnvFileParser

    if not file_path.exists():
        return []

    parser = EnvFileParser()
    entries = parser.parse_file(file_path)

    all_matches: List[SecretMatch] = []

    for key, entry in entries.items():
        matches = detect_secrets_in_value(key, entry.value, entry.line_number)
        all_matches.extend(matches)

    return all_matches


def scan_git_history(
    repo_path: Path, depth: int = 100, file_patterns: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """Scan git history for secrets in .env files.

    Args:
        repo_path: Path to git repository
        depth: Number of commits to scan
        file_patterns: File patterns to scan (default: ['.env', '.env.*'])

    Returns:
        List of findings with commit info
    """
    import subprocess

    if file_patterns is None:
        file_patterns = [".env", ".env.local", ".env.*.local"]

    findings: List[Dict[str, str]] = []

    try:
        # Get commit history
        result = subprocess.run(
            ["git", "log", f"-{depth}", "--all", "--pretty=format:%H"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = result.stdout.strip().split("\n")

        for commit_hash in commits:
            # Check each file pattern
            for pattern in file_patterns:
                try:
                    # Get file content from commit
                    file_result = subprocess.run(
                        ["git", "show", f"{commit_hash}:{pattern}"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )

                    if file_result.returncode == 0:
                        content = file_result.stdout
                        # Parse and scan content
                        from tripwire.parser import EnvFileParser

                        parser = EnvFileParser()
                        entries = parser.parse_string(content)

                        for key, entry in entries.items():
                            matches = detect_secrets_in_value(key, entry.value, entry.line_number)

                            for match in matches:
                                findings.append(
                                    {
                                        "commit": commit_hash[:8],
                                        "file": pattern,
                                        "variable": match.variable_name,
                                        "type": match.secret_type.value,
                                        "severity": match.severity,
                                    }
                                )

                except subprocess.CalledProcessError:
                    # File doesn't exist in this commit
                    continue

    except subprocess.CalledProcessError:
        # Git command failed (not a git repo, etc.)
        pass

    return findings


def get_severity_color(severity: str) -> str:
    """Get color code for severity level (for rich formatting).

    Args:
        severity: Severity level

    Returns:
        Color name for rich library
    """
    colors = {
        "critical": "red",
        "high": "orange3",
        "medium": "yellow",
        "low": "blue",
    }
    return colors.get(severity.lower(), "white")
