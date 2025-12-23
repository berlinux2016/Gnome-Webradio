#!/bin/bash
# RPM Build Script for WebRadio Player
# This script automates the entire RPM build process

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}WebRadio Player - RPM Build${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# Check if required tools are installed
echo -e "${YELLOW}Checking required tools...${NC}"
MISSING_TOOLS=""

for tool in rpmbuild rpmdev-setuptree python3 desktop-file-validate appstream-util; do
    if ! command -v $tool &> /dev/null; then
        MISSING_TOOLS="$MISSING_TOOLS $tool"
    fi
done

if [ ! -z "$MISSING_TOOLS" ]; then
    echo -e "${RED}Error: Missing required tools:$MISSING_TOOLS${NC}"
    echo ""
    echo "Install them with:"
    echo "  sudo dnf install rpm-build rpmdevtools python3-devel desktop-file-utils libappstream-glib"
    exit 1
fi

echo -e "${GREEN}All required tools found!${NC}"
echo ""

# Setup RPM build environment
echo -e "${YELLOW}Setting up RPM build environment...${NC}"
rpmdev-setuptree

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
make clean

# Create source tarball
echo -e "${YELLOW}Creating source tarball...${NC}"
python3 setup.py sdist

# Get version from setup.py
VERSION=$(python3 -c "from setuptools import setup; import sys; sys.argv = ['setup.py', '--version']; setup()" 2>/dev/null | tail -n1)

# Check for tarball with underscore (Python package naming)
TARBALL_UNDERSCORE="webradio_player-${VERSION}.tar.gz"
TARBALL_DASH="webradio-player-${VERSION}.tar.gz"

if [ -f "dist/$TARBALL_UNDERSCORE" ]; then
    TARBALL="$TARBALL_UNDERSCORE"
elif [ -f "dist/$TARBALL_DASH" ]; then
    TARBALL="$TARBALL_DASH"
else
    echo -e "${RED}Error: Source tarball not created!${NC}"
    echo "Expected: dist/$TARBALL_UNDERSCORE or dist/$TARBALL_DASH"
    exit 1
fi

echo -e "${GREEN}Found tarball: $TARBALL${NC}"

# Copy files to RPM build directories
echo -e "${YELLOW}Copying files to RPM build directories...${NC}"

# RPM spec expects webradio-player-VERSION.tar.gz (with dash)
# Python creates webradio_player-VERSION.tar.gz (with underscore)
# So we need to rename it
RPM_TARBALL="webradio-player-${VERSION}.tar.gz"
cp "dist/$TARBALL" ~/rpmbuild/SOURCES/"$RPM_TARBALL"
cp webradio.spec ~/rpmbuild/SPECS/

# Build RPM
echo -e "${YELLOW}Building RPM package...${NC}"
cd ~/rpmbuild
rpmbuild -ba SPECS/webradio.spec

# Check if build was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}RPM Build Successful!${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo "RPM packages created:"
    ls -lh ~/rpmbuild/RPMS/noarch/webradio-player-*.rpm 2>/dev/null
    echo ""
    echo "Source RPM:"
    ls -lh ~/rpmbuild/SRPMS/webradio-player-*.src.rpm 2>/dev/null
    echo ""
    echo "To install the package:"
    echo "  sudo dnf install ~/rpmbuild/RPMS/noarch/webradio-player-${VERSION}-1.*.rpm"
    echo ""
    echo "Or on other RPM-based systems:"
    echo "  sudo rpm -ivh ~/rpmbuild/RPMS/noarch/webradio-player-${VERSION}-1.*.rpm"

    # Copy to project directory
    echo ""
    echo -e "${YELLOW}Copying RPM to project directory...${NC}"
    cp ~/rpmbuild/RPMS/noarch/webradio-player-*.rpm "$SCRIPT_DIR/" 2>/dev/null || true
    cp ~/rpmbuild/SRPMS/webradio-player-*.src.rpm "$SCRIPT_DIR/" 2>/dev/null || true

    if [ -f "$SCRIPT_DIR/webradio-player-${VERSION}-1.*.rpm" ]; then
        echo -e "${GREEN}RPM copied to: $SCRIPT_DIR/${NC}"
    fi
else
    echo ""
    echo -e "${RED}=================================${NC}"
    echo -e "${RED}RPM Build Failed!${NC}"
    echo -e "${RED}=================================${NC}"
    echo ""
    echo "Check the build log above for errors."
    exit 1
fi
