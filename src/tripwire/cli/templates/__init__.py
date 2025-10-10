"""Project templates for TripWire CLI."""

from typing import TypedDict


class TemplateData(TypedDict):
    """Type for project template data."""

    base: str
    secret_comment: str
    placeholder_comment: str


# Project template definitions (module-level constant)
# Templates use {secret_section} placeholder for dynamic secret injection
PROJECT_TEMPLATES: dict[str, TemplateData] = {
    "web": {
        "base": """# Web Application Configuration
# Database connection
DATABASE_URL=postgresql://localhost:5432/mydb

# Security
{secret_section}
DEBUG=false

# Server configuration
PORT=8000
ALLOWED_HOSTS=localhost,127.0.0.1
""",
        "secret_comment": """# IMPORTANT: This is a randomly generated key for development.
# Generate a new random key for production!""",
        "placeholder_comment": """# IMPORTANT: Generate a secure random key for production!
# Never commit real secrets to version control.""",
    },
    "cli": {
        "base": """# CLI Tool Configuration
# API access
API_KEY=your-api-key-here

# Logging
DEBUG=false
LOG_LEVEL=INFO
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
    "data": {
        "base": """# Data Pipeline Configuration
# Database
DATABASE_URL=postgresql://localhost:5432/mydb

# Cloud storage
S3_BUCKET=my-data-bucket
AWS_REGION=us-east-1

# Processing
DEBUG=false
MAX_WORKERS=4
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
    "other": {
        "base": """# Application Configuration
# Add your environment variables here

# Example: API key
# API_KEY=your-api-key-here

# Example: Debug mode
DEBUG=false
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
}

__all__ = ["PROJECT_TEMPLATES"]
