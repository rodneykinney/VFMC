.PHONY: clean build install all dist test icons pypi-build pypi-upload

VERSION=$(shell toml2json pyproject.toml | jq '.project.version' --raw-output)
show-version:
	echo $(VERSION)

all: build

icons:
	@echo "Generating icon files from resources/vfmc-icon.png..."
	# Create macOS icns file
	rm -rf IconSet.iconset
	mkdir -p IconSet.iconset
	sips -z 16 16     resources/vfmc-icon.png --out IconSet.iconset/icon_16x16.png
	sips -z 32 32     resources/vfmc-icon.png --out IconSet.iconset/icon_16x16@2x.png
	sips -z 32 32     resources/vfmc-icon.png --out IconSet.iconset/icon_32x32.png
	sips -z 64 64     resources/vfmc-icon.png --out IconSet.iconset/icon_32x32@2x.png
	sips -z 128 128   resources/vfmc-icon.png --out IconSet.iconset/icon_128x128.png
	sips -z 256 256   resources/vfmc-icon.png --out IconSet.iconset/icon_128x128@2x.png
	sips -z 256 256   resources/vfmc-icon.png --out IconSet.iconset/icon_256x256.png
	sips -z 512 512   resources/vfmc-icon.png --out IconSet.iconset/icon_256x256@2x.png
	sips -z 512 512   resources/vfmc-icon.png --out IconSet.iconset/icon_512x512.png
	sips -z 1024 1024 resources/vfmc-icon.png --out IconSet.iconset/icon_512x512@2x.png
	iconutil -c icns IconSet.iconset -o resources/vfmc.icns
	rm -rf IconSet.iconset
	
	# Create Windows ico file
	magick convert -background transparent resources/vfmc-icon.png -define icon:auto-resize=16,32,48,64,128,256 resources/vfmc.ico
	
	@echo "Icon files created:"
	@echo "  - resources/vfmc.icns (macOS)"
	@echo "  - resources/vfmc.ico (Windows)"
	@echo "  - resources/vfmc-icon.png (Linux)"

clean:
	rm -rf dist-mac-intel/ dist-mac-arm/ build/
	cd rust-src && cargo clean

.venv:
	python3.9 -m venv .venv
	. .venv/bin/activate && \
	pip install ".[dev]"

.venv-rust:
	. .venv/bin/activate && \
	cd rust-src && maturin develop --release --target aarch64-apple-darwin

.venv-x86:
	arch -x86_64 /usr/bin/python3 -m venv .venv-x86
	. .venv-x86/bin/activate && \
	arch -x86_64 pip install ".[dev]"

.venv-x86-rust: .venv-x86
	. .venv-x86/bin/activate && \
	cd rust-src && RUSTFLAGS="-C target-feature=+avx2" arch -x86_64 maturin develop --release --target x86_64-apple-darwin

dist-macos-arm: .venv-rust
	rm -rf dist/macos-arm
	. .venv/bin/activate && \
	pyinstaller macos-arm.spec
	cd dist/macos-arm && \
	cp ../../resource/VFMC-Readme.txt . && \
	zip -q VFMC-v$(VERSION)-Mac-ARM.zip -r VFMC-Readme.txt vfmc.app

dist-macos-x86: .venv-x86-rust
	rm -rf dist/macos-x86
	. .venv-x86/bin/activate && \
	arch -x86_64 pyinstaller macos-x86.spec
	cd dist/macos-x86 && \
	cp ../../resources/VFMC-Readme.txt . && \
	zip -q VFMC-v$(VERSION)-Mac-X86.zip -r VFMC-Readme.txt vfmc.app

dist-mac: dist-macos-arm dist-macos-x86

wheels: .venv .venv-x86
	# Build ARM wheel
	. .venv/bin/activate && cd rust-src && \
	maturin build --release --target aarch64-apple-darwin --strip

	# Build x86 wheel
	. .venv-x86/bin/activate && cd rust-src && \
	RUSTFLAGS="-C target-feature=+avx2" arch -x86_64 maturin build --release --target x86_64-apple-darwin --strip


dist/pypi:
	# Build wheels for both architectures
	rm -rf dist/pypi
	mkdir -p dist/pypi
	
	# Copy wheels to dist/pypi
	cp rust-src/target/wheels/*.whl dist/pypi/
	
	# Build the Python package
	. .venv/bin/activate && \
	python -m build --wheel --sdist

	# Copy Python packages to dist/pypi
	mv dist/*.whl dist/*.tar.gz dist/pypi/

pypi-build: dist/pypi

pypi-upload: pypi-build
	@echo "Uploading to PyPI..."
	. .venv/bin/activate && \
	pip install twine && \
	twine upload dist/pypi/*
	@echo "Upload complete! Version $(VERSION) is now available on PyPI."