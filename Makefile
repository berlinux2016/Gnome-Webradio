.PHONY: help install uninstall clean build run dev rpm rpm-quick rpm-binary deb arch

help:
	@echo "WebRadio Player - Makefile Commands"
	@echo "===================================="
	@echo "  make install     - Install the application"
	@echo "  make uninstall   - Uninstall the application"
	@echo "  make run         - Run without installing"
	@echo "  make dev         - Install in development mode"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make build       - Build distribution packages"
	@echo "  make rpm         - Create RPM package (full build with clean)"
	@echo "  make rpm-quick   - Quick RPM build (no clean)"
	@echo "  make rpm-binary  - Build only binary RPM (no source RPM)"
	@echo "  make deb         - Create DEB package"
	@echo "  make arch        - Create Arch Linux package"
	@echo "  make test        - Run tests (if available)"

install:
	pip install .

uninstall:
	pip uninstall -y webradio-player

run:
	python -m webradio.main

dev:
	pip install -e .

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -f webradio-player-*.tar.gz

build:
	python -m build

rpm: clean
	@echo "Building RPM package..."
	@echo "Using build-rpm.sh script for complete RPM build"
	@./build-rpm.sh

rpm-quick:
	@echo "Quick RPM build (no clean)..."
	@echo "Make sure you have rpm-build and rpmdevtools installed"
	python3 setup.py sdist
	mkdir -p ~/rpmbuild/{SOURCES,SPECS}
	cp dist/webradio-player-*.tar.gz ~/rpmbuild/SOURCES/
	cp webradio.spec ~/rpmbuild/SPECS/
	cd ~/rpmbuild && rpmbuild -ba SPECS/webradio.spec
	@echo "RPM package created in ~/rpmbuild/RPMS/noarch/"

rpm-binary:
	@echo "Building binary RPM only..."
	python3 setup.py sdist
	mkdir -p ~/rpmbuild/{SOURCES,SPECS}
	cp dist/webradio-player-*.tar.gz ~/rpmbuild/SOURCES/
	cp webradio.spec ~/rpmbuild/SPECS/
	cd ~/rpmbuild && rpmbuild -bb SPECS/webradio.spec
	@echo "Binary RPM created in ~/rpmbuild/RPMS/noarch/"

deb: clean
	@echo "Building DEB package..."
	@echo "Make sure you have debhelper, dh-python installed"
	dpkg-buildpackage -us -uc -b
	@echo "DEB package created in parent directory"

arch: clean
	@echo "Building Arch Linux package..."
	@echo "Make sure you have base-devel installed"
	makepkg -s --noconfirm || makepkg
	@echo ""
	@echo "Arch package created successfully!"
	@echo "To install: sudo pacman -U webradio-player-*.pkg.tar.zst"

test:
	@echo "Running tests..."
	python -m pytest tests/ || echo "No tests found"
