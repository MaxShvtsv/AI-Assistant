from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io.wavfile import read


PREPARED_DATASET_DIR = Path("data/wakeword/prepared")
FEATURE_CACHE_DIR = Path("data/wakeword/features/intel")
MODEL_OUTPUT_DIR = Path("data/wakeword/models")


@dataclass(frozen=True)
class DatasetPaths:
    positive_train: Path
    positive_val: Path
    negative_train: Path
    negative_val: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a custom wakeword model for the wakeword 'Intel'."
    )
    parser.add_argument("--model-name", default="intel", help="Output model base name")
    parser.add_argument("--dataset-dir", type=Path, default=PREPARED_DATASET_DIR)
    parser.add_argument("--cache-dir", type=Path, default=FEATURE_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=MODEL_OUTPUT_DIR)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size-per-class", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--layer-size", type=int, default=128)
    parser.add_argument("--n-blocks", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=64, help="Feature extraction batch size")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu", help="Torch device")
    parser.add_argument("--force-recompute", action="store_true", help="Recompute cached feature arrays")
    parser.add_argument(
        "--export-tflite",
        action="store_true",
        help="Also try to export a .tflite model if tensorflow/onnx-tf are installed",
    )
    return parser.parse_args()


def get_dataset_paths(dataset_dir: Path) -> DatasetPaths:
    return DatasetPaths(
        positive_train=dataset_dir / "positive_train",
        positive_val=dataset_dir / "positive_val",
        negative_train=dataset_dir / "negative_train",
        negative_val=dataset_dir / "negative_val",
    )


def list_wavs(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    files = sorted(directory.glob("*.wav"))
    if not files:
        raise FileNotFoundError(f"No WAV files found in: {directory}")
    return files


def read_wav_mono_int16(path: Path) -> np.ndarray:
    sample_rate, audio = read(path)
    if sample_rate != 16000:
        raise ValueError(f"Expected 16kHz WAV, got {sample_rate}Hz in {path}")

    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    if np.issubdtype(audio.dtype, np.floating):
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767.0).astype(np.int16)
    elif audio.dtype != np.int16:
        peak = np.max(np.abs(audio)) if audio.size else 0
        if peak == 0:
            audio = audio.astype(np.int16)
        else:
            audio = (audio.astype(np.float32) / peak * 32767.0).astype(np.int16)

    return audio.astype(np.int16)


def load_audio_batch(files: list[Path]) -> np.ndarray:
    clips = [read_wav_mono_int16(path) for path in files]
    target_length = max(clip.shape[0] for clip in clips)
    padded = []
    for clip in clips:
        if clip.shape[0] < target_length:
            clip = np.pad(clip, (0, target_length - clip.shape[0]))
        elif clip.shape[0] > target_length:
            clip = clip[:target_length]
        padded.append(clip)
    return np.stack(padded, axis=0)


def extract_features(
    files: list[Path],
    cache_path: Path,
    batch_size: int,
    force_recompute: bool,
) -> np.ndarray:
    if cache_path.exists() and not force_recompute:
        return np.load(cache_path)

    try:
        import openwakeword
        from openwakeword.utils import AudioFeatures
    except Exception as exc:
        raise RuntimeError(
            "Failed to import openwakeword feature extraction. "
            "Make sure base dependencies are installed."
        ) from exc

    audio = load_audio_batch(files)
    inference_framework, model_paths = resolve_openwakeword_feature_models(openwakeword)
    extractor = AudioFeatures(
        device="cpu",
        inference_framework=inference_framework,
        melspec_model_path=str(model_paths["melspectrogram"]),
        embedding_model_path=str(model_paths["embedding"]),
    )
    features = extractor.embed_clips(audio, batch_size=batch_size)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, features)
    return features


def resolve_openwakeword_feature_models(openwakeword_module):
    feature_models = openwakeword_module.FEATURE_MODELS

    tflite_melspec = Path(feature_models["melspectrogram"]["model_path"])
    tflite_embedding = Path(feature_models["embedding"]["model_path"])
    onnx_melspec = Path(str(tflite_melspec).replace(".tflite", ".onnx"))
    onnx_embedding = Path(str(tflite_embedding).replace(".tflite", ".onnx"))

    if onnx_melspec.exists() and onnx_embedding.exists():
        return "onnx", {
            "melspectrogram": onnx_melspec,
            "embedding": onnx_embedding,
        }

    if tflite_melspec.exists() and tflite_embedding.exists():
        return "tflite", {
            "melspectrogram": tflite_melspec,
            "embedding": tflite_embedding,
        }

    try:
        openwakeword_module.utils.download_models()
    except Exception as exc:
        raise RuntimeError(
            "openWakeWord feature models are missing and automatic download failed. "
            "Run `python -c \"import openwakeword; openwakeword.utils.download_models()\"` "
            "and then rerun training."
        ) from exc

    if onnx_melspec.exists() and onnx_embedding.exists():
        return "onnx", {
            "melspectrogram": onnx_melspec,
            "embedding": onnx_embedding,
        }

    if tflite_melspec.exists() and tflite_embedding.exists():
        return "tflite", {
            "melspectrogram": tflite_melspec,
            "embedding": tflite_embedding,
        }

    raise RuntimeError(
        "openWakeWord feature models were not found after download. "
        "Expected either ONNX or TFLite versions of melspectrogram and embedding models."
    )


def build_train_dataset(
    positive_features: np.ndarray,
    negative_features: np.ndarray,
    batch_size_per_class: int,
):
    import torch

    class BalancedFeatureDataset(torch.utils.data.IterableDataset):
        def __init__(self, positives: np.ndarray, negatives: np.ndarray, per_class: int) -> None:
            self.positives = positives
            self.negatives = negatives
            self.per_class = per_class

        def __iter__(self):
            while True:
                pos_idx = np.random.randint(0, self.positives.shape[0], size=self.per_class)
                neg_idx = np.random.randint(0, self.negatives.shape[0], size=self.per_class)

                x = np.concatenate([self.positives[pos_idx], self.negatives[neg_idx]], axis=0)
                y = np.concatenate(
                    [
                        np.ones(self.per_class, dtype=np.float32),
                        np.zeros(self.per_class, dtype=np.float32),
                    ],
                    axis=0,
                )

                order = np.random.permutation(x.shape[0])
                yield (
                    torch.from_numpy(x[order]).to(torch.float32),
                    torch.from_numpy(y[order]).to(torch.float32),
                )

    return BalancedFeatureDataset(positive_features, negative_features, batch_size_per_class)


def build_validation_tensors(positive_features: np.ndarray, negative_features: np.ndarray):
    import torch

    x = np.concatenate([positive_features, negative_features], axis=0)
    y = np.concatenate(
        [
            np.ones(positive_features.shape[0], dtype=np.float32),
            np.zeros(negative_features.shape[0], dtype=np.float32),
        ],
        axis=0,
    )

    return (
        torch.from_numpy(x).to(torch.float32),
        torch.from_numpy(y).to(torch.float32),
    )


def create_model(input_shape: tuple[int, ...], layer_size: int, n_blocks: int):
    import torch
    from torch import nn

    class FCNBlock(nn.Module):
        def __init__(self, hidden_size: int) -> None:
            super().__init__()
            self.linear = nn.Linear(hidden_size, hidden_size)
            self.norm = nn.LayerNorm(hidden_size)
            self.relu = nn.ReLU()

        def forward(self, x):
            return self.relu(self.norm(self.linear(x)))

    class WakewordNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            flattened = input_shape[0] * input_shape[1]
            self.flatten = nn.Flatten()
            self.input_layer = nn.Linear(flattened, layer_size)
            self.input_norm = nn.LayerNorm(layer_size)
            self.input_relu = nn.ReLU()
            self.blocks = nn.ModuleList([FCNBlock(layer_size) for _ in range(n_blocks)])
            self.output_layer = nn.Linear(layer_size, 1)
            self.output_act = nn.Sigmoid()

        def forward(self, x):
            x = self.input_relu(self.input_norm(self.input_layer(self.flatten(x))))
            for block in self.blocks:
                x = block(x)
            return self.output_act(self.output_layer(x))

    return WakewordNet()


def evaluate_model(model, x_val, y_val, device: str) -> dict[str, float]:
    import torch

    model.eval()
    with torch.no_grad():
        predictions = model(x_val.to(device)).squeeze(-1)
        loss = torch.nn.functional.binary_cross_entropy(predictions, y_val.to(device))
        preds = (predictions >= 0.5).to(torch.float32)
        accuracy = (preds == y_val.to(device)).to(torch.float32).mean().item()

        pos_mask = y_val == 1
        neg_mask = y_val == 0
        recall = (
            (preds[pos_mask] == 1).to(torch.float32).mean().item()
            if pos_mask.any()
            else 0.0
        )
        false_positive_rate = (
            (preds[neg_mask] == 1).to(torch.float32).mean().item()
            if neg_mask.any()
            else 0.0
        )

    return {
        "loss": float(loss.item()),
        "accuracy": float(accuracy),
        "recall": float(recall),
        "false_positive_rate": float(false_positive_rate),
    }


def export_onnx(model, input_shape: tuple[int, ...], output_path: Path) -> None:
    import torch

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_input = torch.rand((1,) + input_shape, dtype=torch.float32)
    torch.onnx.export(
        model.to("cpu"),
        dummy_input,
        str(output_path),
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
    )


def convert_onnx_to_tflite(onnx_model_path: Path, output_path: Path) -> None:
    import onnx
    from onnx_tf.backend import prepare
    import tensorflow as tf

    onnx_model = onnx.load(str(onnx_model_path))
    tf_rep = prepare(onnx_model, device="CPU")
    saved_model_dir = output_path.parent / f"{output_path.stem}_saved_model"
    saved_model_dir.mkdir(parents=True, exist_ok=True)
    tf_rep.export_graph(str(saved_model_dir))
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
    tflite_model = converter.convert()
    output_path.write_bytes(tflite_model)


def train_model(args: argparse.Namespace) -> Path:
    try:
        import torch
    except Exception as exc:
        raise RuntimeError(
            "Torch is missing. Install training dependencies from requirements.txt first."
        ) from exc

    dataset = get_dataset_paths(args.dataset_dir)
    positive_train_files = list_wavs(dataset.positive_train)
    positive_val_files = list_wavs(dataset.positive_val)
    negative_train_files = list_wavs(dataset.negative_train)
    negative_val_files = list_wavs(dataset.negative_val)

    print("Extracting cached features from prepared WAV files...")
    positive_train = extract_features(
        positive_train_files,
        args.cache_dir / "positive_train.npy",
        batch_size=args.batch_size,
        force_recompute=args.force_recompute,
    )
    positive_val = extract_features(
        positive_val_files,
        args.cache_dir / "positive_val.npy",
        batch_size=args.batch_size,
        force_recompute=args.force_recompute,
    )
    negative_train = extract_features(
        negative_train_files,
        args.cache_dir / "negative_train.npy",
        batch_size=args.batch_size,
        force_recompute=args.force_recompute,
    )
    negative_val = extract_features(
        negative_val_files,
        args.cache_dir / "negative_val.npy",
        batch_size=args.batch_size,
        force_recompute=args.force_recompute,
    )

    if positive_train.shape[0] < 8 or negative_train.shape[0] < 8:
        raise ValueError("Need at least 8 positive and 8 negative training clips for a useful run")

    input_shape = tuple(int(dim) for dim in positive_train.shape[1:])
    print(f"Input feature shape: {input_shape}")
    print(
        "Train samples:",
        f"positive={positive_train.shape[0]}",
        f"negative={negative_train.shape[0]}",
    )
    print(
        "Validation samples:",
        f"positive={positive_val.shape[0]}",
        f"negative={negative_val.shape[0]}",
    )

    train_dataset = build_train_dataset(
        positive_features=positive_train,
        negative_features=negative_train,
        batch_size_per_class=args.batch_size_per_class,
    )
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=None)
    x_val, y_val = build_validation_tensors(positive_val, negative_val)

    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    model = create_model(input_shape, args.layer_size, args.n_blocks).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = torch.nn.BCELoss()

    best_state = None
    best_metrics = None

    print("Training wakeword model...")
    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        steps_per_epoch = max(
            1,
            int(np.ceil((positive_train.shape[0] + negative_train.shape[0]) / (args.batch_size_per_class * 2))),
        )

        iterator = iter(train_loader)
        for _ in range(steps_per_epoch):
            x_batch, y_batch = next(iterator)
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device).unsqueeze(-1)

            optimizer.zero_grad()
            predictions = model(x_batch)
            loss = loss_fn(predictions, y_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item())

        metrics = evaluate_model(model, x_val, y_val, device=device)
        print(
            f"epoch={epoch:02d}",
            f"train_loss={epoch_loss / steps_per_epoch:.4f}",
            f"val_loss={metrics['loss']:.4f}",
            f"val_acc={metrics['accuracy']:.3f}",
            f"val_recall={metrics['recall']:.3f}",
            f"val_fp={metrics['false_positive_rate']:.3f}",
        )

        if best_metrics is None:
            best_metrics = metrics
            best_state = copy.deepcopy(model.state_dict())
            continue

        better_recall = metrics["recall"] > best_metrics["recall"]
        same_recall_lower_fp = (
            metrics["recall"] >= best_metrics["recall"]
            and metrics["false_positive_rate"] < best_metrics["false_positive_rate"]
        )
        same_recall_same_fp_lower_loss = (
            metrics["recall"] >= best_metrics["recall"]
            and metrics["false_positive_rate"] <= best_metrics["false_positive_rate"]
            and metrics["loss"] < best_metrics["loss"]
        )

        if better_recall or same_recall_lower_fp or same_recall_same_fp_lower_loss:
            best_metrics = metrics
            best_state = copy.deepcopy(model.state_dict())

    if best_state is None:
        raise RuntimeError("Training finished without producing a model state")

    model.load_state_dict(best_state)
    model.eval()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = args.output_dir / f"{args.model_name}.onnx"
    export_onnx(model, input_shape=input_shape, output_path=onnx_path)
    print(f"Saved ONNX model: {onnx_path.resolve()}")

    if args.export_tflite:
        tflite_path = args.output_dir / f"{args.model_name}.tflite"
        try:
            convert_onnx_to_tflite(onnx_path, tflite_path)
            print(f"Saved TFLite model: {tflite_path.resolve()}")
        except Exception as exc:
            print(f"[Warning] TFLite export failed: {exc}")
            print("Install optional ONNX/TensorFlow conversion dependencies and try again.")

    return onnx_path


def main() -> None:
    args = parse_args()
    onnx_path = train_model(args)
    print()
    print("Next step:")
    print(f'Set INTEL_WAKEWORD_MODEL_PATH="{onnx_path.resolve()}" in your .env')
    print(f'Set INTEL_WAKEWORD_MODEL_KEY="{args.model_name}" in your .env')


if __name__ == "__main__":
    main()
