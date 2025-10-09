"""Facade for unified configuration access across multiple sources.

This module provides the ConfigRepository class, which acts as a facade for
loading, merging, and comparing configuration from multiple sources.
"""

from enum import Enum
from pathlib import Path

from .models import ConfigDiff, ConfigValue
from .source import ConfigSource
from .sources.env_file import EnvFileSource
from .sources.toml_source import TOMLSource


class MergeStrategy(Enum):
    """Strategy for merging configuration from multiple sources.

    Attributes:
        LAST_WINS: Later sources override earlier sources (default)
        FIRST_WINS: Earlier sources take precedence
        STRICT: Raise error on conflicts
    """

    LAST_WINS = "last_wins"
    FIRST_WINS = "first_wins"
    STRICT = "strict"


class ConfigRepository:
    """Facade for unified configuration access.

    This class provides a high-level interface for working with configuration
    from multiple sources, handling merging, caching, and comparison.

    Features:
        - Multiple source support with configurable merge strategies
        - Automatic format detection from file extensions
        - Configuration caching for performance
        - Diff computation between repositories
        - Builder pattern for fluent API

    Example:
        >>> repo = ConfigRepository()
        >>> repo.add_source(EnvFileSource(".env"))
        >>> repo.add_source(TOMLSource("pyproject.toml"))
        >>> repo.load()
        >>> print(repo.get("DATABASE_URL").value)
        postgresql://localhost/mydb

        >>> # Or use auto-detection
        >>> repo = ConfigRepository.from_file(".env").load()
    """

    def __init__(
        self,
        sources: list[ConfigSource] | None = None,
        merge_strategy: MergeStrategy = MergeStrategy.LAST_WINS,
    ) -> None:
        """Initialize the configuration repository.

        Args:
            sources: List of configuration sources to load from
            merge_strategy: Strategy for handling conflicts between sources
        """
        self.sources = sources or []
        self.merge_strategy = merge_strategy
        self._config: dict[str, ConfigValue] | None = None

    def add_source(self, source: ConfigSource) -> "ConfigRepository":
        """Add a configuration source (builder pattern).

        Args:
            source: Configuration source to add

        Returns:
            Self for method chaining

        Example:
            >>> repo = ConfigRepository()
            >>> repo.add_source(EnvFileSource(".env"))
            >>> repo.add_source(TOMLSource("pyproject.toml"))
            >>> repo.load()
        """
        self.sources.append(source)
        # Invalidate cache
        self._config = None
        return self

    def load(self) -> "ConfigRepository":
        """Load and merge all sources.

        Loads configuration from all sources and merges them according to
        the merge strategy. Results are cached until sources are modified.

        Returns:
            Self for method chaining

        Raises:
            FileNotFoundError: If any source file doesn't exist
            ValueError: If merge strategy is STRICT and conflicts exist

        Example:
            >>> repo = ConfigRepository()
            >>> repo.add_source(EnvFileSource(".env"))
            >>> repo.load()
            >>> repo.get("PORT")
        """
        if not self.sources:
            self._config = {}
            return self

        # Load from all sources
        all_configs: list[dict[str, ConfigValue]] = []
        for source in self.sources:
            try:
                config = source.load()
                all_configs.append(config)
            except FileNotFoundError:
                # Skip missing files gracefully
                continue

        # Merge according to strategy
        self._config = self._merge_configs(all_configs)
        return self

    def get(self, key: str) -> ConfigValue | None:
        """Get a configuration value.

        Args:
            key: Configuration key to retrieve

        Returns:
            ConfigValue if found, None otherwise

        Raises:
            RuntimeError: If repository hasn't been loaded yet

        Example:
            >>> repo = ConfigRepository.from_file(".env").load()
            >>> value = repo.get("DATABASE_URL")
            >>> print(value.value)
        """
        if self._config is None:
            raise RuntimeError("Repository not loaded. Call load() first.")

        return self._config.get(key)

    def get_all(self) -> dict[str, ConfigValue]:
        """Get all configuration values.

        Returns:
            Dict mapping all keys to ConfigValue objects

        Raises:
            RuntimeError: If repository hasn't been loaded yet

        Example:
            >>> repo = ConfigRepository.from_file(".env").load()
            >>> for key, value in repo.get_all().items():
            ...     print(f"{key}={value.value}")
        """
        if self._config is None:
            raise RuntimeError("Repository not loaded. Call load() first.")

        return self._config.copy()

    def diff(self, other: "ConfigRepository") -> ConfigDiff:
        """Compare with another repository.

        Compares this repository with another to identify added, removed,
        and modified configuration values.

        Args:
            other: Repository to compare against

        Returns:
            ConfigDiff object with categorized differences

        Raises:
            RuntimeError: If either repository hasn't been loaded

        Example:
            >>> repo1 = ConfigRepository.from_file(".env").load()
            >>> repo2 = ConfigRepository.from_file("pyproject.toml").load()
            >>> diff = repo1.diff(repo2)
            >>> print(diff.summary())
            2 added, 1 removed, 3 modified
        """
        if self._config is None or other._config is None:
            raise RuntimeError("Both repositories must be loaded before diffing")

        self_keys = set(self._config.keys())
        other_keys = set(other._config.keys())

        # Added: in other but not in self
        added = {key: other._config[key] for key in other_keys - self_keys}

        # Removed: in self but not in other
        removed = {key: self._config[key] for key in self_keys - other_keys}

        # Modified: in both but with different values
        modified: dict[str, tuple[ConfigValue, ConfigValue]] = {}
        unchanged: dict[str, ConfigValue] = {}

        for key in self_keys & other_keys:
            self_val = self._config[key]
            other_val = other._config[key]

            if self_val.raw_value != other_val.raw_value:
                modified[key] = (self_val, other_val)
            else:
                unchanged[key] = self_val

        return ConfigDiff(added=added, removed=removed, modified=modified, unchanged=unchanged)

    @classmethod
    def from_file(cls, file_path: str | Path) -> "ConfigRepository":
        """Auto-detect format and create repository.

        Creates a repository with a single source, automatically detecting
        the file format from the extension.

        Args:
            file_path: Path to configuration file

        Returns:
            ConfigRepository with appropriate source

        Raises:
            ValueError: If file extension is not recognized

        Example:
            >>> repo = ConfigRepository.from_file(".env").load()
            >>> repo = ConfigRepository.from_file("pyproject.toml").load()
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        source: EnvFileSource | TOMLSource
        if suffix == ".env" or path.name.startswith(".env"):
            source = EnvFileSource(path)
        elif suffix == ".toml":
            source = TOMLSource(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. " f"Supported formats: .env, .toml")

        repo = cls()
        repo.add_source(source)
        return repo

    def _merge_configs(self, configs: list[dict[str, ConfigValue]]) -> dict[str, ConfigValue]:
        """Merge multiple configuration dicts according to strategy.

        Args:
            configs: List of configuration dicts to merge

        Returns:
            Merged configuration dict

        Raises:
            ValueError: If merge strategy is STRICT and conflicts exist
        """
        if not configs:
            return {}

        if len(configs) == 1:
            return configs[0]

        merged: dict[str, ConfigValue] = {}

        if self.merge_strategy == MergeStrategy.FIRST_WINS:
            # Reverse order so first source wins
            for config in reversed(configs):
                merged.update(config)
        elif self.merge_strategy == MergeStrategy.LAST_WINS:
            # Normal order so last source wins
            for config in configs:
                merged.update(config)
        elif self.merge_strategy == MergeStrategy.STRICT:
            # Check for conflicts
            all_keys: set[str] = set()
            for config in configs:
                conflicts = all_keys & set(config.keys())
                if conflicts:
                    raise ValueError(f"Merge conflict in STRICT mode: {', '.join(sorted(conflicts))}")
                all_keys.update(config.keys())
                merged.update(config)

        return merged
