# -*- mode: python ; coding: utf-8 -*-
import PyInstaller.config
PyInstaller.config.CONF['distpath'] = "dist/macos-arm"

a = Analysis(
    ['src/vfmc/app.py'],
    pathex=['src'],
    datas=[
        ('src/vfmc/help.html', '.'),
    ],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VFMC',
    console=False,
    argv_emulation=True,  # Should be true for Mac apps
    target_arch='arm64',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='VFMC',
)
app = BUNDLE(
    coll,
    name='VFMC.app',
    icon=None,
    bundle_identifier='com.rodneykinney.vfmc',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleDisplayName': 'VFMC',
        'CFBundleName': 'VFMC',
        'NSPrincipalClass': 'NSApplication',
    },
)
