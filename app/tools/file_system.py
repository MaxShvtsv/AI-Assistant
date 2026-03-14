from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def open_explorer(path: Optional[str] = None) -> str:
    """Open Windows Explorer. If path is provided, open that location."""
    if path:
        target = _resolve_path(path)
        if not target.exists():
            return f"Path does not exist: {target}"

        subprocess.Popen(["explorer.exe", str(target)])
        return f"Opening Explorer at {target}"

    subprocess.Popen(["explorer.exe"])
    return "Opening File Explorer"


def list_dir(path: Optional[str] = None) -> str:
    """Return a structured list of files and folders for a given path."""
    if not path:
        return "Path was not provided"

    target = _resolve_path(path)

    if not target.exists():
        return f"Path does not exist: {target}"

    if not target.is_dir():
        return f"Provided path is not a directory: {target}"

    entries = sorted(target.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    if not entries:
        return f"Directory is empty: {target}"

    folders = [entry.name for entry in entries if entry.is_dir()][:50]
    files = [entry.name for entry in entries if entry.is_file()][:50]

    parts = [f"Directory: {target}"]
    if folders:
        parts.append("Folders:")
        parts.extend(f"- {name}" for name in folders)
    if files:
        parts.append("Files:")
        parts.extend(f"- {name}" for name in files)

    return "\n".join(parts)


def create_folder(path: Optional[str] = None, folder_name: Optional[str] = None) -> str:
    """Create a folder inside the provided directory path."""
    if not path:
        return "Path was not provided"

    if not folder_name:
        return "Folder name was not provided"

    parent = _resolve_path(path)

    if not parent.exists():
        return f"Path does not exist: {parent}"

    if not parent.is_dir():
        return f"Provided path is not a directory: {parent}"

    new_folder_path = parent / folder_name
    new_folder_path.mkdir(exist_ok=True)

    return f"Folder created: {new_folder_path}"


def read_text_file(path: Optional[str] = None, max_chars: int = 4000) -> str:
    """Read a UTF-8 text file and return a bounded preview."""
    if not path:
        return "Path was not provided"

    target = _resolve_path(path)
    if not target.exists():
        return f"Path does not exist: {target}"
    if not target.is_file():
        return f"Provided path is not a file: {target}"

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = target.read_text(encoding="utf-8", errors="replace")

    if len(content) > max_chars:
        content = content[:max_chars] + "\n...[truncated]"

    return f"File: {target}\n{content}"


def write_text_file(path: Optional[str] = None, content: Optional[str] = None, overwrite: bool = True) -> str:
    """Create or overwrite a text file."""
    if not path:
        return "Path was not provided"
    if content is None:
        return "Content was not provided"

    target = _resolve_path(path)
    if target.exists() and target.is_dir():
        return f"Provided path is a directory: {target}"
    if target.exists() and not overwrite:
        return f"File already exists: {target}"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"File saved: {target}"


def append_text_file(path: Optional[str] = None, content: Optional[str] = None) -> str:
    """Append text to a file, creating it if needed."""
    if not path:
        return "Path was not provided"
    if content is None:
        return "Content was not provided"

    target = _resolve_path(path)
    if target.exists() and target.is_dir():
        return f"Provided path is a directory: {target}"

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as file:
        file.write(content)
    return f"Text appended to file: {target}"


def copy_path(source_path: Optional[str] = None, destination_path: Optional[str] = None) -> str:
    """Copy a file or folder to a new location."""
    if not source_path:
        return "Source path was not provided"
    if not destination_path:
        return "Destination path was not provided"

    source = _resolve_path(source_path)
    destination = _resolve_path(destination_path)

    if not source.exists():
        return f"Source path does not exist: {source}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)

    return f"Copied to: {destination}"


def move_path(source_path: Optional[str] = None, destination_path: Optional[str] = None) -> str:
    """Move or rename a file or folder."""
    if not source_path:
        return "Source path was not provided"
    if not destination_path:
        return "Destination path was not provided"

    source = _resolve_path(source_path)
    destination = _resolve_path(destination_path)

    if not source.exists():
        return f"Source path does not exist: {source}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return f"Moved to: {destination}"


def _resolve_path(path: str) -> Path:
    raw_path = path.strip().strip("\"'")

    spoken_drive_path = _try_parse_spoken_drive_path(raw_path)
    if spoken_drive_path is not None:
        return spoken_drive_path

    normalized_drive = _try_parse_drive_path(raw_path)
    if normalized_drive is not None:
        return normalized_drive

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return candidate.resolve()


def _try_parse_drive_path(path: str) -> Optional[Path]:
    cleaned = path.strip().strip("\"'")
    match = re.fullmatch(r"(?i)(?:disk|drive|диск)?\s*([a-z])\s*:?\s*", cleaned)
    if not match:
        return None

    drive_letter = match.group(1).upper()
    return Path(f"{drive_letter}:\\")


def _try_parse_spoken_drive_path(path: str) -> Optional[Path]:
    cleaned = path.strip().strip("\"'")
    match = re.fullmatch(
        r"(?is)(?:disk|drive|диск)?\s*([a-z])\s*[:,]?\s+(.+?)\s*",
        cleaned,
    )
    if not match:
        return None

    drive_letter = match.group(1).upper()
    tail = match.group(2).strip()
    if not tail:
        return Path(f"{drive_letter}:\\")

    parts = [segment.strip(" .,:;\\/") for segment in re.split(r"[\\/,\n]+", tail)]
    normalized_parts = [part for part in parts if part]
    if not normalized_parts:
        return Path(f"{drive_letter}:\\")

    return Path(f"{drive_letter}:\\", *normalized_parts)
