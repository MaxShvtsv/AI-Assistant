from pathlib import Path
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


def record_wav(
    output_path: str = "D:\Desktop\Development\AI-Assistant\data\input.wav",
    duration_sec: int = 5,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str:
    """
    Record audio from the default microphone and save it as WAV.
    """
    output = Path(output_path)

    print(f"Recording {duration_sec} sec...")
    audio = sd.rec(
        int(duration_sec * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
    )
    sd.wait()

    write(output, sample_rate, audio)
    print(f"Saved audio to: {output.resolve()}")
    return str(output.resolve())