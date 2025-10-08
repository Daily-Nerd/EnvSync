"""Concurrency tests for validator registry thread safety.

This module tests the thread-safe behavior of the validator registry
operations to ensure no race conditions occur in multi-threaded environments.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List

from tripwire.validation import (
    clear_custom_validators,
    get_validator,
    list_validators,
    register_validator,
    unregister_validator,
)


def _make_simple_validator() -> Callable[[str], bool]:
    """Factory to create simple validators without closure issues.

    Returns:
        A validator function that always returns True
    """
    return lambda _v: True


class TestValidatorRegistryConcurrency:
    """Tests for concurrent validator registry operations."""

    def setup_method(self) -> None:
        """Clean up validators before each test."""
        clear_custom_validators()

    def teardown_method(self) -> None:
        """Clean up validators after each test."""
        clear_custom_validators()

    def test_concurrent_registration_same_validator(self) -> None:
        """Test concurrent registration of the same validator name.

        Multiple threads attempting to register the same validator should
        complete without errors or race conditions.
        """
        results: List[Exception | None] = []

        def register_test_validator() -> None:
            try:
                register_validator("test_format", lambda v: len(v) > 5)
                results.append(None)
            except Exception as e:
                results.append(e)

        # Run 50 threads concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_test_validator) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # All registrations should succeed (last write wins)
        assert all(r is None for r in results)

        # Validator should be registered
        validator = get_validator("test_format")
        assert validator is not None
        assert callable(validator)

    def test_concurrent_registration_different_validators(self) -> None:
        """Test concurrent registration of different validators.

        Multiple threads registering different validators should all succeed
        without conflicts or race conditions.
        """
        num_validators = 100
        results: List[bool] = []

        def register_numbered_validator(n: int) -> None:
            validator_name = f"validator_{n}"
            register_validator(validator_name, lambda v: len(v) > n)
            results.append(True)

        # Register 100 different validators concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(register_numbered_validator, i) for i in range(num_validators)]
            for future in as_completed(futures):
                future.result()

        # All registrations should succeed
        assert len(results) == num_validators
        assert all(results)

        # All validators should be registered
        validators = list_validators()
        for i in range(num_validators):
            assert f"validator_{i}" in validators
            assert validators[f"validator_{i}"] == "custom"

    def test_concurrent_get_validator(self) -> None:
        """Test concurrent reads of validators.

        Multiple threads reading validators should all get consistent results
        without errors or race conditions.
        """
        # Register some validators first
        register_validator("test_1", lambda v: len(v) > 5)
        register_validator("test_2", lambda v: len(v) < 10)
        register_validator("test_3", lambda v: v.isdigit())

        results: List[bool] = []

        def read_validator(name: str) -> None:
            validator = get_validator(name)
            results.append(validator is not None and callable(validator))

        # Read validators 300 times concurrently (100 per validator)
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = []
            for _ in range(100):
                futures.append(executor.submit(read_validator, "test_1"))
                futures.append(executor.submit(read_validator, "test_2"))
                futures.append(executor.submit(read_validator, "test_3"))

            for future in as_completed(futures):
                future.result()

        # All reads should succeed
        assert len(results) == 300
        assert all(results)

    def test_concurrent_registration_and_retrieval(self) -> None:
        """Test concurrent writes and reads of validators.

        Mixing registration and retrieval operations should be safe and
        consistent without race conditions.
        """
        registration_count = 0
        retrieval_count = 0
        lock = threading.Lock()

        def register_validators() -> None:
            nonlocal registration_count
            for i in range(10):
                # Use factory to avoid lambda closure issue
                validator_func = (lambda length: lambda v: len(v) > length)(i)
                register_validator(f"concurrent_{i}", validator_func)
                with lock:
                    registration_count += 1
                time.sleep(0.001)  # Small delay to interleave operations

        def retrieve_validators() -> None:
            nonlocal retrieval_count
            for i in range(10):
                get_validator(f"concurrent_{i}")
                with lock:
                    retrieval_count += 1
                time.sleep(0.001)  # Small delay to interleave operations

        # Run writers and readers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            write_futures = [executor.submit(register_validators) for _ in range(5)]
            read_futures = [executor.submit(retrieve_validators) for _ in range(5)]

            for future in as_completed(write_futures + read_futures):
                future.result()

        # All operations should complete
        assert registration_count == 50  # 5 threads * 10 registrations
        assert retrieval_count == 50  # 5 threads * 10 retrievals

    def test_concurrent_unregister(self) -> None:
        """Test concurrent unregistration of validators.

        Multiple threads attempting to unregister validators should be safe.
        """
        # Register validators first
        for i in range(20):
            register_validator(f"removable_{i}", lambda v: len(v) > 0)

        results: List[bool] = []

        def unregister_validator_safe(name: str) -> None:
            result = unregister_validator(name)
            results.append(result)

        # Try to unregister each validator from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(20):
                # Each validator gets unregistered by 3 threads
                for _ in range(3):
                    futures.append(executor.submit(unregister_validator_safe, f"removable_{i}"))

            for future in as_completed(futures):
                future.result()

        # Exactly 20 unregistrations should succeed (one per validator)
        # The other 40 should return False
        assert sum(results) == 20
        assert len(results) == 60  # 20 validators * 3 attempts

        # All validators should be gone
        validators = list_validators()
        for i in range(20):
            assert f"removable_{i}" not in validators

    def test_concurrent_list_validators(self) -> None:
        """Test concurrent listing of validators.

        Multiple threads listing validators while others modify the registry
        should be safe and return consistent snapshots.
        """
        results: List[dict[str, str]] = []

        def list_validators_safe() -> None:
            validators = list_validators()
            results.append(validators)

        def register_random_validators() -> None:
            for i in range(10):
                register_validator(f"random_{threading.get_ident()}_{i}", _make_simple_validator())
                time.sleep(0.001)

        # Mix listing and registration operations
        with ThreadPoolExecutor(max_workers=15) as executor:
            list_futures = [executor.submit(list_validators_safe) for _ in range(50)]
            register_futures = [executor.submit(register_random_validators) for _ in range(5)]

            for future in as_completed(list_futures + register_futures):
                future.result()

        # All list operations should succeed and return valid dictionaries
        assert len(results) == 50
        for validators in results:
            assert isinstance(validators, dict)
            # Each result should be internally consistent
            for _name, validator_type in validators.items():
                assert validator_type in ("built-in", "custom")

    def test_concurrent_clear_validators(self) -> None:
        """Test concurrent clearing of validators.

        Multiple threads clearing validators should be safe.
        """
        # Register some validators
        for i in range(50):
            register_validator(f"clearable_{i}", _make_simple_validator())

        clear_count = 0
        lock = threading.Lock()

        def clear_validators_safe() -> None:
            nonlocal clear_count
            clear_custom_validators()
            with lock:
                clear_count += 1

        # Multiple threads clearing concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(clear_validators_safe) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # All clears should complete
        assert clear_count == 10

        # No custom validators should remain
        validators = list_validators()
        custom_validators = [name for name, vtype in validators.items() if vtype == "custom"]
        assert len(custom_validators) == 0

    def test_stress_test_mixed_operations(self) -> None:
        """Stress test with mixed concurrent operations.

        This test performs a mix of all operations (register, unregister,
        get, list, clear) concurrently to verify overall thread safety.
        """
        operation_counts = {
            "register": 0,
            "unregister": 0,
            "get": 0,
            "list": 0,
        }
        lock = threading.Lock()

        def mixed_operations(thread_id: int) -> None:
            for i in range(20):
                # Register
                register_validator(f"stress_{thread_id}_{i}", _make_simple_validator())
                with lock:
                    operation_counts["register"] += 1

                # Get
                get_validator(f"stress_{thread_id}_{i}")
                with lock:
                    operation_counts["get"] += 1

                # List
                list_validators()
                with lock:
                    operation_counts["list"] += 1

                # Unregister
                if i % 2 == 0:
                    unregister_validator(f"stress_{thread_id}_{i}")
                    with lock:
                        operation_counts["unregister"] += 1

        # Run stress test with 15 threads
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(15)]
            for future in as_completed(futures):
                future.result()

        # Verify all operations completed
        assert operation_counts["register"] == 300  # 15 threads * 20 operations
        assert operation_counts["get"] == 300
        assert operation_counts["list"] == 300
        assert operation_counts["unregister"] == 150  # Half of registrations

        # System should still be in a valid state
        validators = list_validators()
        assert isinstance(validators, dict)

    def test_no_deadlock_with_nested_locks(self) -> None:
        """Test that nested operations don't cause deadlocks.

        Register a validator that itself tries to access the registry during
        validation to ensure no deadlock occurs.
        """

        def complex_validator(value: str) -> bool:
            # INTENTIONAL: This validator accesses the registry during validation
            # to test that nested lock acquisition doesn't cause deadlocks.
            # In production, avoid calling list_validators() in validators.
            all_validators = list_validators()
            return len(value) > 5 and "email" in all_validators

        register_validator("complex", complex_validator)

        results: List[bool] = []

        def use_complex_validator() -> None:
            validator = get_validator("complex")
            if validator:
                result = validator("test_value")
                results.append(result)

        # Use the complex validator from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(use_complex_validator) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # All operations should complete without deadlock
        assert len(results) == 50


class TestValidatorRegistryEdgeCases:
    """Tests for edge cases in concurrent validator registry operations."""

    def setup_method(self) -> None:
        """Clean up validators before each test."""
        clear_custom_validators()

    def teardown_method(self) -> None:
        """Clean up validators after each test."""
        clear_custom_validators()

    def test_concurrent_registration_builtin_conflict(self) -> None:
        """Test concurrent attempts to register built-in validator names.

        All attempts should fail with ValueError.
        """
        errors: List[Exception] = []

        def try_register_builtin() -> None:
            try:
                register_validator("email", _make_simple_validator())
            except ValueError as e:
                errors.append(e)

        # Try to register built-in name from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(try_register_builtin) for _ in range(20)]
            for future in as_completed(futures):
                future.result()

        # All attempts should raise ValueError
        assert len(errors) == 20
        assert all(isinstance(e, ValueError) for e in errors)
        assert all("conflicts with built-in validator" in str(e) for e in errors)

    def test_concurrent_get_nonexistent_validator(self) -> None:
        """Test concurrent reads of non-existent validators.

        All reads should safely return None without errors.
        """
        results: List[None] = []

        def get_nonexistent() -> None:
            validator = get_validator("does_not_exist")
            if validator is None:
                results.append(None)

        # Try to get non-existent validator from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_nonexistent) for _ in range(100)]
            for future in as_completed(futures):
                future.result()

        # All reads should return None
        assert len(results) == 100
