import importlib
import sys
from pathlib import Path


sys.path.insert(0, "app")

applications = importlib.import_module("tools.applications")


def test_resolve_app_executable_supports_known_alias_candidates() -> None:
    candidates = applications.APP_ALIASES["telegram"]

    assert "telegram.exe" in [candidate.lower() for candidate in candidates]


def test_resolve_app_match_returns_none_for_unknown_app() -> None:
    match = applications.resolve_app_match("totally_unknown_app")

    assert match is None


def test_steam_alias_is_present() -> None:
    candidates = applications.APP_ALIASES["steam"]

    assert "steam.exe" in [candidate.lower() for candidate in candidates]
