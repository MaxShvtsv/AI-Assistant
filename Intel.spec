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


a = Analysis(
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
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Intel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Intel",
)
