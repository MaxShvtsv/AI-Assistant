"""TODO"""
from core.assistant_service import AssistantService
from voice.input.audio_recorder import record_wav
from voice.input.stt_faster_whisper import FasterWhisperSTT


stt = FasterWhisperSTT(
    model_size="small",
    device="cpu",
    compute_type="int8",
    language="ru",
)


def recognize_speech_from_mic(duration_sec: int = 5) -> str:
    wav_path = record_wav(
        output_path="D:\Desktop\Development\AI-Assistant\data\input.wav",
        duration_sec=duration_sec,
        sample_rate=16000,
        channels=1,
    )
    return stt.transcribe_file(wav_path)


def main():
    assistant = AssistantService()

    print("Intel is ready. Type 'exit' to quit.")

    while True:
        command = input("Enter 'v' for voice or 't' for text: ").strip().lower()

        if command == "v":
            user_message = recognize_speech_from_mic(duration_sec=6)
            print(f"[You said]: {user_message}")
        else:
            user_message = input("You: ").strip()

        if not user_message:
            continue

        answer = assistant.handle_text(user_message)
        print("Intel:", answer)


if __name__ == '__main__':
    main()
