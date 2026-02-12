# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect dynamic libraries for llama_cpp
binaries = []
datas = [
    ('assets', 'assets'),
    ('vendor', 'vendor'),
]

# Collect all llama_cpp resources to be safe
tmp_ret = collect_all('llama_cpp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports = tmp_ret[2]

# Collect spacy model data
tmp_spacy = collect_all('spacy')
datas += tmp_spacy[0]; binaries += tmp_spacy[1]; hiddenimports += tmp_spacy[2]

# Explicitly collect en_core_web_sm if installed as a package
try:
    import en_core_web_sm
    tmp_en = collect_all('en_core_web_sm')
    datas += tmp_en[0]; binaries += tmp_en[1]; hiddenimports += tmp_en[2]
except ImportError:
    pass

hiddenimports += ['spacy', 'thinc', 'srsly', 'cymem', 'preshed', 'blis', 'wasabi', 'murmurhash', 'pydantic']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pandas', 'matplotlib', 'notebook', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DocuMindAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico'
)
