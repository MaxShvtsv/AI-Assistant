from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


@dataclass
class WakeWordConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    blocksize: int = 1280
    detection_threshold: float = 0.5


class WakeWordListener:
    def __init__(
        self,
        detector,
        wakeword_name: str,
        on_wake: Callable[[], None],
        config: Optional[WakeWordConfig] = None,
    ) -> None:
        self.detector = detector
        self.wakeword_name = wakeword_name
        self.on_wake = on_wake
        self.config = config or WakeWordConfig()

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stop_event = threading.Event()
        self._cooldown_until = 0.0

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            print(f"[wakeword] audio status: {status}")
        self._audio_queue.put(indata.copy())

    def start(self) -> None:
        self._stop_event.clear()

        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=self.config.blocksize,
            callback=self._audio_callback,
        ):
            print("[wakeword] listening...")
            while not self._stop_event.is_set():
                now = time.time()
                if now < self._cooldown_until:
                    try:
                        self._audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        pass
                    continue

                try:
                    chunk = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                audio = np.squeeze(chunk)

                # Здесь будет вызов твоего wake word detector
                score = self._predict_score(audio)

                if score >= self.config.detection_threshold:
                    print(f"[wakeword] detected '{self.wakeword_name}' with score={score:.3f}")
                    self._cooldown_until = time.time() + 2.0
                    self.on_wake()

    def stop(self) -> None:
        self._stop_event.set()

    def _predict_score(self, audio: np.ndarray) -> float:
        predictions = self.detector.predict(audio)

        if isinstance(predictions, dict):
            return float(predictions.get(self.wakeword_name, 0.0))

        return 0.0