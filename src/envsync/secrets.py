"""Secret detection for environment files.

This module provides pattern-based detection of secrets and sensitive data
in .env files and git history to prevent accidental commits.
"""

import math
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class SecretType(Enum):
    """Types of secrets that can be detected."""

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


# Secret detection patterns
SECRET_PATTERNS: List[SecretPattern] = [
    # AWS Keys
    SecretPattern(
        secret_type=SecretType.AWS_ACCESS_KEY,
        pattern=r"AKIA[0-9A-Z]{16}",
        description="AWS Access Key ID",
        severity="critical",
    ),
    SecretPattern(
        secret_type=SecretType.AWS_SECRET_KEY,
        pattern=r"aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        description="AWS Secret Access Key",
        severity="critical",
    ),
    # GitHub Tokens
    SecretPattern(
        secret_type=SecretType.GITHUB_TOKEN,
        pattern=r"gh[pousr]_[0-9a-zA-Z]{36,}",
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
        pattern=r"https://hooks\.slack\.com/services/T[0-9A-Z]{8,}/B[0-9A-Z]{8,}/[0-9a-zA-Z]{24,}",
        description="Slack Webhook URL",
        severity="high",
    ),
    # Stripe Keys
    SecretPattern(
        secret_type=SecretType.STRIPE_KEY,
        pattern=r"sk_live_[0-9a-zA-Z]{24,}",
        description="Stripe Live Secret Key",
        severity="critical",
    ),
    # AI API Keys
    SecretPattern(
        secret_type=SecretType.OPENAI_KEY,
        pattern=r"sk-[a-zA-Z0-9]{48,}",
        description="OpenAI API Key",
        severity="high",
    ),
    SecretPattern(
        secret_type=SecretType.ANTHROPIC_KEY,
        pattern=r"sk-ant-[a-zA-Z0-9\-]{95,}",
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
        pattern=r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
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
    # Generic patterns (lower priority)
    SecretPattern(
        secret_type=SecretType.GENERIC_API_KEY,
        pattern=r"(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['\"]?([0-9a-zA-Z\-_]{32,})['\"]?",
        description="Generic API Key",
        severity="medium",
    ),
    SecretPattern(
        secret_type=SecretType.GENERIC_SECRET,
        pattern=r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"]{16,})['\"]?",
        description="Generic Secret or Password",
        severity="medium",
    ),
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


def detect_secrets_in_value(variable_name: str, value: str, line_number: int = 0) -> List[SecretMatch]:
    """Detect secrets in a single environment variable value.

    Args:
        variable_name: Name of the environment variable
        value: Value to scan
        line_number: Line number in file

    Returns:
        List of detected secrets
    """
    matches: List[SecretMatch] = []

    # Skip obvious placeholders
    if is_placeholder(value):
        return matches

    # Check each pattern
    for pattern_def in SECRET_PATTERNS:
        if re.search(pattern_def.pattern, value, re.IGNORECASE):
            matches.append(
                SecretMatch(
                    secret_type=pattern_def.secret_type,
                    variable_name=variable_name,
                    value=redact_value(value),
                    line_number=line_number,
                    severity=pattern_def.severity,
                    recommendation=get_recommendation(pattern_def.secret_type),
                )
            )

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
        r"^<.*>$",  # <YOUR_KEY_HERE>
        r"^CHANGE_?ME",  # CHANGE_ME, CHANGEME
        r"^YOUR_.*_HERE$",  # YOUR_KEY_HERE
        r"^(xxx|yyy|zzz|placeholder|example|test|demo|sample)",  # Common placeholders
        r"^[*]+$",  # ****
        r"^[.]+$",  # ....
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
    from envsync.parser import EnvFileParser

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
                        from envsync.parser import EnvFileParser

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
