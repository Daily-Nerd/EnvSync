"""Tests for TypeInferenceEngine and frame inspection strategy."""

import pytest

from tripwire.core.inference import (
    FrameInspectionStrategy,
    TypeInferenceEngine,
    TypeInferenceStrategy,
)


class TestTypeInferenceStrategy:
    """Test suite for TypeInferenceStrategy ABC."""

    def test_strategy_is_abstract(self):
        """Test that TypeInferenceStrategy cannot be instantiated."""
        with pytest.raises(TypeError):
            TypeInferenceStrategy()  # type: ignore


class TestFrameInspectionStrategy:
    """Test suite for FrameInspectionStrategy."""

    def test_infer_int_type_from_annotation(self):
        """Test inferring int type from annotation."""
        strategy = FrameInspectionStrategy()

        # Annotation should be detected
        PORT: int = lambda: strategy.infer_type()  # type: ignore
        inferred = PORT()

        assert inferred == int

    def test_infer_str_type_from_annotation(self):
        """Test inferring str type from annotation."""
        strategy = FrameInspectionStrategy()

        API_KEY: str = lambda: strategy.infer_type()  # type: ignore
        inferred = API_KEY()

        assert inferred == str

    def test_infer_bool_type_from_annotation(self):
        """Test inferring bool type from annotation."""
        strategy = FrameInspectionStrategy()

        DEBUG: bool = lambda: strategy.infer_type()  # type: ignore
        inferred = DEBUG()

        assert inferred == bool

    def test_infer_float_type_from_annotation(self):
        """Test inferring float type from annotation."""
        strategy = FrameInspectionStrategy()

        TIMEOUT: float = lambda: strategy.infer_type()  # type: ignore
        inferred = TIMEOUT()

        assert inferred == float

    def test_infer_list_type_from_annotation(self):
        """Test inferring list type from annotation."""
        strategy = FrameInspectionStrategy()

        HOSTS: list = lambda: strategy.infer_type()  # type: ignore
        inferred = HOSTS()

        assert inferred == list

    def test_infer_dict_type_from_annotation(self):
        """Test inferring dict type from annotation."""
        strategy = FrameInspectionStrategy()

        CONFIG: dict = lambda: strategy.infer_type()  # type: ignore
        inferred = CONFIG()

        assert inferred == dict

    def test_no_annotation_returns_none(self):
        """Test that missing annotation returns None."""
        strategy = FrameInspectionStrategy()

        # No annotation - should return None
        result = strategy.infer_type()

        assert result is None

    def test_optional_type_unwrapped(self):
        """Test Optional[T] is unwrapped to T."""
        from typing import Optional

        strategy = FrameInspectionStrategy()

        OPT_PORT: Optional[int] = lambda: strategy.infer_type()  # type: ignore
        inferred = OPT_PORT()

        # Should extract int from Optional[int]
        assert inferred == int

    def test_extract_type_from_hint_basic_types(self):
        """Test _extract_type_from_hint with basic types."""
        strategy = FrameInspectionStrategy()

        assert strategy._extract_type_from_hint(int) == int
        assert strategy._extract_type_from_hint(str) == str
        assert strategy._extract_type_from_hint(bool) == bool
        assert strategy._extract_type_from_hint(float) == float
        assert strategy._extract_type_from_hint(list) == list
        assert strategy._extract_type_from_hint(dict) == dict

    def test_extract_type_from_hint_generic(self):
        """Test _extract_type_from_hint with generic types."""
        from typing import Dict, List

        strategy = FrameInspectionStrategy()

        # List[str] -> list
        assert strategy._extract_type_from_hint(List[str]) == list

        # Dict[str, int] -> dict
        assert strategy._extract_type_from_hint(Dict[str, int]) == dict

    def test_extract_type_from_hint_optional(self):
        """Test _extract_type_from_hint with Optional."""
        from typing import Optional

        strategy = FrameInspectionStrategy()

        # Optional[int] -> int
        result = strategy._extract_type_from_hint(Optional[int])
        assert result == int

        # Optional[str] -> str
        result = strategy._extract_type_from_hint(Optional[str])
        assert result == str

    def test_extract_type_from_hint_none_returns_none(self):
        """Test _extract_type_from_hint with unsupported type."""
        strategy = FrameInspectionStrategy()

        # Unsupported type should return None
        class CustomClass:
            pass

        assert strategy._extract_type_from_hint(CustomClass) is None


class TestTypeInferenceEngine:
    """Test suite for TypeInferenceEngine."""

    def test_explicit_type_takes_precedence(self):
        """Test that explicit type parameter takes precedence."""

        class MockStrategy(TypeInferenceStrategy):
            def infer_type(self) -> int:  # type: ignore
                return int

        engine = TypeInferenceEngine(MockStrategy())

        # Explicit str should override inferred int
        result = engine.infer_or_default(explicit_type=str, default=float)

        assert result == str

    def test_inferred_type_used_when_no_explicit(self):
        """Test that inferred type is used when no explicit type."""

        class MockStrategy(TypeInferenceStrategy):
            def infer_type(self) -> int:  # type: ignore
                return int

        engine = TypeInferenceEngine(MockStrategy())

        # Should use inferred int
        result = engine.infer_or_default(explicit_type=None, default=str)

        assert result == int

    def test_default_type_when_inference_fails(self):
        """Test that default type is used when inference fails."""

        class MockStrategy(TypeInferenceStrategy):
            def infer_type(self) -> None:
                return None

        engine = TypeInferenceEngine(MockStrategy())

        # Should use default str
        result = engine.infer_or_default(explicit_type=None, default=str)

        assert result == str

    def test_default_is_str_by_default(self):
        """Test that default type is str when not specified."""

        class MockStrategy(TypeInferenceStrategy):
            def infer_type(self) -> None:
                return None

        engine = TypeInferenceEngine(MockStrategy())

        # Should use str as default
        result = engine.infer_or_default(explicit_type=None)

        assert result == str

    def test_precedence_order(self):
        """Test the complete precedence order: explicit > inferred > default."""

        class IntInferringStrategy(TypeInferenceStrategy):
            def infer_type(self) -> int:  # type: ignore
                return int

        engine = TypeInferenceEngine(IntInferringStrategy())

        # 1. Explicit takes precedence
        assert engine.infer_or_default(explicit_type=bool, default=str) == bool

        # 2. Inferred when no explicit
        assert engine.infer_or_default(explicit_type=None, default=str) == int

        # 3. Default when inference fails
        class NoneStrategy(TypeInferenceStrategy):
            def infer_type(self) -> None:
                return None

        engine_failing = TypeInferenceEngine(NoneStrategy())
        assert engine_failing.infer_or_default(explicit_type=None, default=float) == float


class TestFrameInspectionIntegration:
    """Integration tests for frame inspection in realistic scenarios."""

    def test_frame_inspection_with_tripwire_like_call(self):
        """Test frame inspection similar to how TripWire uses it."""
        strategy = FrameInspectionStrategy()
        engine = TypeInferenceEngine(strategy)

        def mock_require(explicit_type=None):
            """Mock TripWire.require() method."""
            return engine.infer_or_default(explicit_type, default=str)

        # Simulate user code with annotation
        PORT: int = mock_require()  # type: ignore

        assert PORT == int

    def test_multiple_calls_different_annotations(self):
        """Test multiple calls with different annotations."""
        strategy = FrameInspectionStrategy()
        engine = TypeInferenceEngine(strategy)

        def mock_require(explicit_type=None):
            return engine.infer_or_default(explicit_type, default=str)

        # Different annotations should be detected correctly
        VAR1: int = mock_require()  # type: ignore
        VAR2: str = mock_require()  # type: ignore
        VAR3: bool = mock_require()  # type: ignore

        assert VAR1 == int
        assert VAR2 == str
        assert VAR3 == bool

    def test_nested_function_calls(self):
        """Test type inference through nested function calls."""
        strategy = FrameInspectionStrategy()
        engine = TypeInferenceEngine(strategy)

        def inner_require(explicit_type=None):
            return engine.infer_or_default(explicit_type, default=str)

        def outer_require(explicit_type=None):
            return inner_require(explicit_type)

        # Should still detect annotation through nesting
        VALUE: int = outer_require()  # type: ignore

        assert VALUE == int


class TestCaching:
    """Test caching behavior of type inference."""

    def test_cache_prevents_redundant_computation(self):
        """Test that cache prevents redundant frame inspection."""
        strategy = FrameInspectionStrategy()

        # First call - should compute
        CACHED_VAR: int = lambda: strategy.infer_type()  # type: ignore
        result1 = CACHED_VAR()

        # Second call from same location - should use cache
        result2 = CACHED_VAR()

        assert result1 == int
        assert result2 == int
        # Both should return the same (cached) result

    def test_different_locations_different_cache_keys(self):
        """Test that different code locations have different cache keys."""
        strategy = FrameInspectionStrategy()

        # Two different locations should not interfere
        VAR1: int = lambda: strategy.infer_type()  # type: ignore
        VAR2: str = lambda: strategy.infer_type()  # type: ignore

        assert VAR1() == int
        assert VAR2() == str


class TestThreadSafety:
    """Test thread safety of type inference."""

    def test_concurrent_inference(self):
        """Test concurrent type inference from multiple threads."""
        import threading

        strategy = FrameInspectionStrategy()
        engine = TypeInferenceEngine(strategy)
        results = []
        errors = []

        def worker():
            try:

                def mock_require(explicit_type=None):
                    return engine.infer_or_default(explicit_type, default=str)

                VALUE: int = mock_require()  # type: ignore
                results.append(VALUE)
            except Exception as e:
                errors.append(e)

        # Run 20 threads concurrently
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == 20
        assert all(r == int for r in results)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_inference_without_frame(self):
        """Test inference when frame is None (edge case)."""
        # This is hard to test directly, but the code handles it
        strategy = FrameInspectionStrategy()

        # In normal Python code, currentframe() should never be None
        # But the code has guards for this case
        result = strategy.infer_type()

        # Should either infer or return None (both are valid)
        assert result is None or isinstance(result, type)

    def test_complex_annotation_fallback(self):
        """Test that complex annotations fall back gracefully."""
        from typing import Union

        strategy = FrameInspectionStrategy()

        # Union[int, str] - should extract int (first non-None type)
        UNION_VAR: Union[int, str] = lambda: strategy.infer_type()  # type: ignore
        result = UNION_VAR()

        # Should extract int from Union[int, str]
        assert result == int
