from __future__ import annotations

import argparse
import queue
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


RAW_DATASET_DIR = Path("data/wakeword/raw")
DEFAULT_SAMPLE_RATE = 16000


def record_clip(
    output_path: Path,
    sample_rate: int,
    max_duration_sec: float,
    silence_threshold: int,
    silence_duration_sec: float,
    start_timeout_sec: float,
) -> None:
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    frames: list[np.ndarray] = []

    def callback(indata, frames_count, time_info, status) -> None:
        if status:
            print(f"[record-dataset] audio status: {status}")
        audio_queue.put(indata.copy())

    started_at = time.time()
    speech_started_at = None
    silence_started_at = None

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=1024,
        callback=callback,
    ):
        while True:
            chunk = audio_queue.get()
            amplitude = int(np.abs(chunk).mean())

            if speech_started_at is None:
                if amplitude >= silence_threshold:
                    speech_started_at = time.time()
                    frames.append(chunk)
                    print("[record-dataset] speech detected")
                elif time.time() - started_at >= start_timeout_sec:
                    raise TimeoutError("Speech was not detected before timeout")
                continue

            frames.append(chunk)

            if amplitude < silence_threshold:
                if silence_started_at is None:
                    silence_started_at = time.time()
                elif time.time() - silence_started_at >= silence_duration_sec:
                    break
            else:
                silence_started_at = None

            if time.time() - started_at >= max_duration_sec:
                break

    if not frames:
        raise RuntimeError("No audio frames were captured")

    audio = np.concatenate(frames, axis=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write(output_path, sample_rate, audio)


def build_output_dir(label: str) -> Path:
    if label not in {"positive", "negative"}:
        raise ValueError("Label must be 'positive' or 'negative'")
    return RAW_DATASET_DIR / f"intel_{label}"


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
    parser.add_argument("--max-duration-sec", type=float, default=2.0)
    parser.add_argument("--silence-threshold", type=int, default=450)
    parser.add_argument("--silence-duration-sec", type=float, default=0.6)
    parser.add_argument("--start-timeout-sec", type=float, default=4.0)
    parser.add_argument(
        "--prefix",
        default="sample",
        help="Filename prefix inside the target raw dataset directory",
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

    for index in range(1, args.count + 1):
        output_path = output_dir / f"{args.prefix}_{index:03d}.wav"
        input(f"\nPress Enter to record clip {index}/{args.count}...")
        print("Recording...")
        try:
            record_clip(
                output_path=output_path,
                sample_rate=args.sample_rate,
                max_duration_sec=args.max_duration_sec,
                silence_threshold=args.silence_threshold,
                silence_duration_sec=args.silence_duration_sec,
                start_timeout_sec=args.start_timeout_sec,
            )
        except Exception as exc:
            print(f"Failed to record clip {index}: {exc}")
            continue
        print(f"Saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
