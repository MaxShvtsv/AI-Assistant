import importlib
import sys
import types


sys.path.insert(0, "app")

ollama_stub = types.ModuleType("ollama")


class DummyClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def chat(self, *args, **kwargs):
        return {"message": {"content": ""}}


ollama_stub.Client = DummyClient
sys.modules.setdefault("ollama", ollama_stub)

sounddevice_stub = types.ModuleType("sounddevice")
sounddevice_stub.InputStream = object
sys.modules.setdefault("sounddevice", sounddevice_stub)

faster_whisper_stub = types.ModuleType("faster_whisper")


class DummyWhisperModel:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def transcribe(self, *args, **kwargs):
        return [], None


faster_whisper_stub.WhisperModel = DummyWhisperModel
sys.modules.setdefault("faster_whisper", faster_whisper_stub)

main_module = importlib.import_module("main")


def test_transcript_contains_wakeword_detects_intel() -> None:
    assert main_module.transcript_contains_wakeword("Интел открой папку")
    assert main_module.transcript_contains_wakeword("Intel open explorer")


def test_transcript_contains_wakeword_rejects_plain_speech() -> None:
    assert not main_module.transcript_contains_wakeword("Хорошо, молодец")
    assert not main_module.transcript_contains_wakeword("1 2 3")


def test_strip_wakeword_from_transcript_removes_prefix() -> None:
    assert main_module.strip_wakeword_from_transcript("Интел, открой проводник") == "открой проводник"
