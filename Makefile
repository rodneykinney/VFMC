.PHONY: clean build install all dist test icons pypi-build pypi-upload

code-check: code-format-check code-lint

code-format-check:
	black --check src

code-lint:
	flake8 src

code-format:
	black src

print-version:
	@python -c "from importlib.metadata import version; print(version('vfmc'))"

version=
set-version:
	[[ "$(version)" != "" ]] || exit 1
	cat pyproject.toml | sed -e 's/^version *= *"[^"]*"/version = "$(version)"/g' | sed -e 's/"vfmc_core==.*"/"vfmc_core==$(version)"/' > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml
	cat rust-src/Cargo.toml | sed -e 's/^version *= *"[^"]*"/version = "$(version)"/g' > rust-src/Cargo.toml.tmp && mv rust-src/Cargo.toml.tmp rust-src/Cargo.toml
	cat rust-src/pyproject.toml | sed -e 's/^version *= *"[^"]*"/version = "$(version)"/g' > rust-src/pyproject.toml.tmp && mv rust-src/pyproject.toml.tmp rust-src/pyproject.toml

current_version=$(shell grep '^version' pyproject.toml | cut -d\" -f 2)
push-version:
	git tag v$(current_version)
	git push origin v$(current_version)

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
	cd rust-src && cargo clean

.venv:
	python3.9 -m venv .venv
	. .venv/bin/activate && \
	pip install ".[dev]"

dev: .venv
	. .venv/bin/activate && \
	cd rust-src && maturin develop --release --target aarch64-apple-darwin