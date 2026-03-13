from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel


class FasterWhisperSTT:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = "ru",
    ):
        """
        model_size examples: tiny, base, small, medium, large-v3, large-v3-turbo
        device: 'cpu' or 'cuda'
        compute_type examples:
            CPU  -> int8
            GPU  -> float16 / int8_float16
        """
        self.language = language
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe_file(self, audio_path: str) -> str:
        """
        Transcribe audio file and return plain text.
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments, info = self.model.transcribe(
            str(path),
            language=self.language,
            vad_filter=True,
            beam_size=5,
        )

        parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)

        return " ".join(parts).strip()
