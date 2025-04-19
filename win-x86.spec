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
        # Add more specific OpenGL imports
        'OpenGL.platform.egl',
        'OpenGL.raw.EGL.EGL_VERSION_1_0',
        'OpenGL.raw.EGL.EGL_VERSION_1_1',
        'OpenGL.raw.EGL.EGL_VERSION_1_2',
        'OpenGL.raw.EGL.EGL_VERSION_1_3',
        'OpenGL.raw.EGL.EGL_VERSION_1_4',
        'OpenGL.raw.EGL.EGL_VERSION_1_5',
        'OpenGL.raw.WGL',
        'PyQt5.sip',
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

# Add more Qt plugins
qt_styles = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'styles'))
qt_imageformats = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'imageformats'))
qt_iconengines = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'iconengines'))
qt_bearer = collect_data_files('PyQt5', include_py_files=False, subdir=os.path.join('plugins', 'bearer'))

a.datas += qt_plugins
a.datas += qt_platforms
a.datas += qt_egl
a.datas += qt_xcbgl
a.datas += qt_styles
a.datas += qt_imageformats
a.datas += qt_iconengines
a.datas += qt_bearer

# Import DLLs from Qt bin directory
import os
from PyQt5.QtCore import QLibraryInfo
qt_bin_path = QLibraryInfo.location(QLibraryInfo.BinariesPath)
binaries = []
# Walk through the Qt bin directory and add all DLLs
for file in os.listdir(qt_bin_path):
    if file.lower().endswith('.dll'):
        dll_path = os.path.join(qt_bin_path, file)
        # Use proper 3-tuple format: (source, dest_filename, 'BINARY')
        binaries.append((dll_path, os.path.join('.', file), 'BINARY'))
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
    console=True,  # Keep console for debugging the EGL issues
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can specify a path to a .ico file here
)