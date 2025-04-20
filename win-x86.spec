# -*- mode: python ; coding: utf-8 -*-
import os
import PyInstaller.config
from PyInstaller.utils.hooks import collect_data_files

PyInstaller.config.CONF['distpath'] = "dist/win-x86"

# Adjust this to match your actual Python site-packages path
pyqt_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Lib', 'site-packages', 'PyQt5')
bin_path = os.path.join(pyqt_path, 'Qt5', 'bin')

# Collect Qt plugin files (e.g. qwindows.dll)
qt_plugins_path = os.path.join(pyqt_path, 'Qt5', 'plugins')
qt_plugins = collect_data_files("PyQt5", subdir="Qt5/plugins/platforms")
qt_plugins += collect_data_files("PyQt5", subdir="Qt5/plugins/imageformats")
qt_plugins += collect_data_files("PyQt5", subdir="Qt5/plugins/renderers")
print(f"qt_plugins = {qt_plugins}")

# Collect required Qt DLLs for OpenGL rendering
qt_dlls = []
for dll in ['libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_47.dll']:
    dll_path = os.path.join(bin_path, dll)
    if os.path.exists(dll_path):
        qt_dlls.append((dll_path, '.'))

print(f"qt_dlls = {qt_dlls}")

a = Analysis(
    ['src/vfmc/app.py'],
    pathex=['src'],
    datas=[
        ('src/vfmc/help.html', '.'),
    ] + qt_plugins,
    binaries=qt_dlls,
    hiddenimports=[
        'vfmc_core',
        'OpenGL.platform.win32',
        'OpenGL.arrays.ctypesarrays',
        'OpenGL.arrays.numpymodule',
        'OpenGL.arrays.lists',
        'OpenGL.arrays.numbers',
        'OpenGL.arrays.strings',
        'PyQt5.QtOpenGL',
        'PyQt5.Qt',
        'sip',
        'PyQt5.sip',
    ],
    collect_submodules=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL'],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VFMC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VFMC',
)
