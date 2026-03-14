from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Optional

import requests

from tools.applications import resolve_app_match


CHROME_APP_NAME = "Google Chrome"
YOUTUBE_MUSIC_URL = "https://music.youtube.com"
CHROME_DEVTOOLS_PORT = 9222
DEVTOOLS_SESSION = requests.Session()


def open_browser_tab(url: Optional[str] = None, query: Optional[str] = None) -> str:
    """Open a new Chrome tab with a URL or a Google search query."""
    if not url and not query:
        return "URL or search query was not provided"

    target = url or _build_google_search_url(query or "")
    target = _normalize_url(target)
    _launch_chrome(["--new-tab", target])
    return f"Opening Chrome tab: {target}"


def switch_browser_tab(
    direction: Optional[str] = None,
    index: Optional[int] = None,
    title_contains: Optional[str] = None,
) -> str:
    """Switch Chrome tab by direction, numeric index, or partial title."""
    if title_contains:
        activated = _activate_tab_by_title(title_contains)
        if activated:
            return f"Switched to Chrome tab matching: {title_contains}"

    _activate_chrome_window()

    if index is not None:
        normalized_index = max(1, min(9, int(index)))
        _send_keys(f"^{normalized_index}")
        return f"Switched to Chrome tab #{normalized_index}"

    normalized_direction = (direction or "next").strip().lower()
    if normalized_direction in {"previous", "prev", "back", "left"}:
        _send_keys("^+{TAB}")
        return "Switched to previous Chrome tab"

    _send_keys("^{TAB}")
    return "Switched to next Chrome tab"


def youtube_music_control(action: str, query: Optional[str] = None) -> str:
    """Control YouTube Music in Chrome."""
    normalized_action = action.strip().lower()

    if normalized_action == "open":
        _launch_chrome(["--new-tab", YOUTUBE_MUSIC_URL])
        return "Opening YouTube Music"

    if normalized_action == "search":
        if not query:
            return "Search query was not provided"
        search_url = _build_youtube_music_search_url(query)
        _launch_chrome(["--new-tab", search_url])
        return f"Opening YouTube Music search for: {query}"

    _ensure_youtube_music_ready()

    if normalized_action == "play_pause":
        _send_media_key("play_pause")
        return "Toggling playback in YouTube Music"

    if normalized_action == "next_track":
        _send_media_key("next_track")
        return "Switching to the next track in YouTube Music"

    if normalized_action == "previous_track":
        _send_media_key("previous_track")
        return "Switching to the previous track in YouTube Music"

    if normalized_action == "play":
        _inject_youtube_music_command(_build_play_pause_js("play"))
        return "Trying to start playback in YouTube Music"

    if normalized_action == "pause":
        _inject_youtube_music_command(_build_play_pause_js("pause"))
        return "Trying to pause playback in YouTube Music"

    if normalized_action == "play_song":
        if not query:
            return "Song name was not provided"

        search_url = _build_youtube_music_search_url(query)
        _navigate_active_chrome_tab(search_url)
        time.sleep(2.0)
        _inject_youtube_music_command(_build_first_result_play_js())
        return f"Trying to play '{query}' in YouTube Music"

    return f"Unsupported YouTube Music action: {action}"


def _build_google_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query.strip())


def _build_youtube_music_search_url(query: str) -> str:
    return YOUTUBE_MUSIC_URL + "/search?q=" + urllib.parse.quote_plus(query.strip())


def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if cleaned.startswith(("http://", "https://", "javascript:")):
        return cleaned
    return "https://" + cleaned


def _launch_chrome(arguments: list[str]) -> None:
    chrome_path = _get_chrome_path()
    subprocess.Popen([chrome_path, *arguments])


@lru_cache(maxsize=1)
def _get_chrome_path() -> str:
    chrome_entry = resolve_app_match(CHROME_APP_NAME) or resolve_app_match("chrome")
    if chrome_entry is None:
        raise RuntimeError("Google Chrome was not found")
    return str(Path(chrome_entry.executable_path))


def _activate_chrome_window() -> None:
    script = r"""
$wshell = New-Object -ComObject WScript.Shell
$activated = $wshell.AppActivate('Google Chrome')
if (-not $activated) {
    $activated = $wshell.AppActivate('Chrome')
}
if (-not $activated) {
    throw 'Google Chrome window was not found'
}
"""
    _run_powershell(script)


def _send_keys(keys: str, delay_ms: int = 120) -> None:
    script = rf"""
$wshell = New-Object -ComObject WScript.Shell
$activated = $wshell.AppActivate('Google Chrome')
if (-not $activated) {{
    $activated = $wshell.AppActivate('Chrome')
}}
if (-not $activated) {{
    throw 'Google Chrome window was not found'
}}
Start-Sleep -Milliseconds {delay_ms}
$wshell.SendKeys('{keys}')
"""
    _run_powershell(script)


def _set_clipboard(text: str) -> None:
    escaped = text.replace("'", "''")
    script = f"Set-Clipboard -Value '{escaped}'"
    _run_powershell(script)


def _navigate_active_chrome_tab(url: str) -> None:
    _activate_chrome_window()
    _set_clipboard(url)
    _send_keys("^l")
    time.sleep(0.08)
    _send_keys("^v")
    time.sleep(0.08)
    _send_keys("{ENTER}")


def _inject_youtube_music_command(js_code: str) -> None:
    javascript_url = "javascript:" + js_code
    _navigate_active_chrome_tab(javascript_url)


def _ensure_youtube_music_ready() -> None:
    activated = _activate_tab_by_title("YouTube Music")
    if activated:
        return

    _launch_chrome(["--new-tab", YOUTUBE_MUSIC_URL])
    time.sleep(1.5)
    _activate_chrome_window()


def _activate_tab_by_title(title_contains: str) -> bool:
    tab = _find_devtools_tab_by_title(title_contains)
    if tab is None:
        return False

    DEVTOOLS_SESSION.get(
        f"http://127.0.0.1:{CHROME_DEVTOOLS_PORT}/json/activate/{tab['id']}",
        timeout=1.5,
    )
    return True


def _find_devtools_tab_by_title(title_contains: str) -> Optional[dict]:
    try:
        response = DEVTOOLS_SESSION.get(
            f"http://127.0.0.1:{CHROME_DEVTOOLS_PORT}/json/list",
            timeout=1.5,
        )
        response.raise_for_status()
    except Exception:
        return None

    needle = title_contains.strip().lower()
    for tab in response.json():
        title = str(tab.get("title", "")).lower()
        if needle and needle in title:
            return tab
    return None


def _send_media_key(action: str) -> None:
    media_key_map = {
        "play_pause": 0xB3,
        "next_track": 0xB0,
        "previous_track": 0xB1,
    }
    if action not in media_key_map:
        raise RuntimeError(f"Unsupported media key action: {action}")

    vk = media_key_map[action]
    script = rf"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class KeyboardInput {{
    [DllImport("user32.dll", SetLastError=true)]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
}}
"@
[KeyboardInput]::keybd_event({vk}, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
[KeyboardInput]::keybd_event({vk}, 0, 2, [UIntPtr]::Zero)
"""
    _run_powershell(script)


def _build_play_pause_js(action: str) -> str:
    expected_state = json.dumps(action)
    return (
        "(() => {"
        "const button = document.querySelector('ytmusic-player-bar tp-yt-paper-icon-button.play-pause-button');"
        "if (!button) { return; }"
        "const label = (button.getAttribute('aria-label') || button.getAttribute('title') || '').toLowerCase();"
        f"const desired = {expected_state};"
        "const wantsPlay = desired === 'play';"
        "const isPlayButton = label.includes('play') || label.includes('воспроиз') || label.includes('resume');"
        "const isPauseButton = label.includes('pause') || label.includes('пауза');"
        "if ((wantsPlay && isPlayButton) || (!wantsPlay && isPauseButton)) { button.click(); return; }"
        "if (!label) { button.click(); }"
        "})()"
    )


def _build_first_result_play_js() -> str:
    return (
        "(() => {"
        "const selectors = ["
        "'ytmusic-responsive-list-item-renderer ytmusic-play-button-renderer button',"
        "'ytmusic-shelf-renderer ytmusic-play-button-renderer button',"
        "'ytmusic-two-row-item-renderer ytmusic-play-button-renderer button',"
        "'ytmusic-carousel-shelf-renderer ytmusic-play-button-renderer button'"
        "];"
        "for (const selector of selectors) {"
        "  const button = document.querySelector(selector);"
        "  if (button) { button.click(); return; }"
        "}"
        "})();"
    )


def _run_powershell(script: str) -> None:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        check=False,
        creationflags=_creationflags_no_window(),
        startupinfo=_startupinfo_no_window(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(stderr or f"PowerShell command failed with code {completed.returncode}")


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
