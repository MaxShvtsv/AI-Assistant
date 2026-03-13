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
    blocksize: int = 1024,
    speech_threshold: int = 600,
    silence_threshold: int = 400,
    min_speech_duration_sec: float = 0.2,
    start_timeout_sec: float = 4.0,
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
    speech_started_at = None
    started_at = time.time()

    print("[record] waiting for command...")

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=blocksize,
        callback=callback,
    ):
        while True:
            chunk = audio_queue.get()
            amplitude = int(np.abs(chunk).mean())

            if speech_started_at is None:
                if amplitude >= speech_threshold:
                    speech_started_at = time.time()
                    frames.append(chunk)
                    print("[record] speech detected, recording command...")
                elif time.time() - started_at >= start_timeout_sec:
                    raise TimeoutError("Voice command was not detected after wake word")
                continue

            frames.append(chunk)

            speech_duration = time.time() - speech_started_at
            if amplitude < silence_threshold:
                if silence_started_at is None:
                    silence_started_at = time.time()
                elif (
                    speech_duration >= min_speech_duration_sec
                    and time.time() - silence_started_at >= silence_duration_sec
                ):
                    break
            else:
                silence_started_at = None

            if time.time() - started_at >= max_duration_sec:
                break

    if not frames:
        raise RuntimeError("No audio frames were captured for the command")

    audio = np.concatenate(frames, axis=0)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, sample_rate, audio)
    print(f"[record] saved command audio to: {output.resolve()}")
    return str(output.resolve())
