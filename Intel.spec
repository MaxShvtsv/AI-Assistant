from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path(SPECPATH).resolve()
APP_DIR = PROJECT_ROOT / "app"

hiddenimports = (
    collect_submodules("openwakeword")
    + collect_submodules("faster_whisper")
    + collect_submodules("ctranslate2")
    + collect_submodules("av")
)

datas = collect_data_files("openwakeword")
datas += collect_data_files("faster_whisper")
datas += [
    (str(PROJECT_ROOT / "data" / "sounds"), "data/sounds"),
    (str(PROJECT_ROOT / "data" / "wakeword" / "models"), "data/wakeword/models"),
    (str(PROJECT_ROOT / ".env.example"), "."),
    (str(PROJECT_ROOT / "README.md"), "."),
]

excludes = [
    "torch",
    "tensorflow",
    "onnx_tf",
    "onnxscript",
    "tests",
    "utils",
]


console_analysis = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
console_pyz = PYZ(console_analysis.pure)

console_exe = EXE(
    console_pyz,
    console_analysis.scripts,
    [],
    exclude_binaries=True,
    name="Intel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

tray_analysis = Analysis(
    [str(APP_DIR / "tray_main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
tray_pyz = PYZ(tray_analysis.pure)

tray_exe = EXE(
    tray_pyz,
    tray_analysis.scripts,
    [],
    exclude_binaries=True,
    name="IntelTray",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    console_exe,
    tray_exe,
    console_analysis.binaries,
    console_analysis.datas,
    tray_analysis.binaries,
    tray_analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Intel",
)
