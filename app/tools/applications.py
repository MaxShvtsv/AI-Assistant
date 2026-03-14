from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None


APP_ALIASES = {
    "browser": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "steam": ["steam.exe", "Steam.exe"],
    "vscode": ["code.exe", "Code.exe"],
    "telegram": ["telegram.exe", "Telegram.exe"],
    "notepad": ["notepad.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "explorer": ["explorer.exe"],
}

STATIC_APP_PATHS = {
    "steam": Path(r"D:\Program Files\Steam\steam.exe"),
    "telegram": Path(r"D:\Program Files\Telegram Desktop\Telegram.exe"),
}

APP_PATHS_REGISTRY_PATHS = [
    (getattr(winreg, "HKEY_CURRENT_USER", None), r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
    (getattr(winreg, "HKEY_LOCAL_MACHINE", None), r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
]


@dataclass(frozen=True)
class AppEntry:
    display_name: str
    executable_path: str
    aliases: tuple[str, ...] = ()


def open_url(url: Optional[str] = None) -> str:
    """Open a URL in the default browser."""
    if not url:
        return "URL was not provided"

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    webbrowser.open(url)
    return f"Opening URL: {url}"


def open_app(app_name: Optional[str] = None, target: Optional[str] = None) -> str:
    """Open a desktop application by exact catalog name or known alias."""
    if not app_name:
        return "App name was not provided"

    normalized_name = _normalize_app_name(app_name)
    if normalized_name == "browser" and target and target.startswith(("http://", "https://")):
        webbrowser.open(target)
        return f"Opening browser with target: {target}"

    app_entry = resolve_app_match(app_name)
    if app_entry is None:
        supported = get_catalog_prompt(limit=40)
        return f"Could not find app: {app_name}. Available apps sample: {supported}"

    _launch_app(app_entry.executable_path, target)
    if target:
        return f"Opening {app_entry.display_name} with target: {target}"
    return f"Opening {app_entry.display_name}"


def list_available_apps(limit: int = 80) -> str:
    """Return a compact list of launchable applications discovered on the system."""
    entries = get_installed_app_catalog()
    if not entries:
        return "No launchable applications were discovered."

    names = [entry.display_name for entry in entries[:limit]]
    return "Available apps:\n" + "\n".join(f"- {name}" for name in names)


def resolve_app_match(app_name: str) -> Optional[AppEntry]:
    normalized_name = _normalize_app_name(app_name)
    entries = get_installed_app_catalog()

    exact_matches = []
    for entry in entries:
        candidate_names = {entry.display_name, *entry.aliases}
        normalized_candidates = {_normalize_app_name(value) for value in candidate_names if value}
        if normalized_name in normalized_candidates:
            exact_matches.append(entry)

    if len(exact_matches) == 1:
        return exact_matches[0]

    contains_matches = []
    for entry in entries:
        candidate_names = {entry.display_name, *entry.aliases}
        normalized_candidates = {_normalize_app_name(value) for value in candidate_names if value}
        if any(normalized_name and normalized_name in candidate for candidate in normalized_candidates):
            contains_matches.append(entry)

    if len(contains_matches) == 1:
        return contains_matches[0]

    return None


@lru_cache(maxsize=1)
def get_installed_app_catalog() -> list[AppEntry]:
    entries: dict[str, AppEntry] = {}

    for entry in _iter_app_paths_registry_entries():
        _merge_entry(entries, entry)

    for alias_name, candidates in APP_ALIASES.items():
        for candidate in candidates:
            executable_path = _resolve_candidate_executable(candidate)
            if executable_path is None:
                continue
            pretty_name = _pretty_name_from_alias(alias_name)
            _merge_entry(
                entries,
                AppEntry(
                    display_name=pretty_name,
                    executable_path=str(executable_path),
                    aliases=(alias_name, candidate, executable_path.name),
                ),
            )

    return sorted(entries.values(), key=lambda entry: entry.display_name.lower())


def get_catalog_prompt(limit: int = 80) -> str:
    entries = get_installed_app_catalog()
    if not entries:
        return "No apps discovered"
    return ", ".join(entry.display_name for entry in entries[:limit])

def _merge_entry(entries: dict[str, AppEntry], new_entry: AppEntry) -> None:
    key = _normalize_app_name(new_entry.display_name)
    if key in entries:
        existing = entries[key]
        merged_aliases = tuple(sorted({*existing.aliases, *new_entry.aliases}))
        preferred_path = existing.executable_path if Path(existing.executable_path).exists() else new_entry.executable_path
        entries[key] = AppEntry(
            display_name=existing.display_name,
            executable_path=preferred_path,
            aliases=merged_aliases,
        )
        return

    entries[key] = new_entry


def _iter_app_paths_registry_entries() -> Iterable[AppEntry]:
    if winreg is None:
        return []

    discovered: list[AppEntry] = []
    for root, key_path in APP_PATHS_REGISTRY_PATHS:
        if root is None:
            continue
        try:
            with winreg.OpenKey(root, key_path) as base_key:
                subkey_count = winreg.QueryInfoKey(base_key)[0]
                for index in range(subkey_count):
                    subkey_name = winreg.EnumKey(base_key, index)
                    try:
                        with winreg.OpenKey(base_key, subkey_name) as app_key:
                            executable_path, _ = winreg.QueryValueEx(app_key, None)
                    except OSError:
                        continue

                    if not executable_path or not os.path.exists(executable_path):
                        continue

                    display_name = Path(subkey_name).stem
                    discovered.append(
                        AppEntry(
                            display_name=display_name,
                            executable_path=executable_path,
                            aliases=(subkey_name,),
                        )
                    )
        except OSError:
            continue

    return discovered


def _resolve_candidate_executable(candidate: str) -> Optional[Path]:
    static_match = STATIC_APP_PATHS.get(candidate.lower().replace(".exe", ""))
    if static_match is not None and static_match.exists():
        return static_match

    registry_match = _find_from_registry(candidate)
    if registry_match is not None:
        return registry_match

    in_path = shutil.which(candidate)
    if in_path:
        return Path(in_path)

    return None


def _find_from_registry(executable_name: str) -> Optional[Path]:
    if winreg is None:
        return None

    for root, base_key in APP_PATHS_REGISTRY_PATHS:
        if root is None:
            continue
        try:
            with winreg.OpenKey(root, fr"{base_key}\{executable_name}") as key:
                value, _ = winreg.QueryValueEx(key, None)
                if value and os.path.exists(value):
                    return Path(value)
        except OSError:
            continue

    return None


def _pretty_name_from_alias(alias_name: str) -> str:
    pretty_names = {
        "browser": "Browser",
        "chrome": "Google Chrome",
        "edge": "Microsoft Edge",
        "firefox": "Mozilla Firefox",
        "vscode": "Visual Studio Code",
        "telegram": "Telegram",
        "notepad": "Notepad",
        "powershell": "PowerShell",
        "cmd": "Command Prompt",
        "explorer": "File Explorer",
    }
    return pretty_names.get(alias_name, alias_name.title())


def _normalize_app_name(value: str) -> str:
    return " ".join(
        value.strip()
        .lower()
        .replace(".exe", "")
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def _launch_app(executable_path: str, target: Optional[str]) -> None:
    executable = str(Path(executable_path))
    expanded_target = str(Path(target).expanduser()) if target else None

    if os.name == "nt":
        if expanded_target:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", executable, expanded_target],
                shell=False,
            )
            return

        os.startfile(executable)
        return

    command = [executable]
    if expanded_target:
        command.append(expanded_target)
    subprocess.Popen(command)
