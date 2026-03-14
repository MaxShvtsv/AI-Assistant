from __future__ import annotations

import queue
import threading
import time
from collections import deque
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
    cooldown_sec: float = 2.0
    min_chunk_rms: float = 150.0
    min_consecutive_detections: int = 3
    debug_log_scores: bool = False
    debug_score_threshold: float = 0.15
    detector_idle_reset_sec: float = 4.0
    instant_detection_threshold: float = 0.0
    activation_window_frames: int = 4
    activation_window_ratio: float = 0.82
    pre_roll_chunks: int = 8


class WakeWordListener:
    def __init__(
        self,
        detector,
        wakeword_name: str,
        on_wake: Callable[[Optional[np.ndarray]], None],
        config: Optional[WakeWordConfig] = None,
    ) -> None:
        self.detector = detector
        self.wakeword_name = wakeword_name
        self.on_wake = on_wake
        self.config = config or WakeWordConfig()

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stop_event = threading.Event()
        self._handling_wake = threading.Event()
        self._cooldown_until = 0.0
        self._consecutive_detections = 0
        self._last_detector_activity_at = time.time()
        self._recent_scores: deque[float] = deque(maxlen=max(1, self.config.activation_window_frames))
        self._recent_audio_chunks: deque[np.ndarray] = deque(maxlen=max(1, self.config.pre_roll_chunks))

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            print(f"[wakeword] audio status: {status}")
        if self._handling_wake.is_set():
            return
        chunk = indata.copy()
        self._recent_audio_chunks.append(chunk)
        self._audio_queue.put(chunk)

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
                chunk_rms = self._compute_chunk_rms(audio)

                # Ignore silence / very quiet noise before even asking the detector.
                if chunk_rms < self.config.min_chunk_rms:
                    self._consecutive_detections = 0
                    self._recent_scores.clear()
                    self._maybe_reset_detector_for_idle()
                    continue

                score = self._predict_score(audio)
                self._last_detector_activity_at = time.time()
                self._recent_scores.append(score)

                if self.config.debug_log_scores and score >= self.config.debug_score_threshold:
                    print(
                        f"[wakeword-debug] score={score:.3f} "
                        f"rms={chunk_rms:.1f} hits={self._consecutive_detections}"
                    )

                if score >= self.config.detection_threshold:
                    self._consecutive_detections += 1
                else:
                    self._consecutive_detections = 0
                    self._maybe_reset_detector_for_idle()

                should_trigger_now = (
                    self.config.instant_detection_threshold > 0
                    and score >= self.config.instant_detection_threshold
                )
                window_hits = sum(
                    recent_score >= self.config.detection_threshold * self.config.activation_window_ratio
                    for recent_score in self._recent_scores
                )
                has_window_trigger = window_hits >= self.config.min_consecutive_detections

                if should_trigger_now or has_window_trigger or self._consecutive_detections >= self.config.min_consecutive_detections:
                    print(
                        f"[wakeword] detected '{self.wakeword_name}' "
                        f"with score={score:.3f} rms={chunk_rms:.1f}"
                    )
                    self._cooldown_until = time.time() + self.config.cooldown_sec
                    self._handling_wake.set()
                    self._consecutive_detections = 0
                    self._recent_scores.clear()
                    pre_roll_audio = self._collect_pre_roll_audio()
                    self._reset_detector()
                    self._clear_audio_queue()

                    try:
                        self.on_wake(pre_roll_audio)
                    finally:
                        self._reset_detector()
                        self._clear_audio_queue()
                        self._handling_wake.clear()
                        self._last_detector_activity_at = time.time()
                        self._recent_scores.clear()
                        print("[wakeword] resumed listening")

    def stop(self) -> None:
        self._stop_event.set()

    def _predict_score(self, audio: np.ndarray) -> float:
        predictions = self.detector.predict(audio)

        if isinstance(predictions, dict):
            return float(predictions.get(self.wakeword_name, 0.0))

        if isinstance(predictions, (int, float)):
            return float(predictions)

        return 0.0

    def _clear_audio_queue(self) -> None:
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                return

    def _collect_pre_roll_audio(self) -> Optional[np.ndarray]:
        if not self._recent_audio_chunks:
            return None
        return np.concatenate(list(self._recent_audio_chunks), axis=0)

    def _reset_detector(self) -> None:
        reset_method = getattr(self.detector, "reset", None)
        if callable(reset_method):
            reset_method()

    def _maybe_reset_detector_for_idle(self) -> None:
        if self.config.detector_idle_reset_sec <= 0:
            return

        now = time.time()
        if now - self._last_detector_activity_at < self.config.detector_idle_reset_sec:
            return

        self._reset_detector()
        self._last_detector_activity_at = now

    @staticmethod
    def _compute_chunk_rms(audio: np.ndarray) -> float:
        samples = np.asarray(audio, dtype=np.float32)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(samples))))
