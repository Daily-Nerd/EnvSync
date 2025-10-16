"""Performance tests for usage tracker.

Ensures analysis can handle large codebases efficiently.
Target: <1 second for 100 files, <5 seconds for 500 files.
"""

import time
from pathlib import Path

from tripwire.analysis.usage_tracker import UsageAnalyzer


def test_performance_100_files(tmp_path):
    """Should analyze 100 files in <1 second."""
    # Generate config with 10 variables
    config_file = tmp_path / "config.py"
    config_content = ["from tripwire import env"]
    for i in range(10):
        config_content.append(f'VAR_{i}: str = env.require("VAR_{i}")')
    config_file.write_text("\n".join(config_content))

    # Generate 100 Python files using those variables
    for file_idx in range(100):
        app_file = tmp_path / f"app_{file_idx}.py"
        usage_lines = ["from config import VAR_0, VAR_1, VAR_2"]
        usage_lines.append("def process():")
        usage_lines.append("    print(VAR_0)")
        usage_lines.append("    return VAR_1")
        usage_lines.append("    data = {'key': VAR_2}")
        app_file.write_text("\n".join(usage_lines))

    analyzer = UsageAnalyzer(tmp_path)

    start = time.time()
    result = analyzer.analyze()
    duration = time.time() - start

    # Verify correctness
    assert len(result.declarations) == 10
    assert len(result.used_variables) >= 3  # At least VAR_0, VAR_1, VAR_2

    # Verify performance
    print(f"\nAnalyzed 100 files in {duration:.3f} seconds")
    assert duration < 1.0, f"Performance target missed: {duration:.3f}s > 1.0s"


def test_performance_500_files(tmp_path):
    """Should analyze 500 files in <5 seconds."""
    # Generate config with 20 variables
    config_file = tmp_path / "config.py"
    config_content = ["from tripwire import env"]
    for i in range(20):
        config_content.append(f'VAR_{i}: str = env.require("VAR_{i}")')
    config_file.write_text("\n".join(config_content))

    # Generate 500 Python files
    for file_idx in range(500):
        app_file = tmp_path / f"app_{file_idx}.py"
        # Use a subset of variables
        var_subset = [0, 1, 2, file_idx % 20]
        imports = ", ".join([f"VAR_{i}" for i in var_subset])
        usage_lines = [f"from config import {imports}"]
        usage_lines.append("def process():")
        for i in var_subset:
            usage_lines.append(f"    print(VAR_{i})")
        app_file.write_text("\n".join(usage_lines))

    analyzer = UsageAnalyzer(tmp_path)

    start = time.time()
    result = analyzer.analyze()
    duration = time.time() - start

    # Verify correctness
    assert len(result.declarations) == 20
    assert len(result.used_variables) >= 4  # Should have usages

    # Verify performance
    print(f"\nAnalyzed 500 files in {duration:.3f} seconds")
    assert duration < 5.0, f"Performance target missed: {duration:.3f}s > 5.0s"


def test_complex_edge_cases_performance(tmp_path):
    """Should handle complex edge cases efficiently."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATABASE_URL: str = env.require("DATABASE_URL")
API_KEY: str = env.require("API_KEY")
DEBUG: bool = env.require("DEBUG")
MAX_ITEMS: int = env.require("MAX_ITEMS")
"""
    )

    # Create file with many edge cases
    complex_file = tmp_path / "complex.py"
    complex_file.write_text(
        """
from config import DATABASE_URL, API_KEY, DEBUG, MAX_ITEMS

# F-strings
url = f"{DATABASE_URL}/api"

# Comprehensions
items = [x for x in range(MAX_ITEMS)]
data = {k: API_KEY for k in ["a", "b", "c"]}

# Nested structures
config = {
    "db": DATABASE_URL,
    "api": {
        "key": API_KEY,
        "debug": DEBUG
    },
    "items": [MAX_ITEMS] * 3
}

# Control flow
if DEBUG:
    print(DATABASE_URL)

for i in range(MAX_ITEMS):
    print(API_KEY)

# Functions
def connect():
    return create_connection(DATABASE_URL)

def process(key=API_KEY):
    if key and DEBUG:
        return [x for x in range(MAX_ITEMS)]
"""
    )

    analyzer = UsageAnalyzer(tmp_path)

    start = time.time()
    result = analyzer.analyze()
    duration = time.time() - start

    # Verify all edge cases detected
    assert "DATABASE_URL" in result.used_variables
    assert "API_KEY" in result.used_variables
    assert "DEBUG" in result.used_variables
    assert "MAX_ITEMS" in result.used_variables

    # Should be fast even with complex file
    print(f"\nAnalyzed complex edge cases in {duration:.3f} seconds")
    assert duration < 0.5, f"Complex analysis too slow: {duration:.3f}s"
