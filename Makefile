.PHONY: clean build install all dist test

all: build

clean:
	rm -rf target/ dist/ build/ *.egg-info/
	cd rust-src && cargo clean

build:
	maturin build --release

install:
	pip install -e .

# Create a standalone executable package using PyInstaller
dist:
	# Build Rust binaries first
	maturin build --release
	# Install locally to get the compiled extensions
	pip install -e .
	# Use PyInstaller to create standalone executable
	pyinstaller --clean --noconfirm \
		--add-data "src/vfmc/help.html:vfmc" \
		--add-binary "$(shell pip show vfmc | grep Location | cut -d ' ' -f 2)/vfmc_core.*:vfmc" \
		--name vfmc \
		--onefile \
		src/vfmc/app.py
	@echo "Standalone executable created at dist/vfmc"

install-macos: clean
	# Build for macOS with universal2 (x86_64 + arm64)
	cd rust-src && maturin build --release --target aarch64-apple-darwin
	# Install locally
	pip install -e .

PACKAGE_DIR=$(shell pip show vfmc | grep Location | cut -d ' ' -f 2)
# Create platform-specific distributions
dist-macos: # install-macos
	# Create standalone executable
	pyinstaller macos-arm.spec
	@echo "macOS executable created at dist/vfmc-macos"

dist-linux: clean
	# Build for Linux x86_64
	cd rust-src && maturin build --release --target x86_64-unknown-linux-gnu
	# Install locally
	pip install -e .
	# Create standalone executable
	pyinstaller --clean --noconfirm \
		--add-data "src/vfmc/help.html:vfmc" \
		--add-binary "$(shell pip show vfmc | grep Location | cut -d ' ' -f 2)/vfmc/vfmc_core.*:vfmc" \
		--name vfmc-linux \
		--onefile \
		src/vfmc/app.py
	@echo "Linux executable created at dist/vfmc-linux"

dist-windows: clean
	# Build for Windows x86_64
	cd rust-src && maturin build --release --target x86_64-pc-windows-msvc
	# Install locally
	pip install -e .
	# Create standalone executable
	pyinstaller --clean --noconfirm \
		--add-data "src/vfmc/help.html;vfmc" \
		--add-binary "$(shell pip show vfmc | grep Location | cut -d ' ' -f 2)/vfmc/vfmc_core.*;vfmc" \
		--name vfmc-windows \
		--onefile \
		src/vfmc/app.py
	@echo "Windows executable created at dist/vfmc-windows"

dist-all: dist-macos dist-linux dist-windows
	@echo "All platform-specific executables created in dist/"

# Run tests
test:
	pytest
	cd rust-src/cubelib/cli && cargo test

# Development setup
dev-setup:
	pip install -e ".[dev]"
	pip install pyinstaller
	maturin develop