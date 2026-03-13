import importlib.util
import sys
from pathlib import Path

import numpy as np


MODULE_PATH = Path("utils/wakeword/prepare_dataset.py")
SPEC = importlib.util.spec_from_file_location("prepare_dataset", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_fit_duration_pads_audio() -> None:
    audio = np.array([1, 2, 3], dtype=np.int16)
    output = MODULE.fit_duration(audio, 5)

    assert output.dtype == np.int16
    assert output.shape[0] == 5
    assert output.tolist() == [1, 2, 3, 0, 0]


def test_fit_duration_trims_audio() -> None:
    audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    output = MODULE.fit_duration(audio, 3)

    assert output.tolist() == [1, 2, 3]


def test_maybe_trim_silence_keeps_active_region() -> None:
    audio = np.array([0, 0, 20, 40, 0, 0], dtype=np.int16)
    output = MODULE.maybe_trim_silence(audio, silence_threshold=10)

    assert output.tolist() == [20, 40]
