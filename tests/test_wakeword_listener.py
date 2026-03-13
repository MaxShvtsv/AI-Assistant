import importlib
import sys
import types


sys.path.insert(0, "app")

sounddevice_stub = types.ModuleType("sounddevice")
sounddevice_stub.InputStream = object
sys.modules.setdefault("sounddevice", sounddevice_stub)

listener_module = importlib.import_module("voice.wakeword.wakeword_listener")
WakeWordListener = listener_module.WakeWordListener


class FakeDetector:
    def predict(self, audio):
        return 0.73


def test_predict_score_accepts_float_from_detector() -> None:
    listener = WakeWordListener(
        detector=FakeDetector(),
        wakeword_name="Intel",
        on_wake=lambda: None,
    )

    score = listener._predict_score(audio=[1, 2, 3])

    assert score == 0.73
