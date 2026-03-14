"""Main entry point for AI Assistant with wake word support."""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from dotenv import load_dotenv

from core.assistant_service import AssistantService
from voice.input.audio_recorder import record_command_until_silence
from voice.input.stt_faster_whisper import FasterWhisperSTT
from voice.output.tts_windows import speak_text
from voice.sound_cues import play_audio_cue
from voice.wakeword.openwakeword_detector import OpenWakeWordDetector
from voice.wakeword.wakeword_listener import WakeWordConfig, WakeWordListener


def get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


RUNTIME_ROOT = get_runtime_root()
load_dotenv(RUNTIME_ROOT / ".env")


def _resolve_runtime_path(raw_path: Optional[str], default: Path) -> Path:
    if not raw_path:
        return default

    candidate = Path(raw_path.strip().strip('"'))
    if candidate.is_absolute():
        return candidate
    return (RUNTIME_ROOT / candidate).resolve()


BASE_INPUT_DIR = RUNTIME_ROOT / "data" / "input"
DEFAULT_START_CUE_PATH = RUNTIME_ROOT / "data" / "sounds" / "intel_start.wav"
DEFAULT_END_CUE_PATH = RUNTIME_ROOT / "data" / "sounds" / "intel_end.wav"
DEFAULT_WAKEWORD_MODEL_PATH = RUNTIME_ROOT / "data" / "wakeword" / "models" / "intel.onnx"

WAKEWORD_PHRASE = os.getenv("INTEL_WAKEWORD_PHRASE", "Intel")
WAKEWORD_MODEL_KEY = os.getenv("INTEL_WAKEWORD_MODEL_KEY", "assistant")
WAKEWORD_MODEL_PATH_RAW = os.getenv("INTEL_WAKEWORD_MODEL_PATH")
WAKEWORD_MODEL_PATH = (
    str(_resolve_runtime_path(WAKEWORD_MODEL_PATH_RAW, DEFAULT_WAKEWORD_MODEL_PATH))
    if WAKEWORD_MODEL_PATH_RAW
    else None
)
WAKEWORD_THRESHOLD = float(os.getenv("INTEL_WAKEWORD_THRESHOLD", "0.58"))
WAKEWORD_MIN_RMS = float(os.getenv("INTEL_WAKEWORD_MIN_RMS", "220"))
WAKEWORD_MIN_CONSECUTIVE_HITS = int(os.getenv("INTEL_WAKEWORD_MIN_CONSECUTIVE_HITS", "2"))
WAKEWORD_COOLDOWN_SEC = float(os.getenv("INTEL_WAKEWORD_COOLDOWN_SEC", "3.0"))
WAKEWORD_IDLE_RESET_SEC = float(os.getenv("INTEL_WAKEWORD_IDLE_RESET_SEC", "4.0"))
WAKEWORD_INSTANT_THRESHOLD = float(os.getenv("INTEL_WAKEWORD_INSTANT_THRESHOLD", "0.72"))
WAKEWORD_WINDOW_FRAMES = int(os.getenv("INTEL_WAKEWORD_WINDOW_FRAMES", "4"))
WAKEWORD_WINDOW_RATIO = float(os.getenv("INTEL_WAKEWORD_WINDOW_RATIO", "0.82"))
WAKEWORD_PRE_ROLL_CHUNKS = int(os.getenv("INTEL_WAKEWORD_PRE_ROLL_CHUNKS", "8"))
WAKEWORD_DEBUG = os.getenv("INTEL_WAKEWORD_DEBUG", "0") == "1"
WAKEWORD_DEBUG_SCORE_THRESHOLD = float(os.getenv("INTEL_WAKEWORD_DEBUG_SCORE_THRESHOLD", "0.15"))

REQUIRE_WAKEWORD_IN_TRANSCRIPT = os.getenv("INTEL_REQUIRE_WAKEWORD_IN_TRANSCRIPT", "0") == "1"
COMMAND_START_TIMEOUT_SEC = float(os.getenv("INTEL_COMMAND_START_TIMEOUT_SEC", "7.0"))
COMMAND_MAX_DURATION_SEC = float(os.getenv("INTEL_COMMAND_MAX_DURATION_SEC", "12.0"))
COMMAND_SILENCE_DURATION_SEC = float(os.getenv("INTEL_COMMAND_SILENCE_DURATION_SEC", "1.3"))

STT_MODEL_SIZE = os.getenv("INTEL_STT_MODEL_SIZE", "small")
STT_MODEL_PATH_RAW = os.getenv("INTEL_STT_MODEL_PATH")
STT_MODEL_PATH = (
    str(_resolve_runtime_path(STT_MODEL_PATH_RAW, RUNTIME_ROOT / "models" / "faster-whisper"))
    if STT_MODEL_PATH_RAW
    else None
)
STT_DEVICE = os.getenv("INTEL_STT_DEVICE", "cpu")
STT_COMPUTE_TYPE = os.getenv("INTEL_STT_COMPUTE_TYPE", "int8")
STT_BEAM_SIZE = int(os.getenv("INTEL_STT_BEAM_SIZE", "5"))
STT_BEST_OF = int(os.getenv("INTEL_STT_BEST_OF", "3"))
STT_TEMPERATURE = float(os.getenv("INTEL_STT_TEMPERATURE", "0.0"))
STT_VAD_MIN_SILENCE_MS = int(os.getenv("INTEL_STT_VAD_MIN_SILENCE_MS", "500"))

COMMAND_START_CUE_PATH = _resolve_runtime_path(
    os.getenv("INTEL_COMMAND_START_CUE_PATH"),
    DEFAULT_START_CUE_PATH,
)
COMMAND_END_CUE_PATH = _resolve_runtime_path(
    os.getenv("INTEL_COMMAND_END_CUE_PATH"),
    DEFAULT_END_CUE_PATH,
)

TTS_ENABLED = os.getenv("INTEL_TTS_ENABLED", "1") == "1"
TTS_VOICE_NAME = os.getenv("INTEL_TTS_VOICE_NAME")
TTS_RU_VOICE_NAME = os.getenv("INTEL_TTS_RU_VOICE_NAME", "Seva")
TTS_EN_VOICE_NAME = os.getenv("INTEL_TTS_EN_VOICE_NAME", "David")
TTS_RATE = int(os.getenv("INTEL_TTS_RATE", "2"))
TTS_VOLUME = int(os.getenv("INTEL_TTS_VOLUME", "100"))
TTS_MAX_CHARS = int(os.getenv("INTEL_TTS_MAX_CHARS", "280"))


stt = FasterWhisperSTT(
    model_size=STT_MODEL_SIZE,
    model_path=STT_MODEL_PATH,
    device=STT_DEVICE,
    compute_type=STT_COMPUTE_TYPE,
    language="ru",
    beam_size=STT_BEAM_SIZE,
    best_of=STT_BEST_OF,
    temperature=STT_TEMPERATURE,
    vad_min_silence_duration_ms=STT_VAD_MIN_SILENCE_MS,
)


def recognize_speech_from_command_audio(initial_audio: Optional[np.ndarray] = None) -> str:
    """Record a voice command after wake word activation and transcribe it."""
    BASE_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    command_audio_path = BASE_INPUT_DIR / f"command_{int(time.time() * 1000)}.wav"

    initial_rms = _compute_audio_rms(initial_audio)
    should_play_start_cue = initial_rms < 500
    if should_play_start_cue:
        play_audio_cue(str(COMMAND_START_CUE_PATH), wait=True)

    wav_path = record_command_until_silence(
        output_path=str(command_audio_path),
        sample_rate=16000,
        blocksize=1024,
        speech_threshold=650,
        silence_threshold=400,
        min_speech_duration_sec=0.25,
        start_timeout_sec=COMMAND_START_TIMEOUT_SEC,
        silence_duration_sec=COMMAND_SILENCE_DURATION_SEC,
        max_duration_sec=COMMAND_MAX_DURATION_SEC,
        initial_audio=initial_audio,
    )
    play_audio_cue(str(COMMAND_END_CUE_PATH), wait=False)

    return stt.transcribe_file(wav_path).strip()


def build_wake_handler(assistant: AssistantService) -> Callable[[Optional[np.ndarray]], None]:
    """Create a callback that runs when wake word is detected."""
    activation_lock = threading.Lock()

    def handle_wake(initial_audio: Optional[np.ndarray] = None) -> None:
        if not activation_lock.acquire(blocking=False):
            print("[WakeWord] Activation ignored because another command is already being processed.")
            return

        print("[WakeWord] Activated. Listening for command...")

        try:
            user_message = recognize_speech_from_command_audio(initial_audio=initial_audio)
        except Exception as exc:
            print(f"[Error] Failed to record/transcribe command: {exc}")
            activation_lock.release()
            return

        if not user_message:
            print("[WakeWord] Empty command detected.")
            activation_lock.release()
            return

        if REQUIRE_WAKEWORD_IN_TRANSCRIPT and not transcript_contains_wakeword(user_message):
            print(f"[WakeWord] Ignored false activation: '{user_message}'")
            activation_lock.release()
            return

        user_message = strip_wakeword_from_transcript(user_message).strip(" ,.!?:;-")
        if not user_message:
            print("[WakeWord] Wake word detected, but command is empty.")
            activation_lock.release()
            return

        print(f"[You said]: {user_message}")

        try:
            answer = assistant.handle_text(user_message)
            print("Intel:", answer)
            if TTS_ENABLED and answer:
                speak_text(
                    answer,
                    voice_name=TTS_VOICE_NAME,
                    rate=TTS_RATE,
                    volume=TTS_VOLUME,
                    max_chars=TTS_MAX_CHARS,
                    ru_voice_name=TTS_RU_VOICE_NAME,
                    en_voice_name=TTS_EN_VOICE_NAME,
                )
        except Exception as exc:
            print(f"[Error] Assistant failed to process command: {exc}")
        finally:
            activation_lock.release()

    return handle_wake


def normalize_text(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def wakeword_variants() -> list[str]:
    normalized_phrase = normalize_text(WAKEWORD_PHRASE)
    variants = {
        normalized_phrase,
        "интел",
        "intel",
    }
    return [variant for variant in variants if variant]


def transcript_contains_wakeword(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    if not normalized:
        return False

    return any(
        normalized == variant
        or normalized.startswith(variant + " ")
        or f" {variant} " in f" {normalized} "
        for variant in wakeword_variants()
    )


def strip_wakeword_from_transcript(transcript: str) -> str:
    cleaned = transcript.strip()
    pattern = re.compile(r"^\s*(intel|интел)\s*[,.!?:;-]?\s*", flags=re.IGNORECASE)
    return pattern.sub("", cleaned, count=1)


def _compute_audio_rms(audio: Optional[np.ndarray]) -> float:
    if audio is None:
        return 0.0
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def main() -> None:
    assistant = AssistantService()

    print("Intel is ready.")

    detector = OpenWakeWordDetector(
        wakeword_name=WAKEWORD_MODEL_KEY,
        threshold=WAKEWORD_THRESHOLD,
        model_path=WAKEWORD_MODEL_PATH,
        download_models=WAKEWORD_MODEL_PATH is None,
    )

    listener = WakeWordListener(
        detector=detector,
        wakeword_name=WAKEWORD_PHRASE,
        on_wake=build_wake_handler(assistant),
        config=WakeWordConfig(
            sample_rate=16000,
            channels=1,
            dtype="int16",
            blocksize=1280,
            detection_threshold=WAKEWORD_THRESHOLD,
            cooldown_sec=WAKEWORD_COOLDOWN_SEC,
            min_chunk_rms=WAKEWORD_MIN_RMS,
            min_consecutive_detections=WAKEWORD_MIN_CONSECUTIVE_HITS,
            debug_log_scores=WAKEWORD_DEBUG,
            debug_score_threshold=WAKEWORD_DEBUG_SCORE_THRESHOLD,
            detector_idle_reset_sec=WAKEWORD_IDLE_RESET_SEC,
            instant_detection_threshold=WAKEWORD_INSTANT_THRESHOLD,
            activation_window_frames=WAKEWORD_WINDOW_FRAMES,
            activation_window_ratio=WAKEWORD_WINDOW_RATIO,
            pre_roll_chunks=WAKEWORD_PRE_ROLL_CHUNKS,
        ),
    )

    if WAKEWORD_PHRASE.lower() != WAKEWORD_MODEL_KEY.lower() and not WAKEWORD_MODEL_PATH:
        print(
            "[WakeWord] Warning: activation phrase and detector model key differ. "
            "For the phrase 'Intel' you usually need a custom openWakeWord model."
        )

    print(
        f"[WakeWord] Listening continuously for '{WAKEWORD_PHRASE}'. "
        "Press Ctrl+C to stop."
    )
    try:
        listener.start()
    except KeyboardInterrupt:
        print("\n[WakeWord] Stopped.")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
