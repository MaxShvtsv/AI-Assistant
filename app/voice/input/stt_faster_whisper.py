from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import Optional

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

warnings.filterwarnings(
    "ignore",
    message=".*huggingface_hub.*symlinks.*",
)

logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("faster_whisper").setLevel(logging.ERROR)

from faster_whisper import WhisperModel


DEFAULT_INITIAL_PROMPT = (
    "Это короткие голосовые команды локальному ассистенту Intel на русском языке. "
    "Частые слова и фразы: Intel, интел, открой проводник, открой диск C, открой диск D, "
    "открой браузер, открой телеграм, открой vscode, покажи файлы, создай папку, "
    "прочитай файл, скопируй файл, перемести файл."
)


class FasterWhisperSTT:
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = "ru",
        beam_size: int = 7,
        best_of: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_min_silence_duration_ms: int = 500,
        initial_prompt: Optional[str] = DEFAULT_INITIAL_PROMPT,
    ):
        """
        model_size examples: tiny, base, small, medium, large-v3, large-v3-turbo
        device: 'cpu' or 'cuda'
        compute_type examples:
            CPU  -> int8
            GPU  -> float16 / int8_float16
        """
        self.language = language
        self.beam_size = beam_size
        self.best_of = best_of
        self.temperature = temperature
        self.vad_filter = vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.initial_prompt = initial_prompt
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            local_files_only=False,
        )

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe audio file and return plain text."""
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments, info = self.model.transcribe(
            str(path),
            language=self.language,
            vad_filter=self.vad_filter,
            vad_parameters={
                "min_silence_duration_ms": self.vad_min_silence_duration_ms,
            },
            beam_size=self.beam_size,
            best_of=self.best_of,
            temperature=self.temperature,
            condition_on_previous_text=False,
            initial_prompt=self.initial_prompt,
        )

        parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)

        return " ".join(parts).strip()
