# -*- mode: python ; coding: utf-8 -*-
# CP2112 Battery Analyzer — PyInstaller build spec (Windows standalone)
#
# Prerequisites:
#   1. pip install -r requirements.txt pyinstaller
#   2. Place SLABHIDtoSMBus.dll and SLABHIDDevice.dll in python/vendor/
#
# Usage (from python/):
#   pyinstaller packaging/cp2112_analyzer.spec --noconfirm
#
# Output:
#   dist/CP2112-Battery-Analyzer.exe

import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
PYTHON_DIR = SPEC_DIR.parent
VENDOR_DIR = PYTHON_DIR / 'vendor'
PYREADER_DIR = PYTHON_DIR / 'pyreader'

APP_NAME = 'CP2112-Battery-Analyzer'
SCRIPT = str(PYTHON_DIR / 'run_app.py')
ICON_ICO = str(PYREADER_DIR / 'icon.ico')
VERSION = '1.1.0'

REQUIRED_DLLS = ('SLABHIDtoSMBus.dll', 'SLABHIDDevice.dll')

if sys.platform != 'win32':
    raise SystemExit('This build spec targets Windows only (CP2112 hardware requires SLAB DLLs).')

missing = [name for name in REQUIRED_DLLS if not (VENDOR_DIR / name).exists()]
if missing:
    raise SystemExit(
        'Missing Silicon Labs DLLs in python/vendor/:\n  '
        + '\n  '.join(missing)
        + '\n\nDownload the CP2112 SDK from Silicon Labs and copy both DLLs to python/vendor/.'
    )

datas = [
    (str(PYREADER_DIR / 'icon.ico'), 'pyreader'),
    (str(PYREADER_DIR / 'icon.png'), 'pyreader'),
]

binaries = [(str(VENDOR_DIR / name), '.') for name in REQUIRED_DLLS]

a = Analysis(
    [SCRIPT],
    pathex=[str(PYTHON_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(SPEC_DIR / 'runtime_hook.py')],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_ICO,
    version_file=None,
)
