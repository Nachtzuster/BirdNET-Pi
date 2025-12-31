#!/usr/bin/env bash
# Test script for TFT display wrapper functionality

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Function to print test result
print_result() {
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$1" = "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}✓ PASS${NC}: $2"
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
    fi
}

echo "=== Testing TFT Display Wrapper Script ==="
echo ""

# Test 1: Check wrapper script exists
echo "Test 1: Wrapper script exists"
if [ -f "scripts/tft_display_wrapper.sh" ]; then
    print_result "PASS" "Wrapper script found"
else
    print_result "FAIL" "Wrapper script not found"
fi

# Test 2: Check wrapper script is executable
echo "Test 2: Wrapper script is executable"
if [ -x "scripts/tft_display_wrapper.sh" ]; then
    print_result "PASS" "Wrapper script is executable"
else
    print_result "FAIL" "Wrapper script is not executable"
fi

# Test 3: Check bash syntax
echo "Test 3: Wrapper script bash syntax"
if bash -n scripts/tft_display_wrapper.sh 2>/dev/null; then
    print_result "PASS" "Bash syntax is valid"
else
    print_result "FAIL" "Bash syntax errors found"
fi

# Test 4: Check shellcheck
echo "Test 4: Wrapper script shellcheck"
if command -v shellcheck &> /dev/null; then
    if shellcheck scripts/tft_display_wrapper.sh 2>/dev/null; then
        print_result "PASS" "Shellcheck passed"
    else
        print_result "FAIL" "Shellcheck found issues"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC}: Shellcheck not available"
fi

# Test 5: Check update script exists
echo "Test 5: Update script exists"
if [ -f "scripts/update_tft_script.sh" ]; then
    print_result "PASS" "Update script found"
else
    print_result "FAIL" "Update script not found"
fi

# Test 6: Check update script is executable
echo "Test 6: Update script is executable"
if [ -x "scripts/update_tft_script.sh" ]; then
    print_result "PASS" "Update script is executable"
else
    print_result "FAIL" "Update script is not executable"
fi

# Test 7: Check update script syntax
echo "Test 7: Update script bash syntax"
if bash -n scripts/update_tft_script.sh 2>/dev/null; then
    print_result "PASS" "Bash syntax is valid"
else
    print_result "FAIL" "Bash syntax errors found"
fi

# Test 8: Check install_tft_service.sh references wrapper
echo "Test 8: install_tft_service.sh references wrapper"
if grep -q "tft_display_wrapper.sh" scripts/install_tft_service.sh; then
    print_result "PASS" "install_tft_service.sh references wrapper"
else
    print_result "FAIL" "install_tft_service.sh doesn't reference wrapper"
fi

# Test 9: Check install_services.sh references wrapper
echo "Test 9: install_services.sh references wrapper"
if grep -q "tft_display_wrapper.sh" scripts/install_services.sh; then
    print_result "PASS" "install_services.sh references wrapper"
else
    print_result "FAIL" "install_services.sh doesn't reference wrapper"
fi

# Test 10: Check update_birdnet_snippets.sh references wrapper
echo "Test 10: update_birdnet_snippets.sh references wrapper"
if grep -q "tft_display_wrapper.sh" scripts/update_birdnet_snippets.sh; then
    print_result "PASS" "update_birdnet_snippets.sh references wrapper"
else
    print_result "FAIL" "update_birdnet_snippets.sh doesn't reference wrapper"
fi

# Test 11: Check documentation exists (Dutch)
echo "Test 11: Dutch documentation exists"
if [ -f "docs/TFT_EXIT_CODE_2_FIX_NL.md" ]; then
    print_result "PASS" "Dutch documentation found"
else
    print_result "FAIL" "Dutch documentation not found"
fi

# Test 12: Check documentation exists (English)
echo "Test 12: English documentation exists"
if [ -f "docs/TFT_EXIT_CODE_2_FIX.md" ]; then
    print_result "PASS" "English documentation found"
else
    print_result "FAIL" "English documentation not found"
fi

# Test 13: Check wrapper has error handling
echo "Test 13: Wrapper has error checking"
if grep -q "set -e" scripts/tft_display_wrapper.sh; then
    print_result "PASS" "Wrapper has 'set -e' for error handling"
else
    print_result "FAIL" "Wrapper missing 'set -e'"
fi

# Test 14: Check wrapper checks for repository script
echo "Test 14: Wrapper checks for repository script"
if grep -q "REPO_SCRIPT" scripts/tft_display_wrapper.sh && \
   grep -q "if \[ ! -f" scripts/tft_display_wrapper.sh; then
    print_result "PASS" "Wrapper checks for repository script"
else
    print_result "FAIL" "Wrapper doesn't check for repository script"
fi

# Test 15: Check wrapper compares timestamps
echo "Test 15: Wrapper compares file timestamps"
if grep -q "\-nt" scripts/tft_display_wrapper.sh; then
    print_result "PASS" "Wrapper compares file timestamps"
else
    print_result "FAIL" "Wrapper doesn't compare timestamps"
fi

# Test 16: Check wrapper has logging
echo "Test 16: Wrapper has logging function"
if grep -q "log_message" scripts/tft_display_wrapper.sh; then
    print_result "PASS" "Wrapper has logging function"
else
    print_result "FAIL" "Wrapper missing logging function"
fi

# Summary
echo ""
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $((TESTS_RUN - TESTS_PASSED))"
echo ""

if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
