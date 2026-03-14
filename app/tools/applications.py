from __future__ import annotations

import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional


APP_COMMANDS = {
    "browser": ["cmd", "/c", "start", "", "chrome"],
    "chrome": ["cmd", "/c", "start", "", "chrome"],
    "vscode": ["code"],
    "telegram": ["Telegram.exe"],
    "notepad": ["notepad.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "explorer": ["explorer.exe"],
}


def open_url(url: Optional[str] = None) -> str:
    """Open a URL in the default browser."""
    if not url:
        return "URL was not provided"

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    webbrowser.open(url)
    return f"Opening URL: {url}"


def open_app(app_name: Optional[str] = None, target: Optional[str] = None) -> str:
    """Open a supported application by name, optionally with a target path."""
    if not app_name:
        return "App name was not provided"

    normalized_name = app_name.strip().lower()
    command = APP_COMMANDS.get(normalized_name)
    if command is None:
        supported = ", ".join(sorted(APP_COMMANDS))
        return f"Unknown app: {app_name}. Supported apps: {supported}"

    executable = command[0]
    if executable.endswith(".exe") and shutil.which(executable) is None and executable not in {"cmd", "cmd.exe"}:
        if normalized_name == "telegram":
            return "Telegram executable was not found in PATH"
        if normalized_name == "vscode":
            return "VS Code executable 'code' was not found in PATH"

    args = command[:]
    if target:
        args.append(str(Path(target).expanduser()))

    subprocess.Popen(args)
    if target:
        return f"Opening {app_name} with target: {target}"
    return f"Opening {app_name}"
