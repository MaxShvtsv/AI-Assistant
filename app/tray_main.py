from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from main import RUNTIME_ROOT, create_listener


class IntelTrayApp:
    def __init__(self) -> None:
        self.listener = None
        self.listener_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._status = "Stopped"

    def run(self) -> None:
        icon = pystray.Icon(
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

        self._start_listener()
        icon.run()

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
        draw.rectangle((29, 16, 35, 48), fill=(255, 255, 255, 255))
        draw.rectangle((20, 16, 44, 22), fill=(255, 255, 255, 255))
        return image


def main() -> None:
    IntelTrayApp().run()


if __name__ == "__main__":
    main()
