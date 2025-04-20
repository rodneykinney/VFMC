# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

# Adjust this to match your actual Python site-packages path
pyqt_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Lib', 'site-packages', 'PyQt5')

# Collect Qt plugin files (e.g. qwindows.dll)
qt_plugins = collect_data_files('PyQt5', include_py_files=False, subdir='plugins')

# Collect required Qt DLLs for OpenGL rendering
qt_dlls = []
for dll in ['libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_47.dll']:
    dll_path = os.path.join(pyqt_path, 'Qt', 'bin', dll)
    if os.path.exists(dll_path):
        qt_dlls.append((dll_path, '.'))

print(f"qt_dlls = {qt_dlls}")
# Optional: Add platform plugin manually if collect_data_files doesn't find it
# qt_plugins += [
#     (os.path.join(pyqt_path, 'Qt', 'plugins', 'platforms', 'qwindows.dll'), 'PyQt5/Qt/plugins/platforms')
# ]
print(f"qt_plugins = {qt_plugins}")

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
    ],
    collect_submodules=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL'],
)

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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
