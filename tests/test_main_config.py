import importlib
import os
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


def test_wakeword_in_transcript_check_is_disabled_by_default() -> None:
    os.environ.pop("INTEL_REQUIRE_WAKEWORD_IN_TRANSCRIPT", None)
    if "main" in sys.modules:
        del sys.modules["main"]

    main_module = importlib.import_module("main")

    assert main_module.REQUIRE_WAKEWORD_IN_TRANSCRIPT is False
