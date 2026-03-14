from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run() -> int:
    parser = argparse.ArgumentParser(description="Build portable Intel app with PyInstaller.")
    parser.add_argument("--clean", action="store_true", help="Remove build/ and dist/ before building.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    if args.clean:
        for folder_name in ("build", "dist"):
            folder = project_root / folder_name
            if folder.exists():
                shutil.rmtree(folder)

    _run_command([sys.executable, "-m", "pip", "install", "-r", "requirements-build.txt"], project_root)
    _run_command([sys.executable, "-m", "PyInstaller", "--noconfirm", "Intel.spec"], project_root)

    dist_root = project_root / "dist" / "Intel"
    (dist_root / "data" / "input").mkdir(parents=True, exist_ok=True)
    (dist_root / "logs").mkdir(parents=True, exist_ok=True)
    _copy_runtime_assets(project_root, dist_root)

    env_path = dist_root / ".env"
    if not env_path.exists():
        shutil.copy2(project_root / ".env.example", env_path)

    print()
    print("Portable build is ready:")
    print(f"  {dist_root}")
    print()
    print("Next steps:")
    print(f"  1. Edit {env_path}")
    print("  2. Make sure Ollama + gemma3 are installed on the target machine")
    print(f"  3. Run {dist_root / 'Intel.exe'}")

    return 0


def _run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def _copy_runtime_assets(project_root: Path, dist_root: Path) -> None:
    runtime_dirs = [
        (project_root / "data" / "sounds", dist_root / "data" / "sounds"),
        (project_root / "data" / "wakeword" / "models", dist_root / "data" / "wakeword" / "models"),
    ]

    for source_dir, target_dir in runtime_dirs:
        if not source_dir.exists():
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, target_dir / item.name)


if __name__ == "__main__":
    raise SystemExit(run())
