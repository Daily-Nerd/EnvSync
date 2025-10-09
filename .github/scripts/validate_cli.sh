#!/usr/bin/env bash
# Validates CLI installation in CI/CD workflows
# Uses behavior-based testing, not exact string matching
#
# Usage:
#   ./validate_cli.sh [expected_version]
#
# Exit codes:
#   0 - All validations passed
#   1 - One or more validations failed

set -euo pipefail

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Collect failures for summary
declare -a FAILED_TESTS

#######################################
# Helper Functions
#######################################

log_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

log_info() {
    echo -e "${CYAN}→${NC} $1"
}

log_section() {
    echo ""
    echo -e "${YELLOW}===${NC} $1"
}

#######################################
# Validation Tests
#######################################

test_command_exists() {
    log_info "Testing: tripwire command is available in PATH"

    if command -v tripwire &> /dev/null; then
        log_success "tripwire command found in PATH"
        return 0
    else
        log_error "tripwire command not found in PATH"
        return 1
    fi
}

test_basic_execution() {
    log_info "Testing: Basic command execution (--help)"

    if tripwire --help > /dev/null 2>&1; then
        log_success "tripwire --help executes successfully"
        return 0
    else
        log_error "tripwire --help failed to execute"
        return 1
    fi
}

test_version_flag() {
    local expected_version="$1"
    log_info "Testing: Version flag (expecting: $expected_version)"

    # Capture version output
    local version_output
    if ! version_output=$(tripwire --version 2>&1); then
        log_error "tripwire --version failed to execute"
        return 1
    fi

    # Extract version with flexible regex (handles various formats)
    if [[ $version_output =~ ([0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?) ]]; then
        local actual_version="${BASH_REMATCH[1]}"

        if [ "$actual_version" == "$expected_version" ]; then
            log_success "Version matches: $actual_version"
            return 0
        else
            log_error "Version mismatch: got '$actual_version', expected '$expected_version'"
            return 1
        fi
    else
        log_error "Could not extract version from output: $version_output"
        return 1
    fi
}

test_help_structure() {
    log_info "Testing: Help output structure (not exact text)"

    local help_output
    if ! help_output=$(tripwire --help 2>&1); then
        log_error "Failed to get help output"
        return 1
    fi

    # Test structural elements exist (case-insensitive)
    local output_lower
    output_lower=$(echo "$help_output" | tr '[:upper:]' '[:lower:]')

    local has_usage=false
    local has_options=false
    local has_program_name=false

    [[ $output_lower =~ "usage:" ]] && has_usage=true
    [[ $output_lower =~ "options:" ]] && has_options=true
    [[ $output_lower =~ "tripwire" ]] && has_program_name=true

    if $has_usage && $has_options && $has_program_name; then
        log_success "Help output has expected structure (usage, options, program name)"
        return 0
    else
        log_error "Help output missing expected structure"
        [[ $has_usage == false ]] && echo "  Missing: Usage section"
        [[ $has_options == false ]] && echo "  Missing: Options section"
        [[ $has_program_name == false ]] && echo "  Missing: Program name"
        return 1
    fi
}

test_help_not_empty() {
    log_info "Testing: Help output is substantial (not empty)"

    local help_output
    help_output=$(tripwire --help 2>&1)

    local length=${#help_output}

    if [ "$length" -gt 100 ]; then
        log_success "Help output is substantial ($length characters)"
        return 0
    else
        log_error "Help output too short ($length characters)"
        return 1
    fi
}

test_commands_available() {
    log_info "Testing: All expected commands execute without crashing"

    local commands=("init" "generate" "check" "sync" "scan" "audit" "validate" "docs")
    local all_passed=true

    for cmd in "${commands[@]}"; do
        if tripwire "$cmd" --help > /dev/null 2>&1; then
            # Don't log individual successes to reduce noise
            :
        else
            log_error "Command failed: $cmd --help"
            all_passed=false
        fi
    done

    if $all_passed; then
        log_success "All ${#commands[@]} commands available and executable"
        return 0
    else
        return 1
    fi
}

test_python_imports() {
    log_info "Testing: Python imports work correctly"

    # Run Python import test
    if python3 - <<'EOF'
import sys

try:
    # Test basic import
    import tripwire

    # Test core components
    from tripwire import env, TripWire

    # Test exceptions
    from tripwire import (
        TripWireError,
        MissingVariableError,
        ValidationError,
    )

    # Test validator
    from tripwire import validator

    # All imports successful
    sys.exit(0)

except ImportError as e:
    print(f"Import failed: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    then
        log_success "All Python imports work correctly"
        return 0
    else
        log_error "Python imports failed"
        return 1
    fi
}

test_version_consistency() {
    log_info "Testing: CLI version matches package version"

    # Get CLI version
    local cli_output
    cli_output=$(tripwire --version 2>&1)

    if [[ $cli_output =~ ([0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?) ]]; then
        local cli_version="${BASH_REMATCH[1]}"

        # Get package version
        local pkg_version
        pkg_version=$(python3 -c "import tripwire; print(tripwire.__version__)" 2>&1)

        if [ "$cli_version" == "$pkg_version" ]; then
            log_success "CLI version matches package version: $cli_version"
            return 0
        else
            log_error "Version mismatch: CLI=$cli_version, Package=$pkg_version"
            return 1
        fi
    else
        log_error "Could not extract CLI version"
        return 1
    fi
}

test_functional_workflow() {
    log_info "Testing: Functional workflow (init creates files)"

    # Create temporary directory
    local test_dir
    test_dir=$(mktemp -d)

    # Run test in isolated environment
    (
        cd "$test_dir" || exit 1

        # Test init command
        if ! tripwire init --project-type=cli > /dev/null 2>&1; then
            echo "init command failed" >&2
            exit 1
        fi

        # Check files were created
        if [ ! -f ".env" ]; then
            echo ".env not created" >&2
            exit 1
        fi

        if [ ! -f ".env.example" ]; then
            echo ".env.example not created" >&2
            exit 1
        fi

        # Check files have content
        if [ ! -s ".env" ]; then
            echo ".env is empty" >&2
            exit 1
        fi

        if [ ! -s ".env.example" ]; then
            echo ".env.example is empty" >&2
            exit 1
        fi

        exit 0
    )

    local result=$?

    # Cleanup
    rm -rf "$test_dir"

    if [ $result -eq 0 ]; then
        log_success "init command creates expected files with content"
        return 0
    else
        log_error "Functional workflow test failed"
        return 1
    fi
}

test_json_output_valid() {
    log_info "Testing: Commands with --json produce valid JSON"

    local test_dir
    test_dir=$(mktemp -d)

    (
        cd "$test_dir" || exit 1

        # Create test files
        echo "VAR1=value1" > .env
        echo "VAR1=" > .env.example
        echo "VAR2=" >> .env.example

        # Test check --json
        local json_output
        json_output=$(tripwire check --json 2>&1)

        # Validate JSON with Python
        python3 - <<EOF
import sys
import json

try:
    data = json.loads('''$json_output''')
    if not isinstance(data, dict):
        print("JSON output is not a dictionary", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    )

    local result=$?
    rm -rf "$test_dir"

    if [ $result -eq 0 ]; then
        log_success "Commands produce valid JSON output"
        return 0
    else
        log_error "JSON output validation failed"
        return 1
    fi
}

test_error_handling() {
    log_info "Testing: CLI handles errors gracefully (no crashes)"

    local all_passed=true

    # Test 1: Invalid command
    if tripwire invalid_command_xyz > /dev/null 2>&1; then
        # Should fail, not succeed
        log_error "Invalid command should return non-zero exit code"
        all_passed=false
    fi

    # Test 2: Missing file (check should handle gracefully)
    local test_dir
    test_dir=$(mktemp -d)

    (
        cd "$test_dir" || exit 1
        # No .env file exists
        tripwire check > /dev/null 2>&1
        # Should exit gracefully (not crash)
        exit 0
    )

    if [ $? -ne 0 ]; then
        all_passed=false
    fi

    rm -rf "$test_dir"

    if $all_passed; then
        log_success "CLI handles errors gracefully (no crashes)"
        return 0
    else
        log_error "Error handling test failed"
        return 1
    fi
}

#######################################
# Main Execution
#######################################

main() {
    local expected_version="${1:-}"

    echo "========================================="
    echo "TripWire CLI Validation"
    echo "========================================="

    if [ -n "$expected_version" ]; then
        echo "Expected version: $expected_version"
    fi

    echo ""

    # Run all validation tests
    log_section "Basic Functionality"
    test_command_exists || true
    test_basic_execution || true
    test_help_structure || true
    test_help_not_empty || true

    if [ -n "$expected_version" ]; then
        log_section "Version Validation"
        test_version_flag "$expected_version" || true
        test_version_consistency || true
    fi

    log_section "Command Availability"
    test_commands_available || true

    log_section "Python Integration"
    test_python_imports || true

    log_section "Functional Tests"
    test_functional_workflow || true
    test_json_output_valid || true

    log_section "Error Handling"
    test_error_handling || true

    # Summary
    echo ""
    echo "========================================="
    echo "Test Summary"
    echo "========================================="
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"

    if [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done

        echo ""
        echo -e "${RED}Validation failed${NC}"
        exit 1
    else
        echo ""
        echo -e "${GREEN}All validations passed!${NC}"
        exit 0
    fi
}

# Run with optional version argument
main "$@"
