# TripWire Performance Benchmarks

This directory contains performance benchmarks for TripWire, measuring the execution time of various operations.

## Running Benchmarks

To run the full benchmark suite:

```bash
uv run python benchmarks/performance.py
```

This will:
1. Run all benchmarks with proper warmup
2. Display results in the terminal
3. Generate a detailed report in `benchmarks/results.txt`

## Benchmark Categories

### Core Operations
- **env.require()** - Variable retrieval with type coercion
- **env.optional()** - Optional variables with defaults
- **Validation** - Format validators (email, URL, etc.)

### Parser Operations
- **Simple parsing** - Basic .env file parsing
- **With interpolation** - Variable expansion support
- **Variable expansion** - ${VAR} syntax processing

### Type Coercion
- **List coercion** - Multiple formats (CSV, JSON, quoted)
- **Dict coercion** - JSON objects and key=value pairs

### Plugin System
- **Validator registration** - Custom validator registration

### Configuration
- **Config parsing** - .tripwire.toml parsing

## Performance Metrics

All benchmarks report:
- **Average time** - Mean execution time across iterations
- **Minimum time** - Fastest execution
- **Maximum time** - Slowest execution (includes outliers)
- **Iterations** - Number of test runs

## Typical Results

On a modern system (Apple M1/M2, 2023):

| Operation | Avg Time | Notes |
|-----------|----------|-------|
| env.require() | ~0.001ms | Very fast, minimal overhead |
| Parser (simple) | ~0.03ms | Efficient for typical files |
| Parser (interpolation) | ~0.03ms | Interpolation adds minimal overhead |
| Variable expansion | ~0.002ms | Fast recursive expansion |
| List coercion (simple) | ~0.001ms | Fastest format |
| List coercion (JSON) | ~0.002ms | JSON parsing overhead |
| Dict coercion (JSON) | ~0.001ms | Native JSON performance |
| Dict coercion (key=value) | ~0.008ms | Smart parsing with quotes |
| Email validation | ~0.0005ms | Regex-based, very fast |
| URL validation | ~0.0006ms | Similar to email |

## Performance Characteristics

### What's Fast?
- Basic variable retrieval (<0.002ms)
- Simple type coercion (<0.002ms)
- Built-in validators (<0.001ms)
- Variable expansion (<0.002ms)

### What Takes More Time?
- Complex parsing with quotes (~0.008ms for dicts)
- File I/O operations (not benchmarked, varies by system)
- Custom validators (depends on implementation)

### Optimization Tips

1. **Use simple formats when possible**
   - CSV lists are faster than JSON
   - Direct types are faster than coercion

2. **Cache parsed configurations**
   - Parse .tripwire.toml once at startup
   - Reuse TripWire instances

3. **Minimize validation**
   - Use format validators only when needed
   - Custom validators should be optimized

4. **Batch operations**
   - Load all env files at initialization
   - Avoid repeated parsing

## Interpreting Results

### Good Performance
- Sub-millisecond operation times
- Minimal variance between min/max
- Linear scaling with data size

### Performance Issues
If you see significantly slower times:
1. Check for I/O bottlenecks
2. Profile custom validators
3. Review complex regex patterns
4. Check for excessive file operations

## Continuous Monitoring

Run benchmarks:
- Before major releases
- After optimization changes
- When adding new features
- To detect performance regressions

## Contributing

When adding new features:
1. Add corresponding benchmarks
2. Document expected performance
3. Compare against baseline
4. Optimize if regression detected
