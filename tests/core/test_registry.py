"""Tests for VariableRegistry thread-safe variable registration."""

import threading
from typing import List

import pytest

from tripwire.core.registry import VariableMetadata, VariableRegistry


class TestVariableMetadata:
    """Test suite for VariableMetadata dataclass."""

    def test_metadata_creation_minimal(self):
        """Test creating metadata with minimal required fields."""
        metadata = VariableMetadata(
            name="API_KEY",
            required=True,
            type_name="str",
        )
        assert metadata.name == "API_KEY"
        assert metadata.required is True
        assert metadata.type_name == "str"
        assert metadata.default is None
        assert metadata.description is None
        assert metadata.secret is False

    def test_metadata_creation_full(self):
        """Test creating metadata with all fields."""
        metadata = VariableMetadata(
            name="DATABASE_URL",
            required=True,
            type_name="str",
            default=None,
            description="PostgreSQL connection string",
            secret=True,
        )
        assert metadata.name == "DATABASE_URL"
        assert metadata.required is True
        assert metadata.type_name == "str"
        assert metadata.default is None
        assert metadata.description == "PostgreSQL connection string"
        assert metadata.secret is True

    def test_metadata_with_default(self):
        """Test metadata for optional variable with default."""
        metadata = VariableMetadata(
            name="PORT",
            required=False,
            type_name="int",
            default=8000,
            description="Server port",
        )
        assert metadata.name == "PORT"
        assert metadata.required is False
        assert metadata.type_name == "int"
        assert metadata.default == 8000


class TestVariableRegistry:
    """Test suite for VariableRegistry thread-safe operations."""

    def test_empty_registry(self):
        """Test newly created registry is empty."""
        registry = VariableRegistry()
        assert registry.get_all() == {}
        assert registry.get("NONEXISTENT") is None

    def test_register_and_retrieve(self):
        """Test basic registration and retrieval."""
        registry = VariableRegistry()
        metadata = VariableMetadata(
            name="API_KEY",
            required=True,
            type_name="str",
            secret=True,
        )
        registry.register(metadata)

        retrieved = registry.get("API_KEY")
        assert retrieved is not None
        assert retrieved.name == "API_KEY"
        assert retrieved.required is True
        assert retrieved.type_name == "str"
        assert retrieved.secret is True

    def test_register_multiple_variables(self):
        """Test registering multiple different variables."""
        registry = VariableRegistry()

        metadata1 = VariableMetadata(name="VAR1", required=True, type_name="str")
        metadata2 = VariableMetadata(name="VAR2", required=False, type_name="int", default=42)
        metadata3 = VariableMetadata(
            name="VAR3",
            required=True,
            type_name="bool",
            description="Feature flag",
        )

        registry.register(metadata1)
        registry.register(metadata2)
        registry.register(metadata3)

        all_vars = registry.get_all()
        assert len(all_vars) == 3
        assert "VAR1" in all_vars
        assert "VAR2" in all_vars
        assert "VAR3" in all_vars
        assert all_vars["VAR2"].default == 42

    def test_duplicate_registration_overwrites(self):
        """Test that registering same variable twice overwrites first."""
        registry = VariableRegistry()

        # First registration
        metadata1 = VariableMetadata(
            name="DATABASE_URL",
            required=True,
            type_name="str",
            description="First description",
        )
        registry.register(metadata1)

        # Second registration (should overwrite)
        metadata2 = VariableMetadata(
            name="DATABASE_URL",
            required=False,
            type_name="str",
            description="Second description",
            default="sqlite:///db.sqlite3",
        )
        registry.register(metadata2)

        retrieved = registry.get("DATABASE_URL")
        assert retrieved is not None
        assert retrieved.description == "Second description"
        assert retrieved.required is False
        assert retrieved.default == "sqlite:///db.sqlite3"

        # Should only have one entry
        assert len(registry.get_all()) == 1

    def test_get_nonexistent_returns_none(self):
        """Test that getting nonexistent variable returns None."""
        registry = VariableRegistry()
        registry.register(VariableMetadata(name="EXISTING", required=True, type_name="str"))

        assert registry.get("NONEXISTENT") is None
        assert registry.get("existing") is None  # Case sensitive

    def test_get_all_returns_copy(self):
        """Test that get_all returns immutable copy."""
        registry = VariableRegistry()
        metadata = VariableMetadata(name="VAR1", required=True, type_name="str")
        registry.register(metadata)

        # Get snapshot
        snapshot1 = registry.get_all()
        assert "VAR1" in snapshot1

        # Modify snapshot (should not affect registry)
        snapshot1["VAR2"] = VariableMetadata(name="VAR2", required=True, type_name="int")

        # Get fresh snapshot
        snapshot2 = registry.get_all()
        assert "VAR1" in snapshot2
        assert "VAR2" not in snapshot2  # Mutation didn't affect registry

    def test_clear(self):
        """Test clearing all variables."""
        registry = VariableRegistry()

        # Register multiple variables
        for i in range(5):
            registry.register(VariableMetadata(name=f"VAR{i}", required=True, type_name="str"))
        assert len(registry.get_all()) == 5

        # Clear
        registry.clear()
        assert len(registry.get_all()) == 0
        assert registry.get("VAR0") is None

    def test_concurrent_registration_thread_safety(self):
        """Test thread-safe concurrent registration (50+ threads)."""
        registry = VariableRegistry()
        num_threads = 50
        errors: List[Exception] = []

        def register_variable(thread_id: int):
            """Register a variable from a thread."""
            try:
                metadata = VariableMetadata(
                    name=f"VAR_{thread_id}",
                    required=True,
                    type_name="str",
                    description=f"Variable from thread {thread_id}",
                )
                registry.register(metadata)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=register_variable, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all variables were registered
        all_vars = registry.get_all()
        assert len(all_vars) == num_threads
        for i in range(num_threads):
            assert f"VAR_{i}" in all_vars

    def test_concurrent_read_write_stress(self):
        """Thread-safety stress test: 20 threads × 100 operations each."""
        registry = VariableRegistry()
        num_threads = 20
        operations_per_thread = 100
        errors: List[Exception] = []

        def stress_worker(thread_id: int):
            """Perform mixed read/write operations."""
            try:
                for i in range(operations_per_thread):
                    # Register variable
                    metadata = VariableMetadata(
                        name=f"VAR_{thread_id}_{i}",
                        required=(i % 2 == 0),
                        type_name="str" if i % 3 == 0 else "int",
                    )
                    registry.register(metadata)

                    # Read variable
                    retrieved = registry.get(f"VAR_{thread_id}_{i}")
                    assert retrieved is not None

                    # Read all variables
                    all_vars = registry.get_all()
                    assert len(all_vars) > 0

            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=stress_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify final state
        all_vars = registry.get_all()
        expected_count = num_threads * operations_per_thread
        assert len(all_vars) == expected_count

    def test_concurrent_duplicate_registration(self):
        """Test concurrent registration of same variable (last write wins)."""
        registry = VariableRegistry()
        num_threads = 20
        errors: List[Exception] = []

        def register_same_variable(thread_id: int):
            """Register the same variable from multiple threads."""
            try:
                metadata = VariableMetadata(
                    name="SHARED_VAR",
                    required=True,
                    type_name="str",
                    description=f"From thread {thread_id}",
                )
                registry.register(metadata)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=register_same_variable, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify only one variable exists (last write wins)
        all_vars = registry.get_all()
        assert len(all_vars) == 1
        assert "SHARED_VAR" in all_vars

        # Description should be from one of the threads
        retrieved = registry.get("SHARED_VAR")
        assert retrieved is not None
        assert retrieved.description.startswith("From thread ")

    def test_clear_during_concurrent_operations(self):
        """Test clearing registry during concurrent operations."""
        registry = VariableRegistry()
        num_threads = 10
        errors: List[Exception] = []
        should_stop = threading.Event()

        def worker():
            """Continuously register variables until stopped."""
            try:
                counter = 0
                while not should_stop.is_set():
                    metadata = VariableMetadata(
                        name=f"VAR_{threading.current_thread().ident}_{counter}",
                        required=True,
                        type_name="str",
                    )
                    registry.register(metadata)
                    counter += 1
            except Exception as e:
                errors.append(e)

        # Start worker threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Let workers run briefly
        import time

        time.sleep(0.1)

        # Clear registry while workers are active
        registry.clear()

        # Stop workers
        should_stop.set()
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Registry might have some variables registered after clear
        # but the clear operation itself should not cause errors
