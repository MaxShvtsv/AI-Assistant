from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io.wavfile import read, write
from scipy.signal import resample_poly


TARGET_SAMPLE_RATE = 16000
RAW_DATASET_DIR = Path("data/wakeword/raw")
PREPARED_DATASET_DIR = Path("data/wakeword/prepared")


@dataclass(frozen=True)
class DatasetLayout:
    positive_input: Path
    negative_input: Path
    positive_train_output: Path
    positive_val_output: Path
    negative_train_output: Path
    negative_val_output: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare raw wakeword clips into 16kHz mono WAV train/val sets."
    )
    parser.add_argument(
        "--positive-dir",
        type=Path,
        default=RAW_DATASET_DIR / "intel_positive",
        help="Directory with raw WAV files containing only the wakeword Intel",
    )
    parser.add_argument(
        "--negative-dir",
        type=Path,
        default=RAW_DATASET_DIR / "intel_negative",
        help="Directory with raw WAV files that do not contain the wakeword Intel",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PREPARED_DATASET_DIR,
        help="Where the normalized train/val dataset will be written",
    )
    parser.add_argument("--validation-ratio", type=float, default=0.2)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--trim-silence", action="store_true")
    parser.add_argument("--silence-threshold", type=int, default=300)
    parser.add_argument(
        "--target-duration-sec",
        type=float,
        default=2.0,
        help="All output clips are padded or trimmed to this duration",
    )
    return parser.parse_args()


def build_layout(output_dir: Path) -> DatasetLayout:
    return DatasetLayout(
        positive_input=RAW_DATASET_DIR / "intel_positive",
        negative_input=RAW_DATASET_DIR / "intel_negative",
        positive_train_output=output_dir / "positive_train",
        positive_val_output=output_dir / "positive_val",
        negative_train_output=output_dir / "negative_train",
        negative_val_output=output_dir / "negative_val",
    )


def load_wav(path: Path) -> tuple[int, np.ndarray]:
    sample_rate, audio = read(path)

    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    if np.issubdtype(audio.dtype, np.floating):
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767.0).astype(np.int16)
    elif audio.dtype != np.int16:
        max_value = np.max(np.abs(audio)) if audio.size else 0
        if max_value == 0:
            audio = audio.astype(np.int16)
        else:
            audio = (audio.astype(np.float32) / max_value * 32767.0).astype(np.int16)

    return sample_rate, audio.astype(np.int16)


def maybe_trim_silence(audio: np.ndarray, silence_threshold: int) -> np.ndarray:
    active = np.flatnonzero(np.abs(audio) >= silence_threshold)
    if active.size == 0:
        return audio
    return audio[active[0]:active[-1] + 1]


def resample_audio(audio: np.ndarray, source_sample_rate: int, target_sample_rate: int) -> np.ndarray:
    if source_sample_rate == target_sample_rate:
        return audio.astype(np.int16)
    resampled = resample_poly(audio.astype(np.float32), target_sample_rate, source_sample_rate)
    resampled = np.clip(resampled, -32768, 32767)
    return resampled.astype(np.int16)


def fit_duration(audio: np.ndarray, target_samples: int) -> np.ndarray:
    if audio.shape[0] > target_samples:
        return audio[:target_samples]
    if audio.shape[0] < target_samples:
        padding = np.zeros(target_samples - audio.shape[0], dtype=np.int16)
        return np.concatenate([audio, padding])
    return audio


def prepare_clip(
    input_path: Path,
    output_path: Path,
    target_duration_sec: float,
    trim_silence: bool,
    silence_threshold: int,
) -> None:
    sample_rate, audio = load_wav(input_path)
    if trim_silence:
        audio = maybe_trim_silence(audio, silence_threshold)
    audio = resample_audio(audio, sample_rate, TARGET_SAMPLE_RATE)
    audio = fit_duration(audio, int(TARGET_SAMPLE_RATE * target_duration_sec))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write(output_path, TARGET_SAMPLE_RATE, audio)


def split_files(files: list[Path], validation_ratio: float, random_seed: int) -> tuple[list[Path], list[Path]]:
    shuffled = files[:]
    random.Random(random_seed).shuffle(shuffled)
    val_count = max(1, int(round(len(shuffled) * validation_ratio))) if shuffled else 0
    return shuffled[val_count:], shuffled[:val_count]


def process_group(
    files: list[Path],
    train_dir: Path,
    val_dir: Path,
    validation_ratio: float,
    random_seed: int,
    target_duration_sec: float,
    trim_silence: bool,
    silence_threshold: int,
) -> tuple[int, int]:
    train_files, val_files = split_files(files, validation_ratio, random_seed)

    for file in train_files:
        prepare_clip(
            input_path=file,
            output_path=train_dir / file.name,
            target_duration_sec=target_duration_sec,
            trim_silence=trim_silence,
            silence_threshold=silence_threshold,
        )

    for file in val_files:
        prepare_clip(
            input_path=file,
            output_path=val_dir / file.name,
            target_duration_sec=target_duration_sec,
            trim_silence=trim_silence,
            silence_threshold=silence_threshold,
        )

    return len(train_files), len(val_files)


def ensure_input_dir(path: Path, label: str) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(f"{label} directory does not exist: {path}")
    files = sorted(path.glob("*.wav"))
    if not files:
        raise FileNotFoundError(f"{label} directory is empty: {path}")
    return files


def main() -> None:
    args = parse_args()
    layout = DatasetLayout(
        positive_input=args.positive_dir,
        negative_input=args.negative_dir,
        positive_train_output=args.output_dir / "positive_train",
        positive_val_output=args.output_dir / "positive_val",
        negative_train_output=args.output_dir / "negative_train",
        negative_val_output=args.output_dir / "negative_val",
    )

    positive_files = ensure_input_dir(layout.positive_input, "Positive")
    negative_files = ensure_input_dir(layout.negative_input, "Negative")

    for directory in [
        layout.positive_train_output,
        layout.positive_val_output,
        layout.negative_train_output,
        layout.negative_val_output,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    pos_train, pos_val = process_group(
        files=positive_files,
        train_dir=layout.positive_train_output,
        val_dir=layout.positive_val_output,
        validation_ratio=args.validation_ratio,
        random_seed=args.random_seed,
        target_duration_sec=args.target_duration_sec,
        trim_silence=args.trim_silence,
        silence_threshold=args.silence_threshold,
    )
    neg_train, neg_val = process_group(
        files=negative_files,
        train_dir=layout.negative_train_output,
        val_dir=layout.negative_val_output,
        validation_ratio=args.validation_ratio,
        random_seed=args.random_seed + 1,
        target_duration_sec=args.target_duration_sec,
        trim_silence=args.trim_silence,
        silence_threshold=args.silence_threshold,
    )

    print("Prepared dataset saved to:", args.output_dir.resolve())
    print(f"positive_train={pos_train}, positive_val={pos_val}")
    print(f"negative_train={neg_train}, negative_val={neg_val}")
    print("Expected next step: use this prepared dataset as the source for your custom wakeword training pipeline.")


if __name__ == "__main__":
    main()
