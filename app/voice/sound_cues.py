from __future__ import annotations

import threading
import winsound
from pathlib import Path


def play_audio_cue(file_path: str | Path | None, wait: bool = False) -> None:
    if not file_path:
        return

    path = Path(file_path)
    if not path.exists():
        print(f"[sound] cue file not found: {path}")
        return

    flags = winsound.SND_FILENAME
    if not wait:
        flags |= winsound.SND_ASYNC

    try:
        winsound.PlaySound(str(path.resolve()), flags)
    except RuntimeError as exc:
        print(f"[sound] failed to play cue '{path.name}': {exc}")


def stop_audio_cue() -> None:
    thread = threading.Thread(target=winsound.PlaySound, args=(None, 0), daemon=True)
    thread.start()
