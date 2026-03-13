import importlib.util
import sys
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write


MODULE_PATH = Path("utils/wakeword/train_intel_wakeword.py")
SPEC = importlib.util.spec_from_file_location("train_intel_wakeword", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_read_wav_mono_int16_converts_float_audio(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    sample_path = tmp_path / "sample.wav"
    audio = np.array([0.0, 0.5, -0.5], dtype=np.float32)
    write(sample_path, 16000, audio)

    output = MODULE.read_wav_mono_int16(sample_path)

    assert output.dtype == np.int16
    assert output.shape[0] == 3


def test_load_audio_batch_pads_to_equal_length(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    first = tmp_path / "a.wav"
    second = tmp_path / "b.wav"
    write(first, 16000, np.array([1, 2, 3], dtype=np.int16))
    write(second, 16000, np.array([1, 2, 3, 4, 5], dtype=np.int16))

    batch = MODULE.load_audio_batch([first, second])

    assert batch.shape == (2, 5)
    assert batch[0].tolist() == [1, 2, 3, 0, 0]


def test_get_dataset_paths_uses_prepared_layout(tmp_path: Path) -> None:
    paths = MODULE.get_dataset_paths(tmp_path)

    assert paths.positive_train == tmp_path / "positive_train"
    assert paths.negative_val == tmp_path / "negative_val"
