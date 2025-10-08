"""Pytest configuration and shared fixtures for TripWire tests."""

import os
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Clean up environment variables after test.

    This fixture saves the current environment state and restores it
    after the test completes, ensuring test isolation.
    """
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Create a temporary .env file for testing.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to temporary .env file
    """
    env_file = tmp_path / ".env"
    return env_file


@pytest.fixture
def sample_env_file(temp_env_file: Path) -> Path:
    """Create a sample .env file with test data.

    Args:
        temp_env_file: Path to temp env file

    Returns:
        Path to populated .env file
    """
    content = """# Sample environment file
API_KEY=test-api-key-12345
DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
DEBUG=true
PORT=8000
MAX_CONNECTIONS=100
ALLOWED_HOSTS=localhost,example.com,api.example.com
"""
    temp_env_file.write_text(content)
    return temp_env_file


@pytest.fixture
def sample_env_vars(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up sample environment variables for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Dictionary of set environment variables
    """
    env_vars = {
        "API_KEY": "test-api-key-12345",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
        "DEBUG": "true",
        "PORT": "8000",
        "MAX_CONNECTIONS": "100",
        "ADMIN_EMAIL": "admin@example.com",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Create an isolated environment with no variables set.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Clear all environment variables for isolated testing
    for key in list(os.environ.keys()):
        monkeypatch.delenv(key, raising=False)

    yield
