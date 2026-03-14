import importlib
import sys


sys.path.insert(0, "app")

applications = importlib.import_module("tools.applications")


def test_normalize_app_name_removes_exe_suffix() -> None:
    assert applications._normalize_app_name("Telegram.exe") == "telegram"


def test_catalog_prompt_returns_string() -> None:
    prompt = applications.get_catalog_prompt(limit=5)

    assert isinstance(prompt, str)
