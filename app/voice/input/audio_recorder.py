from __future__ import annotations

import queue
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


def record_command_until_silence(
    output_path: str = "command.wav",
    sample_rate: int = 16000,
    silence_threshold: int = 400,
    silence_duration_sec: float = 1.0,
    max_duration_sec: float = 10.0,
) -> str:
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    frames: list[np.ndarray] = []

    def callback(indata, frames_count, time_info, status) -> None:
        if status:
            print(f"[record] audio status: {status}")
        audio_queue.put(indata.copy())

    silence_started_at = None
    started_at = time.time()

    print("[record] listening for command...")

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        callback=callback,
    ):
        while True:
            chunk = audio_queue.get()
            frames.append(chunk)

            amplitude = int(np.abs(chunk).mean())

            if amplitude < silence_threshold:
                if silence_started_at is None:
                    silence_started_at = time.time()
                elif time.time() - silence_started_at >= silence_duration_sec:
                    break
            else:
                silence_started_at = None

            if time.time() - started_at >= max_duration_sec:
                break

    audio = np.concatenate(frames, axis=0)
    output = Path(output_path)
    write(output, sample_rate, audio)
    print(f"[record] saved command audio to: {output.resolve()}")
    return str(output.resolve())