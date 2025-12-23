#!/bin/bash
# Install GSettings schema for development

set -e

SCHEMA_FILE="data/org.webradio.Player.gschema.xml"
SCHEMA_DIR="$HOME/.local/share/glib-2.0/schemas"

# Create directory if it doesn't exist
mkdir -p "$SCHEMA_DIR"

# Copy schema file
echo "Installing GSettings schema..."
cp "$SCHEMA_FILE" "$SCHEMA_DIR/"

# Compile schemas
echo "Compiling GSettings schemas..."
glib-compile-schemas "$SCHEMA_DIR"

echo "✓ GSettings schema installed successfully!"
echo ""
echo "The schema is now available for development."
echo "To uninstall: rm $SCHEMA_DIR/org.webradio.Player.gschema.xml && glib-compile-schemas $SCHEMA_DIR"
