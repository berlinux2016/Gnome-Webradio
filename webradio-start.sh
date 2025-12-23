#!/bin/bash
# WebRadio Player Starter mit Debugging

set -e

echo "================================================"
echo "  WebRadio Player Starter"
echo "================================================"
echo ""

# Prüfe DISPLAY
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY variable not set!"
    echo "Please run this from a graphical session"
    exit 1
fi

echo "Display: $DISPLAY"
echo "Python: $(python3 --version)"
echo ""

# Set up environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export GST_DEBUG=1  # Reduced GStreamer debug output

echo "Starting WebRadio Player..."
echo "Press Ctrl+C to stop"
echo ""

# Start with output
cd "$(dirname "$0")"
exec python3 -u -m webradio.main 2>&1
