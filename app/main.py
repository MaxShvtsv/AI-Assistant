"""Main entry point for AI Assistant with wake word support."""

import os
from pathlib import Path
from typing import Callable

from core.assistant_service import AssistantService
from voice.input.audio_recorder import record_command_until_silence
from voice.input.stt_faster_whisper import FasterWhisperSTT
from voice.wakeword.wakeword_listener import WakeWordConfig, WakeWordListener
from voice.wakeword.openwakeword_detector import OpenWakeWordDetector


BASE_INPUT_DIR = Path(r"D:\Desktop\Development\AI-Assistant\data\input")
COMMAND_AUDIO_PATH = BASE_INPUT_DIR / "command.wav"
WAKEWORD_PHRASE = os.getenv("INTEL_WAKEWORD_PHRASE", "Intel")
WAKEWORD_MODEL_KEY = os.getenv("INTEL_WAKEWORD_MODEL_KEY", "assistant")
WAKEWORD_MODEL_PATH = os.getenv("INTEL_WAKEWORD_MODEL_PATH")


stt = FasterWhisperSTT(
    model_size="small",
    device="cpu",
    compute_type="int8",
    language="ru",
)


def recognize_speech_from_command_audio() -> str:
    """
    Record a voice command after wake word activation and transcribe it.
    """
    BASE_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    wav_path = record_command_until_silence(
        output_path=str(COMMAND_AUDIO_PATH),
        sample_rate=16000,
        blocksize=1024,
        speech_threshold=650,
        silence_threshold=400,
        min_speech_duration_sec=0.25,
        start_timeout_sec=4.0,
        silence_duration_sec=1.0,
        max_duration_sec=8.0,
    )

    return stt.transcribe_file(wav_path).strip()


def build_wake_handler(assistant: AssistantService) -> Callable[[], None]:
    """
    Create a callback that runs when wake word is detected.
    """

    def handle_wake() -> None:
        print("[WakeWord] Activated. Listening for command...")

        try:
            user_message = recognize_speech_from_command_audio()
        except Exception as exc:
            print(f"[Error] Failed to record/transcribe command: {exc}")
            return

        if not user_message:
            print("[WakeWord] Empty command detected.")
            return

        print(f"[You said]: {user_message}")

        try:
            answer = assistant.handle_text(user_message)
            print("Intel:", answer)
        except Exception as exc:
            print(f"[Error] Assistant failed to process command: {exc}")

    return handle_wake


def main() -> None:
    assistant = AssistantService()

    print("Intel is ready.")
    print("Modes:")
    print("  1. Wake word mode")
    print("  2. Text mode fallback")
    print("Type 'exit' in text mode to quit.")

    detector = OpenWakeWordDetector(
        wakeword_name=WAKEWORD_MODEL_KEY,
        threshold=0.5,
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
            detection_threshold=0.5,
            cooldown_sec=2.5,
        ),
    )

    if WAKEWORD_PHRASE.lower() != WAKEWORD_MODEL_KEY.lower() and not WAKEWORD_MODEL_PATH:
        print(
            "[WakeWord] Warning: activation phrase and detector model key differ. "
            "For the phrase 'Intel' you usually need a custom openWakeWord model."
        )

    try:
        while True:
            mode = input("\nEnter 'w' for wake word mode or 't' for text mode: ").strip().lower()

            if mode == "t":
                user_message = input("You: ").strip()

                if user_message.lower() == "exit":
                    break

                if not user_message:
                    continue

                try:
                    answer = assistant.handle_text(user_message)
                    print("Intel:", answer)
                except Exception as exc:
                    print(f"[Error] Assistant failed to process text: {exc}")

            elif mode == "w":
                print(
                    f"[WakeWord] Listening continuously for '{WAKEWORD_PHRASE}'. "
                    "Press Ctrl+C to stop wake word mode."
                )
                try:
                    listener.start()
                except KeyboardInterrupt:
                    listener.stop()
                    print("\n[WakeWord] Stopped. Returning to mode selection.")

            else:
                print("Unknown mode. Use 'w' or 't'.")

    finally:
        listener.stop()


if __name__ == "__main__":
    main()
