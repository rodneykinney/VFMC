.PHONY: clean build install all dist test

VERSION=$(shell toml2json pyproject.toml | jq '.project.version' --raw-output)
show-version:
	echo $(VERSION)

all: build

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