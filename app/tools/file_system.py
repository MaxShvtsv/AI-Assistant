from typing import Optional
import subprocess
from pathlib import Path

def open_explorer(path: Optional[str] = None) -> str:
    """Open Windows Explorer. If path is provided, open that location."""
    if path:
        p = Path(path)
        if not p.exists():
            return "Given path does not exists"

        subprocess.Popen(["explorer", str(p)])
        return f"Opening Explorer at {path}"

    subprocess.Popen(["explorer"])
    return "Opening File Exporer"


def list_dir(path: Optional[str] = None) -> str:
    """Return a list of files and folders for a given path."""
    if not path:
        return "Path was not provided"

    p = Path(path)

    if not p.exists():
        return "Path does not exist"

    if not p.is_dir():
        return "Provided path is not a directory"

    objects = [obj.name for obj in p.iterdir()]

    if not objects:
        return "Directory is empty"

    return "Directory contains:\n" + "\n".join(objects[:50])


def create_folder(path: Optional[str] = None, folder_name: Optional[str] = None) -> str:
    """Create a folder inside the provided directory path."""
    if not path:
        return "Path was not provided"

    if not folder_name:
        return "Folder name was not provided"

    p = Path(path)

    if not p.exists():
        return "Path does not exist"

    if not p.is_dir():
        return "Provided path is not a directory"

    new_folder_path = p / folder_name
    new_folder_path.mkdir(exist_ok=True)

    return f"Folder created: {new_folder_path}"
