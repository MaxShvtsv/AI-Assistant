from tools.applications import list_available_apps, open_app, open_url
from tools.browser import open_browser_tab, switch_browser_tab, youtube_music_control
from tools.file_system import (
    append_text_file,
    copy_path,
    create_folder,
    list_dir,
    move_path,
    open_explorer,
    read_text_file,
    write_text_file,
)

TOOLS_REGISTRY = {
    "open_explorer": open_explorer,
    "list_dir": list_dir,
    "create_folder": create_folder,
    "read_text_file": read_text_file,
    "write_text_file": write_text_file,
    "append_text_file": append_text_file,
    "copy_path": copy_path,
    "move_path": move_path,
    "open_url": open_url,
    "open_app": open_app,
    "list_available_apps": list_available_apps,
    "open_browser_tab": open_browser_tab,
    "switch_browser_tab": switch_browser_tab,
    "youtube_music_control": youtube_music_control,
}
