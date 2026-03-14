import importlib
import sys
from pathlib import Path


sys.path.insert(0, "app")

file_system = importlib.import_module("tools.file_system")


def test_list_dir_returns_folders_and_files(tmp_path: Path) -> None:
    (tmp_path / "folder_a").mkdir(exist_ok=True)
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")

    result = file_system.list_dir(str(tmp_path))

    assert "Folders:" in result
    assert "- folder_a" in result
    assert "Files:" in result
    assert "- note.txt" in result


def test_write_and_read_text_file(tmp_path: Path) -> None:
    target = tmp_path / "memo.txt"

    write_result = file_system.write_text_file(str(target), "hello")
    read_result = file_system.read_text_file(str(target))

    assert "File saved:" in write_result
    assert "hello" in read_result


def test_append_text_file(tmp_path: Path) -> None:
    target = tmp_path / "memo.txt"

    file_system.write_text_file(str(target), "hello")
    file_system.append_text_file(str(target), "\nworld")
    read_result = file_system.read_text_file(str(target))

    assert "world" in read_result


def test_resolve_path_supports_drive_aliases() -> None:
    drive_c = file_system._resolve_path("диск c")
    drive_d = file_system._resolve_path("D:")

    assert str(drive_c).lower().startswith("c:")
    assert str(drive_d).lower().startswith("d:")


def test_resolve_path_supports_spoken_drive_paths() -> None:
    spoken_path = file_system._resolve_path("D, Games")
    russian_spoken_path = file_system._resolve_path("диск d steam")

    assert str(spoken_path).lower().startswith("d:\\games")
    assert str(russian_spoken_path).lower().startswith("d:\\steam")
