from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from typing import Optional


def speak_text(
    text: str,
    voice_name: Optional[str] = None,
    rate: int = 0,
    volume: int = 100,
    max_chars: int = 280,
    ru_voice_name: Optional[str] = None,
    en_voice_name: Optional[str] = None,
) -> bool:
    prepared = prepare_tts_text(text)
    if not prepared:
        return False

    segments = split_text_into_voice_segments(
        prepared,
        max_chars=max_chars,
        default_voice_name=voice_name,
        ru_voice_name=ru_voice_name,
        en_voice_name=en_voice_name,
    )
    if not segments:
        return False

    script = build_tts_powershell_script(
        segments=segments,
        rate=rate,
        volume=volume,
    )

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            _encode_powershell_script(script),
        ],
        capture_output=True,
        text=True,
        check=False,
        creationflags=_creationflags_no_window(),
        startupinfo=_startupinfo_no_window(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        print(f"[tts] failed to speak text: {stderr or completed.returncode}")
        return False

    return True


def prepare_tts_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"[,:;()\[\]{}\"'`]+", " ", cleaned)
    cleaned = re.sub(r"[\\/|]+", " ", cleaned)
    cleaned = re.sub(r"\s*[.?!]+\s*", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned


def split_text_into_voice_segments(
    text: str,
    max_chars: int = 280,
    default_voice_name: Optional[str] = None,
    ru_voice_name: Optional[str] = None,
    en_voice_name: Optional[str] = None,
) -> list[dict[str, str]]:
    text_chunks = split_text_into_chunks(text, max_chars=max_chars)
    segments: list[dict[str, str]] = []

    for chunk in text_chunks:
        segments.extend(
            split_text_by_language(
                chunk,
                default_voice_name=default_voice_name,
                ru_voice_name=ru_voice_name,
                en_voice_name=en_voice_name,
            )
        )

    return segments


def split_text_by_language(
    text: str,
    default_voice_name: Optional[str] = None,
    ru_voice_name: Optional[str] = None,
    en_voice_name: Optional[str] = None,
) -> list[dict[str, str]]:
    chunks = re.findall(r"[A-Za-z0-9_./:-]+|[А-Яа-яЁё0-9_./:-]+|[^A-Za-zА-Яа-яЁё]+", text)
    if not chunks:
        return []

    segments: list[dict[str, str]] = []
    current_text = ""
    current_voice = ""

    for chunk in chunks:
        voice_hint = _voice_for_chunk(
            chunk,
            default_voice_name=default_voice_name,
            ru_voice_name=ru_voice_name,
            en_voice_name=en_voice_name,
        )

        if not current_text:
            current_text = chunk
            current_voice = voice_hint
            continue

        if not voice_hint:
            current_text += chunk
            continue

        if not current_voice or voice_hint == current_voice:
            current_text += chunk
            current_voice = voice_hint or current_voice
            continue

        if current_text.strip():
            segments.append({"text": current_text.strip(), "voice": current_voice or ""})
        current_text = chunk
        current_voice = voice_hint

    if current_text.strip():
        segments.append({"text": current_text.strip(), "voice": current_voice or ""})

    return segments


def split_text_into_chunks(text: str, max_chars: int = 280) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    if max_chars <= 0 or len(cleaned) <= max_chars:
        return [cleaned]

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_sentence(sentence, max_chars))
            continue

        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    return chunks


def _split_long_sentence(text: str, max_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = word
            continue

        chunks.extend(_split_long_word(word, max_chars))
        current = ""

    if current:
        chunks.append(current.strip())

    return chunks


def _split_long_word(word: str, max_chars: int) -> list[str]:
    return [word[index:index + max_chars] for index in range(0, len(word), max_chars)]


def build_tts_powershell_script(
    segments: list[dict[str, str]],
    rate: int,
    volume: int,
) -> str:
    payload = base64.b64encode(json.dumps(segments, ensure_ascii=False).encode("utf-8")).decode("ascii")
    safe_rate = max(-10, min(10, int(rate)))
    safe_volume = max(0, min(100, int(volume)))

    return f"""
$payload = '{payload}'
$segments = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($payload)) | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$voice.Rate = {safe_rate}
$voice.Volume = {safe_volume}
$tokens = $voice.GetVoices()
$selectedToken = $null
$selectedDescription = ''

foreach ($segment in $segments) {{
    $text = [string]$segment.text
    if (-not $text) {{
        continue
    }}

    $voiceHint = [string]$segment.voice
    if ($voiceHint -and $voiceHint -ne $selectedDescription) {{
        $match = $null
        for ($i = 0; $i -lt $tokens.Count; $i++) {{
            $token = $tokens.Item($i)
            $description = $token.GetDescription()
            if ($description -like ('*' + $voiceHint + '*')) {{
                $match = $token
                $selectedDescription = $description
                break
            }}
        }}
        if ($match -ne $null) {{
            $voice.Voice = $match
            $selectedToken = $match
        }}
    }}

    $null = $voice.Speak($text)
}}
""".strip()


def _voice_for_chunk(
    chunk: str,
    default_voice_name: Optional[str],
    ru_voice_name: Optional[str],
    en_voice_name: Optional[str],
) -> str:
    if re.search(r"[А-Яа-яЁё]", chunk):
        return (ru_voice_name or default_voice_name or "").strip()
    if re.search(r"[A-Za-z]", chunk):
        return (en_voice_name or default_voice_name or "").strip()
    return ""


def _encode_powershell_script(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _creationflags_no_window() -> int:
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _startupinfo_no_window():
    if sys.platform != "win32":
        return None

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo
