# -*- mode: python ; coding: utf-8 -*-
import PyInstaller.config
PyInstaller.config.CONF['distpath'] = "dist/win-x86"

a = Analysis(
    ['src/vfmc/app.py'],
    pathex=['src'],
    datas=[
        ('src/vfmc/help.html', '.'),
    ],
    hiddenimports=[
        'vfmc_core',
        'OpenGL.platform.win32',
        'OpenGL.arrays.ctypesarrays',
        'OpenGL.arrays.numpymodule',
        'OpenGL.arrays.lists',
        'OpenGL.arrays.numbers',
        'OpenGL.arrays.strings',
    ],
    binaries=[],
    collect_submodules=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL'],
)

# Fix for PyQt5 plugins on Windows
from PyInstaller.utils.hooks import collect_data_files
qt_plugins = collect_data_files('PyQt5', include_py_files=False, subdir='plugins')
a.datas += qt_plugins

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VFMC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Change to True to see console output for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can specify a path to a .ico file here
)