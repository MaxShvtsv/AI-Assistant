from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import openwakeword
from openwakeword.model import Model


class OpenWakeWordDetector:
    """
    Adapter around openWakeWord that returns a single float score
    for one configured wake word.

    Supports two modes:
    1. Built-in / downloaded pre-trained models
    2. Custom local model file (.onnx / .tflite)

    Notes:
    - Input audio must be 16-bit PCM, 16 kHz.
    - `predict()` is intended to be called repeatedly on short audio frames.
    """

    def __init__(
        self,
        wakeword_name: str,
        threshold: float = 0.5,
        model_path: Optional[str] = None,
        vad_threshold: Optional[float] = None,
        download_models: bool = True,
    ) -> None:
        self.wakeword_name = wakeword_name
        self.threshold = float(threshold)
        self.model_path = model_path
        self.vad_threshold = vad_threshold

        # If you want to use built-in/pretrained models,
        # downloading them once is the easiest path.
        if download_models and model_path is None:
            try:
                openwakeword.utils.download_models()
            except Exception as exc:
                # Don't crash here immediately; model init below may still succeed
                # if models are already present.
                print(f"[OpenWakeWord] Model download skipped/failed: {exc}")

        self.model = self._build_model()
        self._model_key = self._resolve_model_key()

    def _build_model(self) -> Model:
        """
        Create the underlying openWakeWord model.
        """
        kwargs = {}

        if self.vad_threshold is not None:
            kwargs["vad_threshold"] = float(self.vad_threshold)

        if self.model_path:
            model_file = Path(self.model_path)
            if not model_file.exists():
                raise FileNotFoundError(f"Wake word model file not found: {model_file}")

            # openWakeWord accepts a list of model paths.
            kwargs["wakeword_models"] = [str(model_file)]

        return Model(**kwargs)

    def _resolve_model_key(self) -> str:
        """
        Figure out which key will appear in prediction dicts.

        For a custom model file, openWakeWord usually uses the model filename stem
        as the prediction key.

        For built-in models, the prediction key is typically the wake word name itself.
        """
        if self.model_path:
            return Path(self.model_path).stem
        return self.wakeword_name

    def predict(self, audio: np.ndarray) -> float:
        """
        Return detection score for the configured wake word.

        Parameters
        ----------
        audio : np.ndarray
            16-bit PCM 16 kHz mono audio chunk.

        Returns
        -------
        float
            Detection score in range [0, 1] in normal scenarios.
        """
        prepared_audio = self._prepare_audio(audio)

        predictions = self.model.predict(prepared_audio)

        if not isinstance(predictions, dict):
            return 0.0

        # Exact key match first
        if self._model_key in predictions:
            return float(predictions[self._model_key])

        # Fallback: fuzzy matching by normalized names
        normalized_target = self._normalize_name(self.wakeword_name)
        for key, value in predictions.items():
            if self._normalize_name(key) == normalized_target:
                return float(value)

        return 0.0

    def is_detected(self, audio: np.ndarray) -> bool:
        """
        Convenience helper if you want direct bool usage.
        """
        return self.predict(audio) >= self.threshold

    @staticmethod
    def _prepare_audio(audio: np.ndarray) -> np.ndarray:
        """
        Normalize input chunk shape/dtype for openWakeWord.

        Expected format from docs:
        - 16-bit PCM
        - 16 kHz
        """
        if audio is None:
            raise ValueError("Audio chunk is None")

        if not isinstance(audio, np.ndarray):
            audio = np.asarray(audio)

        # squeeze (N,1) -> (N,)
        audio = np.squeeze(audio)

        if audio.ndim != 1:
            raise ValueError(f"Audio chunk must be 1D after squeeze, got shape={audio.shape}")

        if audio.dtype != np.int16:
            # safer conversion
            audio = audio.astype(np.int16)

        return audio

    @staticmethod
    def _normalize_name(name: str) -> str:
        return (
            name.strip()
            .lower()
            .replace("-", " ")
            .replace("_", " ")
        )