#!/usr/bin/env bash
# Test script for TFT auto-configuration
# Tests the automatic detection and configuration logic

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
test_passed() {
    echo -e "${GREEN}✓ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_failed() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

echo "=== TFT Auto-Configuration Tests ==="
echo ""

# Test 1: Check if auto_configure_tft.sh exists
echo "Test 1: Checking if auto_configure_tft.sh exists..."
if [ -f "scripts/auto_configure_tft.sh" ]; then
    test_passed "auto_configure_tft.sh exists"
else
    test_failed "auto_configure_tft.sh not found"
fi

# Test 2: Check if script is executable
echo "Test 2: Checking if auto_configure_tft.sh is executable..."
if [ -x "scripts/auto_configure_tft.sh" ]; then
    test_passed "auto_configure_tft.sh is executable"
else
    test_failed "auto_configure_tft.sh is not executable"
fi

# Test 3: Check if detect_tft.sh exists
echo "Test 3: Checking if detect_tft.sh exists..."
if [ -f "scripts/detect_tft.sh" ]; then
    test_passed "detect_tft.sh exists"
else
    test_failed "detect_tft.sh not found"
fi

# Test 4: Check if install_tft_autoconfig_service.sh exists
echo "Test 4: Checking if install_tft_autoconfig_service.sh exists..."
if [ -f "scripts/install_tft_autoconfig_service.sh" ]; then
    test_passed "install_tft_autoconfig_service.sh exists"
else
    test_failed "install_tft_autoconfig_service.sh not found"
fi

# Test 5: Verify tft_display.py exists
echo "Test 5: Checking if tft_display.py exists..."
if [ -f "scripts/tft_display.py" ]; then
    test_passed "tft_display.py exists"
else
    test_failed "tft_display.py not found"
fi

# Test 6: Check for standby mode in tft_display.py
echo "Test 6: Checking if tft_display.py has standby mode..."
if grep -q "standby mode" scripts/tft_display.py; then
    test_passed "tft_display.py has standby mode implementation"
else
    test_failed "tft_display.py missing standby mode"
fi

# Test 7: Check for fallback mode in tft_display.py
echo "Test 7: Checking if tft_display.py has fallback mode..."
if grep -q "fallback mode" scripts/tft_display.py; then
    test_passed "tft_display.py has fallback mode implementation"
else
    test_failed "tft_display.py missing fallback mode"
fi

# Test 8: Check if install_services.sh has auto-configuration
echo "Test 8: Checking if install_services.sh includes auto-configuration..."
if grep -q "install_tft_autoconfig_service" scripts/install_services.sh; then
    test_passed "install_services.sh includes auto-configuration setup"
else
    test_failed "install_services.sh missing auto-configuration"
fi

# Test 9: Check if install_tft.sh enables TFT by default
echo "Test 9: Checking if install_tft.sh enables TFT by default..."
if grep -q "TFT_ENABLED=1" scripts/install_tft.sh; then
    test_passed "install_tft.sh enables TFT by default"
else
    test_failed "install_tft.sh doesn't enable TFT by default"
fi

# Test 10: Verify syntax of bash scripts
echo "Test 10: Checking bash script syntax..."
SYNTAX_OK=true

for script in scripts/auto_configure_tft.sh scripts/detect_tft.sh scripts/install_tft_autoconfig_service.sh; do
    if [ -f "$script" ]; then
        if ! bash -n "$script" 2>/dev/null; then
            SYNTAX_OK=false
            echo "  Syntax error in $script"
        fi
    fi
done

if [ "$SYNTAX_OK" = true ]; then
    test_passed "All bash scripts have valid syntax"
else
    test_failed "Some bash scripts have syntax errors"
fi

# Test 11: Check Python script syntax
echo "Test 11: Checking Python script syntax..."
if command -v python3 &>/dev/null; then
    if python3 -m py_compile scripts/tft_display.py 2>/dev/null; then
        test_passed "tft_display.py has valid Python syntax"
    else
        test_failed "tft_display.py has syntax errors"
    fi
else
    echo -e "${YELLOW}⚠ Python3 not available, skipping syntax check${NC}"
fi

# Test 12: Check for auto-detection functions
echo "Test 12: Checking for auto-detection functions in auto_configure_tft.sh..."
DETECTION_FUNCTIONS_OK=true

for func in "detect_tft_type" "detect_resolution" "check_tft_hardware"; do
    if ! grep -q "$func()" scripts/auto_configure_tft.sh; then
        DETECTION_FUNCTIONS_OK=false
        echo "  Missing function: $func"
    fi
done

if [ "$DETECTION_FUNCTIONS_OK" = true ]; then
    test_passed "All required detection functions present"
else
    test_failed "Some detection functions are missing"
fi

# Test 13: Check for configuration update function
echo "Test 13: Checking for configuration update function..."
if grep -q "update_birdnet_conf" scripts/auto_configure_tft.sh; then
    test_passed "Configuration update function present"
else
    test_failed "Configuration update function missing"
fi

# Test 14: Verify portrait mode default
echo "Test 14: Checking for portrait mode default (90 degrees)..."
if grep -q "rotation=90" scripts/auto_configure_tft.sh; then
    test_passed "Portrait mode (90°) is set as default"
else
    test_failed "Portrait mode not set as default"
fi

# Test 15: Check for backup functionality
echo "Test 15: Checking for configuration backup..."
if grep -q "backup" scripts/auto_configure_tft.sh; then
    test_passed "Configuration backup functionality present"
else
    test_failed "Configuration backup missing"
fi

# Summary
echo ""
echo "=== Test Summary ==="
echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the implementation.${NC}"
    exit 1
fi
