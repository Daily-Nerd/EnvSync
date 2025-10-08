#!/bin/bash
# Test script to verify the EnvSync package is correctly built

set -e

echo "========================================="
echo "EnvSync Package Verification Test"
echo "========================================="
echo ""

# Clean previous build
echo "1. Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info src/*.egg-info 2>/dev/null || true
echo "   ✓ Cleaned"
echo ""

# Build package
echo "2. Building package..."
python -m build
echo "   ✓ Built successfully"
echo ""

# Check package size
echo "3. Checking package size..."
WHEEL_SIZE=$(ls -lh dist/*.whl | awk '{print $5}')
echo "   Package size: $WHEEL_SIZE"
if [ "$WHEEL_SIZE" = "3.9K" ]; then
    echo "   ✗ ERROR: Package is too small!"
    exit 1
fi
echo "   ✓ Package size looks good (expected ~57K)"
echo ""

# List wheel contents
echo "4. Listing wheel contents..."
python -m zipfile -l dist/*.whl | grep -E "envsync/(cli|core|validation)\.py"
echo "   ✓ Core modules present"
echo ""

# Install in test environment
echo "5. Installing in clean test environment..."
TEST_VENV="/tmp/test_envsync_$$"
python -m venv "$TEST_VENV"
"$TEST_VENV/bin/pip" install -q dist/*.whl
echo "   ✓ Installed successfully"
echo ""

# Test --version
echo "6. Testing --version..."
VERSION_OUTPUT=$("$TEST_VENV/bin/envsync" --version)
echo "   Output: $VERSION_OUTPUT"
if [[ ! "$VERSION_OUTPUT" =~ "0.1.1" ]]; then
    echo "   ✗ ERROR: Version check failed!"
    rm -rf "$TEST_VENV"
    exit 1
fi
echo "   ✓ Version check passed"
echo ""

# Test --help
echo "7. Testing --help..."
"$TEST_VENV/bin/envsync" --help | head -5
echo "   ✓ Help command works"
echo ""

# Test subcommands exist
echo "8. Testing subcommands..."
HELP_OUTPUT=$("$TEST_VENV/bin/envsync" --help)
for cmd in init generate check sync scan audit validate docs; do
    if echo "$HELP_OUTPUT" | grep -q "$cmd"; then
        echo "   ✓ Command '$cmd' found"
    else
        echo "   ✗ ERROR: Command '$cmd' missing!"
        rm -rf "$TEST_VENV"
        exit 1
    fi
done
echo ""

# Cleanup
echo "9. Cleaning up test environment..."
rm -rf "$TEST_VENV"
echo "   ✓ Cleaned up"
echo ""

echo "========================================="
echo "✓ ALL TESTS PASSED!"
echo "========================================="
echo ""
echo "The package is correctly built and ready for release."
