from __future__ import annotations

import argparse
import re
import queue
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


RAW_DATASET_DIR = Path("data/wakeword/raw")
DEFAULT_SAMPLE_RATE = 16000
INDEX_PATTERN_TEMPLATE = r"^{prefix}_(\d+)\.wav$"


def record_clip(
    output_path: Path,
    sample_rate: int,
    max_duration_sec: float,
) -> None:
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    frames: list[np.ndarray] = []
    stop_recording = threading.Event()

    def callback(indata, frames_count, time_info, status) -> None:
        if status:
            print(f"[record-dataset] audio status: {status}")
        audio_queue.put(indata.copy())

    def wait_for_stop() -> None:
        input("[record-dataset] Press Enter again to stop recording...")
        stop_recording.set()

    started_at = time.time()
    stop_thread = threading.Thread(target=wait_for_stop, daemon=True)

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=1024,
        callback=callback,
    ):
        stop_thread.start()
        while True:
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                if stop_recording.is_set():
                    break
                if time.time() - started_at >= max_duration_sec:
                    print("[record-dataset] max duration reached, stopping recording")
                    break
                continue

            frames.append(chunk)
            if stop_recording.is_set():
                break
            if time.time() - started_at >= max_duration_sec:
                print("[record-dataset] max duration reached, stopping recording")
                break

    if not frames:
        raise RuntimeError("No audio frames were captured")

    audio = np.concatenate(frames, axis=0)
    audio = normalize_audio(audio)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write(output_path, sample_rate, audio)


def normalize_audio(audio: np.ndarray, target_peak: int = 20000) -> np.ndarray:
    samples = np.asarray(audio)
    if samples.dtype != np.int16:
        samples = samples.astype(np.int16)

    if samples.size == 0:
        return samples

    centered = samples.astype(np.float32)
    centered -= centered.mean(axis=0, keepdims=True)

    peak = float(np.max(np.abs(centered)))
    if peak < 1.0:
        return centered.astype(np.int16)

    scale = min(target_peak / peak, 4.0)
    normalized = np.clip(centered * scale, -32768, 32767)
    return normalized.astype(np.int16)


def build_output_dir(label: str) -> Path:
    if label not in {"positive", "negative"}:
        raise ValueError("Label must be 'positive' or 'negative'")
    return RAW_DATASET_DIR / f"intel_{label}"


def get_next_index(output_dir: Path, prefix: str) -> int:
    pattern = re.compile(INDEX_PATTERN_TEMPLATE.format(prefix=re.escape(prefix)))
    max_index = 0

    for wav_path in output_dir.glob(f"{prefix}_*.wav"):
        match = pattern.match(wav_path.name)
        if not match:
            continue
        max_index = max(max_index, int(match.group(1)))

    return max_index + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record wakeword dataset clips for the phrase 'Intel'."
    )
    parser.add_argument(
        "--label",
        choices=["positive", "negative"],
        required=True,
        help="positive = say only the wakeword, negative = say anything except the wakeword",
    )
    parser.add_argument("--count", type=int, default=20, help="Number of clips to record")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--max-duration-sec", type=float, default=4.0)
    parser.add_argument(
        "--prefix",
        default="sample",
        help="Filename prefix inside the target raw dataset directory",
    )
    parser.add_argument(
        "--timestamp-names",
        action="store_true",
        help="Add a millisecond timestamp suffix to filenames for extra safety",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = build_output_dir(args.label)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory: {output_dir.resolve()}")
    print(f"Recording {args.count} clips for label='{args.label}'")
    if args.label == "positive":
        print("For every clip say only the wakeword: Intel")
    else:
        print("For every clip say normal speech without the word Intel")

    next_index = get_next_index(output_dir, args.prefix)
    print(f"Starting from clip index: {next_index:03d}")

    for clip_number in range(args.count):
        file_index = next_index + clip_number
        if args.timestamp_names:
            timestamp = int(time.time() * 1000)
            filename = f"{args.prefix}_{file_index:03d}_{timestamp}.wav"
        else:
            filename = f"{args.prefix}_{file_index:03d}.wav"
        output_path = output_dir / filename

        input(f"\nPress Enter to start clip {clip_number + 1}/{args.count}...")
        print("Recording...")
        try:
            record_clip(
                output_path=output_path,
                sample_rate=args.sample_rate,
                max_duration_sec=args.max_duration_sec,
            )
        except Exception as exc:
            print(f"Failed to record clip {clip_number + 1}: {exc}")
            continue
        print(f"Saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
