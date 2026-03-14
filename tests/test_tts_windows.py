import importlib
import sys


sys.path.insert(0, "app")

tts = importlib.import_module("voice.output.tts_windows")


def test_prepare_tts_text_trims_whitespace() -> None:
    result = tts.prepare_tts_text("  Intel   готов   помочь  ")

    assert result == "Intel готов помочь"


def test_prepare_tts_text_removes_extra_punctuation() -> None:
    result = tts.prepare_tts_text("Привет, Intel: открой папку / Downloads.")

    assert result == "Привет Intel открой папку Downloads"


def test_split_text_into_chunks_preserves_full_text() -> None:
    text = "Первая фраза. Вторая фраза немного длиннее. Третья фраза."

    chunks = tts.split_text_into_chunks(text, max_chars=20)

    assert len(chunks) >= 3
    assert " ".join(chunks) == text


def test_split_text_by_language_keeps_spaces_inside_segments() -> None:
    result = tts.split_text_by_language(
        "Открываю GitHub и папку Downloads",
        ru_voice_name="Seva",
        en_voice_name="David",
    )

    assert any(segment["text"] == "Открываю" and segment["voice"] == "Seva" for segment in result)
    assert any(segment["text"] == "GitHub" and segment["voice"] == "David" for segment in result)
    assert any("и папку" in segment["text"] for segment in result)


def test_split_text_by_language_uses_different_voice_hints() -> None:
    result = tts.split_text_by_language(
        "Открываю GitHub и папку Downloads",
        ru_voice_name="Seva",
        en_voice_name="David",
    )

    assert any(segment["voice"] == "Seva" for segment in result)
    assert any(segment["voice"] == "David" for segment in result)
