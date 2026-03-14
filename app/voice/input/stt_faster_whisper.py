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
        model_size: str = "small",
        model_path: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = "ru",
        beam_size: int = 5,
        best_of: int = 3,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_min_silence_duration_ms: int = 500,
        initial_prompt: Optional[str] = DEFAULT_INITIAL_PROMPT,
    ):
        self.language = language
        self.beam_size = beam_size
        self.best_of = best_of
        self.temperature = temperature
        self.vad_filter = vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.initial_prompt = initial_prompt
        model_reference = model_path or model_size
        self.model = WhisperModel(
            model_reference,
            device=device,
            compute_type=compute_type,
            local_files_only=bool(model_path),
        )

    def transcribe_file(self, audio_path: str) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments, _ = self.model.transcribe(
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

        return " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text and segment.text.strip()
        ).strip()
