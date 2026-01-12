#!/bin/bash
# Run all unit tests for WebRadio Player

echo "======================================"
echo "WebRadio Player - Running Unit Tests"
echo "======================================"
echo ""

# Set PYTHONPATH to include src directory
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Run tests with unittest discovery
python3 -m unittest discover -s tests/unit -p "test_*.py" -v

# Capture exit code
EXIT_CODE=$?

echo ""
echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed"
fi
echo "======================================"

exit $EXIT_CODE
