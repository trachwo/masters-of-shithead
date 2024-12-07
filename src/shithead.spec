# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['shithead_start.py'],
    pathex=[],
    binaries=[],
    datas=[('./shithead/title.json','shithead'),\
	       ('./shithead/rules.py','shithead'),\
		   ('./shithead/face_up_table.json', 'shithead'),\
		   ('./shithead/rules_eng.json', 'shithead'),\
		   ('./shithead/rules_ger.json', 'shithead')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='shithead',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
