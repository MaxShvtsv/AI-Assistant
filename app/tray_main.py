from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from main import COMMAND_START_CUE_PATH, PLAY_STARTUP_CUE, RUNTIME_ROOT, create_listener
from voice.sound_cues import play_audio_cue


class IntelTrayApp:
    def __init__(self) -> None:
        self.listener = None
        self.listener_thread: Optional[threading.Thread] = None
        self.icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()
        self._status = "Stopped"

    def run(self) -> None:
        self.icon = pystray.Icon(
            "Intel",
            icon=self._build_icon(),
            title="Intel Assistant",
            menu=pystray.Menu(
                pystray.MenuItem(lambda item: f"Status: {self._status}", lambda icon, item: None, enabled=False),
                pystray.MenuItem("Start", self._on_start),
                pystray.MenuItem("Stop", self._on_stop),
                pystray.MenuItem("Open Folder", self._on_open_folder),
                pystray.MenuItem("Exit", self._on_exit),
            ),
        )

        self.icon.run(setup=self._on_setup)

    def _on_setup(self, icon: pystray.Icon) -> None:
        self.icon = icon
        try:
            icon.visible = True
        except Exception:
            pass
        if PLAY_STARTUP_CUE:
            play_audio_cue(str(COMMAND_START_CUE_PATH), wait=False)
        thread = threading.Thread(target=self._start_listener_and_refresh, args=(icon,), daemon=True)
        thread.start()

    def _on_start(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._start_listener()
        icon.update_menu()

    def _on_stop(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._stop_listener()
        icon.update_menu()

    def _on_open_folder(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        os.startfile(str(RUNTIME_ROOT))

    def _on_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._stop_listener()
        icon.stop()

    def _start_listener(self) -> None:
        with self._lock:
            if self.listener_thread and self.listener_thread.is_alive():
                self._status = "Running"
                return

            self.listener = create_listener()
            self.listener_thread = threading.Thread(target=self._run_listener, daemon=True)
            self.listener_thread.start()
            self._status = "Running"

    def _start_listener_and_refresh(self, icon: pystray.Icon) -> None:
        self._start_listener()
        icon.update_menu()

    def _run_listener(self) -> None:
        assert self.listener is not None
        try:
            self.listener.start()
        finally:
            self._status = "Stopped"

    def _stop_listener(self) -> None:
        with self._lock:
            if self.listener is not None:
                self.listener.stop()
            self.listener = None
            self._status = "Stopped"

    @staticmethod
    def _build_icon() -> Image.Image:
        image = Image.new("RGBA", (64, 64), (20, 20, 24, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(34, 197, 94, 255))
        draw.rounded_rectangle((27, 14, 37, 50), radius=4, fill=(255, 255, 255, 255))
        draw.rounded_rectangle((21, 14, 43, 20), radius=3, fill=(255, 255, 255, 255))
        draw.rounded_rectangle((21, 44, 43, 50), radius=3, fill=(255, 255, 255, 255))
        return image


def main() -> None:
    IntelTrayApp().run()


if __name__ == "__main__":
    main()
