# -*- mode: python ; coding: utf-8 -*-

import site
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Add "src" to Python path for correct imports and collection
#sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

vfmc_datas = []
vfmc_binaries = []
vfmc_hiddenimports = []

# Collect all modules and data for pyquaternion
# pyquaternion_datas, pyquaternion_binaries, pyquaternion_hiddenimports = collect_all('pyquaternion')
# vfmc_datas.extend(pyquaternion_datas)
# vfmc_binaries.extend(pyquaternion_binaries)
# vfmc_hiddenimports.extend(pyquaternion_hiddenimports)

# Collect all modules and data for PyOpenGL
pyopengl_datas, pyopengl_binaries, pyopengl_hiddenimports = collect_all('PyOpenGL')
vfmc_datas.extend(pyopengl_datas)
vfmc_binaries.extend(pyopengl_binaries)
vfmc_hiddenimports.extend(pyopengl_hiddenimports)

# Collect all vfmc modules
vfmc_hiddenimports.extend(collect_submodules('vfmc'))

a = Analysis(
    ['launcher.py'],  # Use launcher.py as the entry point
    pathex=['src'],
    binaries=[
        ('rust-src/target/aarch64-apple-darwin/release/libvfmc_core.dylib', 'vfmc_core'),
        *vfmc_binaries
    ],
    datas=[
        ('src/vfmc/*.py', 'vfmc'),
        ('src/vfmc/help.html', 'vfmc'),
        *vfmc_datas
    ],
    hiddenimports=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 
        'PyQt5.sip', 'PyQt5.QtOpenGL', 'PyOpenGL', 'OpenGL', 'pyquaternion',
        'vfmc', 'vfmc_core',
        *vfmc_hiddenimports
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='vfmc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Should be true for Mac apps
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='vfmc',
)
app = BUNDLE(
    coll,
    name='vfmc.app',
    icon=None,
    bundle_identifier='com.rodneykinney.vfmc',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleDisplayName': 'VFMC',
        'CFBundleDocumentTypes': [],  # Add document types if needed
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'LSRequiresCarbon': False,
        'LSEnvironment': {
            'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        },
        'LSBackgroundOnly': False,
        'LSUIElement': False,  # Set to True for menubar-only apps with no dock icon
    },
)
