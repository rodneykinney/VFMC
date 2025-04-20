# -*- mode: python ; coding: utf-8 -*-
import os
import PyInstaller.config
from PyInstaller.utils.hooks import collect_data_files

PyInstaller.config.CONF['distpath'] = "dist/win-x86"

a = Analysis(
    ['src/vfmc/app.py'],
    pathex=['src'],
    datas=[
        ('src/vfmc/help.html', '.'),
    ],
    binaries=[],
    hiddenimports=[
        'vfmc_core',
        'PyQt5.QtOpenGL',
        'PyQt5.Qt5',
        'sip',
        'PyQt5.sip',
        'OpenGL.GL',
        'OpenGL.GLU',
        'OpenGL.GLUT',
        'OpenGL.platform',
        'OpenGL.platform.win32',
        'OpenGL.WGL',
        'OpenGL.arrays',
        'OpenGL.arrays.ctypesarrays',
        'OpenGL.arrays.numpymodule',
        'OpenGL.arrays.lists',
        'OpenGL.arrays.numbers',
        'OpenGL.arrays.strings',
        'OpenGL.GL.VERSION.GL_1_1',
        'OpenGL.GL.VERSION.GL_1_2',
        'OpenGL.GL.VERSION.GL_1_3',
        'OpenGL.GL.VERSION.GL_1_4',
        'OpenGL.GL.VERSION.GL_1_5',
        'OpenGL.GL.VERSION.GL_2_0',
        'OpenGL.GL.VERSION.GL_2_1',
        'OpenGL.GL.VERSION.GL_3_0',
        'OpenGL.GLU.EXT.object_space_tess',
        'OpenGL.GLU.EXT.nurbs_tessellator',
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
