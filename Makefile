.PHONY: clean build install all dist test icons

VERSION=$(shell toml2json pyproject.toml | jq '.project.version' --raw-output)
show-version:
	echo $(VERSION)

all: build

icons:
	@echo "Generating icon files from dist/vfmc-icon.png..."
	# Create macOS icns file
	mkdir -p IconSet.iconset
	sips -z 16 16     dist/vfmc-icon.png --out IconSet.iconset/icon_16x16.png
	sips -z 32 32     dist/vfmc-icon.png --out IconSet.iconset/icon_16x16@2x.png
	sips -z 32 32     dist/vfmc-icon.png --out IconSet.iconset/icon_32x32.png
	sips -z 64 64     dist/vfmc-icon.png --out IconSet.iconset/icon_32x32@2x.png
	sips -z 128 128   dist/vfmc-icon.png --out IconSet.iconset/icon_128x128.png
	sips -z 256 256   dist/vfmc-icon.png --out IconSet.iconset/icon_128x128@2x.png
	sips -z 256 256   dist/vfmc-icon.png --out IconSet.iconset/icon_256x256.png
	sips -z 512 512   dist/vfmc-icon.png --out IconSet.iconset/icon_256x256@2x.png
	sips -z 512 512   dist/vfmc-icon.png --out IconSet.iconset/icon_512x512.png
	sips -z 1024 1024 dist/vfmc-icon.png --out IconSet.iconset/icon_512x512@2x.png
	iconutil -c icns IconSet.iconset -o dist/vfmc.icns
	rm -rf IconSet.iconset
	
	# Create Windows ico file
	magick convert -background transparent dist/vfmc-icon.png -define icon:auto-resize=16,32,48,64,128,256 dist/vfmc.ico
	
	@echo "Icon files created:"
	@echo "  - dist/vfmc.icns (macOS)"
	@echo "  - dist/vfmc.ico (Windows)"
	@echo "  - dist/vfmc-icon.png (Linux)"

clean:
	rm -rf dist-mac-intel/ dist-mac-arm/ build/
	cd rust-src && cargo clean

venv:
	if [ ! -d ".venv" ]; then \
	    python3.9 -m venv .venv; \
	fi
	. .venv/bin/activate && \
	pip install . && \
	cd rust-src && maturin develop --release --target aarch64-apple-darwin

venv-x86:
	if [ ! -d ".venv-x86" ]; then \
		arch -x86_64 /usr/bin/python3 -m venv .venv-x86; \
	fi
	. .venv-x86/bin/activate && \
	arch -x86_64 pip install . && \
	cd rust-src && RUSTFLAGS="-C target-feature=+avx2" arch -x86_64 maturin develop --release --target x86_64-apple-darwin

dist-macos-arm:
	rm -rf dist/macos-arm
	. .venv/bin/activate && \
	pyinstaller macos-arm.spec
	cd dist/macos-arm && \
	cp ../VFMC-Readme.txt . && \
	zip -q VFMC-v$(VERSION)-Mac-ARM.zip -r VFMC-Readme.txt vfmc.app

dist-macos-x86:
	rm -rf dist/macos-x86
	. .venv-x86/bin/activate && \
	arch -x86_64 pyinstaller macos-x86.spec
	cd dist/macos-x86 && \
	cp ../VFMC-Readme.txt . && \
	zip -q VFMC-v$(VERSION)-Mac-X86.zip -r VFMC-Readme.txt vfmc.app

dist-mac: dist-macos-arm dist-macos-x86