#!/bin/bash
# Test script for WebRadio Player improvements

echo "=========================================="
echo "WebRadio Player - Testing Improvements"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -n "Testing $test_name... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "1. Python Syntax Validation"
echo "----------------------------"
run_test "logger.py syntax" "python3 -m py_compile src/webradio/logger.py"
run_test "player_advanced.py syntax" "python3 -m py_compile src/webradio/player_advanced.py"
run_test "player_factory.py syntax" "python3 -m py_compile src/webradio/player_factory.py"
run_test "exceptions.py syntax" "python3 -m py_compile src/webradio/exceptions.py"
echo ""

echo "2. Module Imports"
echo "----------------------------"
run_test "logger import" "python3 -c 'from webradio.logger import get_logger'"
run_test "player_advanced import" "python3 -c 'from webradio.player_advanced import AdvancedAudioPlayer'"
run_test "player_factory import" "python3 -c 'from webradio.player_factory import create_player'"
run_test "exceptions import" "python3 -c 'from webradio.exceptions import WebRadioException'"
echo ""

echo "3. Functional Tests"
echo "----------------------------"
run_test "Logger instantiation" "python3 -c 'from webradio.logger import get_logger; logger = get_logger(\"test\"); logger.info(\"Test\")'"
run_test "Exception hierarchy" "python3 -c 'from webradio.exceptions import RecordingException, WebRadioException; assert issubclass(RecordingException, WebRadioException)'"
echo ""

echo "4. File Structure"
echo "----------------------------"
run_test "Logger file exists" "test -f src/webradio/logger.py"
run_test "Advanced player exists" "test -f src/webradio/player_advanced.py"
run_test "Factory exists" "test -f src/webradio/player_factory.py"
run_test "Exceptions file exists" "test -f src/webradio/exceptions.py"
run_test "Improvements doc exists" "test -f IMPROVEMENTS.md"
run_test "CSS updated" "grep -q 'recording-active' data/webradio.css"
echo ""

echo "=========================================="
echo "Test Results"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "You can now run the application with:"
    echo "  python3 -m webradio"
    echo ""
    echo "Or use the start script:"
    echo "  sh webradio-start.sh"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the errors above.${NC}"
    exit 1
fi
