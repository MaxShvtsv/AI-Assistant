import importlib
import sys
import types


sys.path.insert(0, "app")

sounddevice_stub = types.ModuleType("sounddevice")
sounddevice_stub.InputStream = object
sys.modules.setdefault("sounddevice", sounddevice_stub)

listener_module = importlib.import_module("voice.wakeword.wakeword_listener")
WakeWordConfig = listener_module.WakeWordConfig
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


def test_compute_chunk_rms_returns_zero_for_silence() -> None:
    rms = WakeWordListener._compute_chunk_rms([0, 0, 0, 0])

    assert rms == 0.0


def test_listener_supports_configured_detection_guards() -> None:
    listener = WakeWordListener(
        detector=FakeDetector(),
        wakeword_name="Intel",
        on_wake=lambda: None,
        config=WakeWordConfig(
            min_chunk_rms=220.0,
            min_consecutive_detections=4,
            debug_log_scores=True,
            debug_score_threshold=0.2,
            activation_window_frames=5,
            activation_window_ratio=0.85,
        ),
    )

    assert listener.config.min_chunk_rms == 220.0
    assert listener.config.min_consecutive_detections == 4
    assert listener.config.debug_log_scores is True
    assert listener.config.debug_score_threshold == 0.2
    assert listener.config.activation_window_frames == 5
    assert listener.config.activation_window_ratio == 0.85
