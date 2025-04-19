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
        'OpenGL.EGL',  # EGL specific module
        'OpenGL.raw.EGL',  # Raw EGL bindings
        'OpenGL.raw.EGL.EXT',  # EGL extensions
        'PyQt5.QtOpenGL',
        'PyQt5.QtWidgets',
        'PyQt5.Qt3DCore',
        'PyQt5.Qt3DRender',
    ],
    binaries=[],
    collect_submodules=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtOpenGL',
        'PyQt5.Qt3DCore',
        'PyQt5.Qt3DRender',
        'PyQt5.QtNetwork'
    ]
)

# Fix for PyQt5 plugins on Windows
from PyInstaller.utils.hooks import collect_data_files
qt_plugins = collect_data_files('PyQt5', include_py_files=False, subdir='plugins')
qt_platforms = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'platforms'))
qt_egl = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'egldeviceintegrations'))
qt_xcbgl = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'xcbglintegrations'))

a.datas += qt_plugins
a.datas += qt_platforms
a.datas += qt_egl
a.datas += qt_xcbgl

import os
from PyQt5.QtCore import QLibraryInfo
qt_bin_path = QLibraryInfo.location(QLibraryInfo.BinariesPath)
binaries = []
for dll in ['libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_47.dll']:
    dll_path = os.path.join(qt_bin_path, dll)
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))
a.binaries += binaries

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