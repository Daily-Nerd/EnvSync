"""Performance benchmarks for EnvSync.

This module provides comprehensive performance benchmarks to measure
the execution time of various EnvSync operations.
"""

import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from envsync import env
from envsync.config import load_config, parse_config
from envsync.parser import EnvFileParser, expand_variables
from envsync.validation import (
    coerce_dict,
    coerce_list,
    register_validator,
    validate_email,
    validate_url,
)


def benchmark(func: Callable[[], None], iterations: int = 1000) -> Dict[str, float]:
    """Benchmark a function execution.

    Args:
        func: Function to benchmark
        iterations: Number of iterations to run

    Returns:
        Dictionary with timing statistics
    """
    times = []

    # Warmup
    for _ in range(10):
        func()

    # Actual benchmarking
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to milliseconds

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    median_time = sorted(times)[len(times) // 2]

    return {
        "avg_ms": round(avg_time, 4),
        "min_ms": round(min_time, 4),
        "max_ms": round(max_time, 4),
        "median_ms": round(median_time, 4),
        "total_ms": round(sum(times), 2),
        "iterations": iterations,
    }


def benchmark_env_require() -> Dict[str, float]:
    """Benchmark env.require() with type coercion."""
    os.environ["BENCH_VAR"] = "42"

    def test():
        env.require("BENCH_VAR", type=int)

    result = benchmark(test, iterations=10000)
    del os.environ["BENCH_VAR"]
    return result


def benchmark_env_require_validation() -> Dict[str, float]:
    """Benchmark env.require() with format validation."""
    os.environ["BENCH_EMAIL"] = "test@example.com"

    def test():
        env.require("BENCH_EMAIL", format="email")

    result = benchmark(test, iterations=10000)
    del os.environ["BENCH_EMAIL"]
    return result


def benchmark_env_optional() -> Dict[str, float]:
    """Benchmark env.optional() with default value."""

    def test():
        env.optional("NONEXISTENT_VAR", default="default_value")

    return benchmark(test, iterations=10000)


def benchmark_parser_simple() -> Dict[str, float]:
    """Benchmark simple .env parsing."""
    content = """
# Database configuration
DATABASE_URL=postgresql://localhost:5432/mydb
DATABASE_USER=postgres
DATABASE_PASSWORD=secret123

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application settings
DEBUG=true
LOG_LEVEL=info
"""

    parser = EnvFileParser()

    def test():
        parser.parse_string(content)

    return benchmark(test, iterations=1000)


def benchmark_parser_with_interpolation() -> Dict[str, float]:
    """Benchmark parsing with variable interpolation."""
    content = """
BASE_URL=https://api.example.com
API_V1=${BASE_URL}/v1
API_V2=${BASE_URL}/v2
USERS_ENDPOINT=${API_V1}/users
POSTS_ENDPOINT=${API_V1}/posts
COMMENTS_ENDPOINT=${API_V2}/comments
"""

    parser = EnvFileParser(expand_vars=True)

    def test():
        parser.parse_string(content)

    return benchmark(test, iterations=1000)


def benchmark_variable_expansion() -> Dict[str, float]:
    """Benchmark variable expansion function."""
    env_dict = {
        "HOST": "localhost",
        "PORT": "5432",
        "DB_NAME": "mydb",
    }
    value = "postgresql://${HOST}:${PORT}/${DB_NAME}"

    def test():
        expand_variables(value, env_dict, allow_os_environ=False)

    return benchmark(test, iterations=10000)


def benchmark_coerce_list_simple() -> Dict[str, float]:
    """Benchmark simple list coercion."""
    value = "item1, item2, item3, item4, item5"

    def test():
        coerce_list(value)

    return benchmark(test, iterations=10000)


def benchmark_coerce_list_json() -> Dict[str, float]:
    """Benchmark JSON list coercion."""
    value = '["item1", "item2", "item3", "item4", "item5"]'

    def test():
        coerce_list(value)

    return benchmark(test, iterations=10000)


def benchmark_coerce_list_quoted() -> Dict[str, float]:
    """Benchmark quoted CSV list coercion."""
    value = '"item 1", "item 2", "item 3", "item 4", "item 5"'

    def test():
        coerce_list(value)

    return benchmark(test, iterations=10000)


def benchmark_coerce_dict_json() -> Dict[str, float]:
    """Benchmark JSON dict coercion."""
    value = '{"key1": "value1", "key2": "value2", "key3": "value3"}'

    def test():
        coerce_dict(value)

    return benchmark(test, iterations=10000)


def benchmark_coerce_dict_keyvalue() -> Dict[str, float]:
    """Benchmark key=value dict coercion."""
    value = "key1=value1,key2=value2,key3=value3"

    def test():
        coerce_dict(value)

    return benchmark(test, iterations=10000)


def benchmark_email_validation() -> Dict[str, float]:
    """Benchmark email validation."""
    value = "user@example.com"

    def test():
        validate_email(value)

    return benchmark(test, iterations=10000)


def benchmark_url_validation() -> Dict[str, float]:
    """Benchmark URL validation."""
    value = "https://www.example.com/path?query=value"

    def test():
        validate_url(value)

    return benchmark(test, iterations=10000)


def benchmark_custom_validator_registration() -> Dict[str, float]:
    """Benchmark custom validator registration."""

    def validate_test(value: str) -> bool:
        return True

    counter = [0]

    def test():
        register_validator(f"test_{counter[0]}", validate_test)
        counter[0] += 1

    return benchmark(test, iterations=100)


def benchmark_config_parsing() -> Dict[str, float]:
    """Benchmark configuration parsing."""
    config_data = {
        "envsync": {
            "env_file": ".env",
            "strict": True,
            "detect_secrets": True,
        },
        "variables": {
            "DATABASE_URL": {"required": True, "type": "str", "format": "postgresql"},
            "REDIS_URL": {"required": True, "type": "str"},
            "PORT": {"required": False, "type": "int", "default": 8000, "min": 1024, "max": 65535},
            "DEBUG": {"required": False, "type": "bool", "default": False},
            "ALLOWED_HOSTS": {"required": False, "type": "list"},
        },
    }

    def test():
        parse_config(config_data)

    return benchmark(test, iterations=1000)


def run_all_benchmarks() -> List[Tuple[str, Dict[str, float]]]:
    """Run all benchmarks and return results.

    Returns:
        List of tuples (benchmark_name, results)
    """
    benchmarks_list = [
        ("env.require() with type coercion", benchmark_env_require),
        ("env.require() with validation", benchmark_env_require_validation),
        ("env.optional() with default", benchmark_env_optional),
        ("Parser: Simple .env file", benchmark_parser_simple),
        ("Parser: With interpolation", benchmark_parser_with_interpolation),
        ("Variable expansion", benchmark_variable_expansion),
        ("List coercion (simple CSV)", benchmark_coerce_list_simple),
        ("List coercion (JSON array)", benchmark_coerce_list_json),
        ("List coercion (quoted CSV)", benchmark_coerce_list_quoted),
        ("Dict coercion (JSON object)", benchmark_coerce_dict_json),
        ("Dict coercion (key=value)", benchmark_coerce_dict_keyvalue),
        ("Email validation", benchmark_email_validation),
        ("URL validation", benchmark_url_validation),
        ("Custom validator registration", benchmark_custom_validator_registration),
        ("Config file parsing", benchmark_config_parsing),
    ]

    results = []
    for name, bench_func in benchmarks_list:
        print(f"Running: {name}...", end=" ", flush=True)
        result = bench_func()
        results.append((name, result))
        print(f"✓ ({result['avg_ms']:.4f}ms avg)")

    return results


def print_results(results: List[Tuple[str, Dict[str, float]]]) -> None:
    """Print benchmark results in a formatted table.

    Args:
        results: List of benchmark results
    """
    print("\n" + "=" * 90)
    print("EnvSync Performance Benchmark Results")
    print("=" * 90)
    print(f"{'Benchmark':<45} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}")
    print("-" * 90)

    for name, result in results:
        print(f"{name:<45} " f"{result['avg_ms']:>10.4f}  " f"{result['min_ms']:>10.4f}  " f"{result['max_ms']:>10.4f}")

    print("=" * 90)

    # Calculate some statistics
    total_operations = sum(r[1]["iterations"] for r in results)
    total_time = sum(r[1]["total_ms"] for r in results)

    print(f"\nTotal operations: {total_operations:,}")
    print(f"Total time: {total_time:.2f}ms ({total_time/1000:.2f}s)")
    print(f"Average operation time: {total_time/total_operations:.4f}ms")


def generate_performance_report(output_file: str = "benchmarks/results.txt") -> None:
    """Generate performance report and save to file.

    Args:
        output_file: Path to output file
    """
    results = run_all_benchmarks()

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("=" * 90 + "\n")
        f.write("EnvSync Performance Benchmark Results\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 90 + "\n\n")

        f.write(f"{'Benchmark':<45} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}\n")
        f.write("-" * 90 + "\n")

        for name, result in results:
            f.write(
                f"{name:<45} "
                f"{result['avg_ms']:>10.4f}  "
                f"{result['min_ms']:>10.4f}  "
                f"{result['max_ms']:>10.4f}\n"
            )

        f.write("=" * 90 + "\n\n")

        # Statistics
        total_operations = sum(r[1]["iterations"] for r in results)
        total_time = sum(r[1]["total_ms"] for r in results)

        f.write(f"Total operations: {total_operations:,}\n")
        f.write(f"Total time: {total_time:.2f}ms ({total_time/1000:.2f}s)\n")
        f.write(f"Average operation time: {total_time/total_operations:.4f}ms\n")

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    print("Starting EnvSync performance benchmarks...\n")
    results = run_all_benchmarks()
    print_results(results)
    print("\nGenerating report file...")
    generate_performance_report()
    print("\nBenchmarking complete!")
