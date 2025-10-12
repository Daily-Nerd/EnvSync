"""Environment file loading with source abstraction.

This module provides an abstraction for loading environment variables from
different sources (files, remote configs, etc.) with proper error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv as _dotenv_load

from tripwire.exceptions import EnvFileNotFoundError


class EnvSource(ABC):
    """Abstract base class for environment variable sources.

    This enables loading environment variables from various sources:
    - Local .env files (DotenvFileSource)
    - Remote configuration servers (future: RemoteConfigSource)
    - Cloud secret managers (future: AWSSecretsSource, GCPSecretsSource)
    - Encrypted vaults (future: VaultSource)

    Design Pattern:
        Strategy pattern - different sources implement the same interface
    """

    @abstractmethod
    def load(self) -> Dict[str, str]:
        """Load environment variables from this source.

        Returns:
            Dictionary of environment variable key-value pairs

        Raises:
            Exception subclasses for source-specific errors
        """
        pass


class DotenvFileSource(EnvSource):
    """Load environment variables from .env files using python-dotenv.

    This source wraps python-dotenv to provide consistent error handling
    and integration with TripWire's architecture.

    Attributes:
        file_path: Path to .env file
        override: Whether to override existing environment variables
    """

    def __init__(self, file_path: Path, override: bool = False) -> None:
        """Initialize dotenv file source.

        Args:
            file_path: Path to .env file
            override: Whether to override existing environment variables
        """
        self.file_path = file_path
        self.override = override

    def load(self) -> Dict[str, str]:
        """Load environment variables from .env file.

        Returns:
            Dictionary of loaded variables (empty dict if file doesn't exist
            and we're not in strict mode - handled by EnvFileLoader)

        Raises:
            EnvFileNotFoundError: If file doesn't exist and strict mode enabled
                (raised by EnvFileLoader, not here)

        Note:
            This method loads variables into os.environ as a side effect.
            The return value is for tracking purposes only.
        """
        if not self.file_path.exists():
            return {}

        # Load into os.environ
        _dotenv_load(self.file_path, override=self.override)

        # Parse file to return loaded variables for tracking
        loaded_vars: Dict[str, str] = {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse KEY=VALUE format
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        # Remove quotes if present
                        value = value.strip().strip("\"'")
                        loaded_vars[key] = value
        except Exception:
            # If parsing fails, just return empty dict
            # The variables are still loaded into os.environ by dotenv
            pass

        return loaded_vars


class EnvFileLoader:
    """Orchestrates loading environment variables from multiple sources.

    This class manages the loading process:
    - Loads sources in order (later sources can override earlier ones)
    - Tracks which files were successfully loaded
    - Handles errors according to strict mode

    Design Pattern:
        Facade pattern - simplifies complex multi-source loading

    Attributes:
        sources: List of environment variable sources to load
        strict: Whether to raise errors for missing files
    """

    def __init__(self, sources: List[EnvSource], strict: bool = False) -> None:
        """Initialize environment file loader.

        Args:
            sources: List of sources to load (order matters - later overrides earlier)
            strict: If True, raise error when a source fails to load
        """
        self.sources = sources
        self.strict = strict
        self._loaded_files: List[Path] = []

    def load_all(self) -> None:
        """Load all sources in order.

        Sources are loaded sequentially. If a source has override=True,
        it will overwrite variables from previous sources.

        Raises:
            EnvFileNotFoundError: If strict=True and a file source doesn't exist
        """
        import os

        for source in self.sources:
            # Load the source
            loaded_vars = source.load()

            # For non-DotenvFileSource sources (like plugins), we need to
            # inject the variables into os.environ manually
            if not isinstance(source, DotenvFileSource):
                # Inject variables from plugin into environment
                for key, value in loaded_vars.items():
                    os.environ[key] = value

            # Track successful file loads for reporting
            if isinstance(source, DotenvFileSource):
                # Check if file exists and was loaded
                if source.file_path.exists():
                    self._loaded_files.append(source.file_path)
                elif self.strict:
                    raise EnvFileNotFoundError(str(source.file_path))

    def get_loaded_files(self) -> List[Path]:
        """Get list of files that were successfully loaded.

        Returns:
            List of Path objects for successfully loaded files
        """
        return self._loaded_files.copy()
