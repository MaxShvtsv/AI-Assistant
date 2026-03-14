from __future__ import annotations

import re

from llm.ollama_client import OllamaClient, OllamaConfig
from llm.tool_selector import ToolSelector
from tools.executor import ToolExecutionError, execute_tool


RAW_TOOL_RESPONSE_TOOLS = {
    "list_dir",
    "read_text_file",
}


class AssistantService:
    def __init__(self) -> None:
        self.llm = OllamaClient(
            OllamaConfig(
                model="gemma3",
                system_prompt="Тебя зовут Intel, ты локальный голосовой ассистент.",
            )
        )
        self.selector = ToolSelector(self.llm)

    def handle_text(self, user_input: str) -> str:
        decision = self.selector.decide(user_input)

        if not decision.use_tool:
            return decision.response or "Я не понял сообщение."

        try:
            tool_result = execute_tool(decision.tool, decision.args or {})
            if decision.tool in RAW_TOOL_RESPONSE_TOOLS:
                return tool_result
            return self._format_tool_reply(decision.tool or "", tool_result)
        except ToolExecutionError as exc:
            return f"Ошибка инструмента: {exc}"

    def _format_tool_reply(self, tool_name: str, tool_result: str) -> str:
        cleaned = (tool_result or "").strip()
        if not cleaned:
            return "Готово."

        direct_mappings = {
            "open_explorer": "Открываю проводник.",
            "open_url": "Открываю сайт.",
            "open_app": "Открываю приложение.",
            "open_browser_tab": "Открываю вкладку.",
            "switch_browser_tab": "Переключаю вкладку.",
        }
        if tool_name in direct_mappings:
            return direct_mappings[tool_name]

        if tool_name == "youtube_music_control":
            return _humanize_youtube_music_result(cleaned)

        replacements = [
            (r"^Folder created:\s*(.+)$", r'Папка создана: \1'),
            (r"^File saved:\s*(.+)$", r'Файл сохранен: \1'),
            (r"^Text appended to file:\s*(.+)$", r'Текст добавлен в файл: \1'),
            (r"^Copied to:\s*(.+)$", r'Скопировано: \1'),
            (r"^Moved to:\s*(.+)$", r'Перемещено: \1'),
            (r"^Opening Explorer at\s+(.+)$", r'Открываю проводник: \1'),
            (r"^Opening File Explorer$", 'Открываю проводник.'),
            (r"^Opening Chrome tab:\s*(.+)$", r'Открываю вкладку: \1'),
            (r"^Opening URL:\s*(.+)$", r'Открываю сайт: \1'),
            (r"^Opening (.+) with target:\s*(.+)$", r'Открываю \1: \2'),
            (r"^Opening (.+)$", r'Открываю \1.'),
        ]
        for pattern, replacement in replacements:
            if re.match(pattern, cleaned, flags=re.IGNORECASE):
                return re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        if cleaned.startswith(("Path does not exist:", "Source path does not exist:")):
            return "Путь не найден."
        if cleaned.startswith("Provided path is not a directory:"):
            return "Указанный путь не является папкой."
        if cleaned.startswith("Provided path is not a file:"):
            return "Указанный путь не является файлом."
        if cleaned.startswith("Could not find app:"):
            return "Не удалось найти приложение."

        return cleaned


def _humanize_youtube_music_result(result: str) -> str:
    normalized = result.lower()
    if "opening youtube music search for:" in normalized:
        query = result.split(":", 1)[-1].strip()
        return f"Ищу в YouTube Music: {query}"
    if "trying to play" in normalized:
        query = result.split("'", 2)[1] if "'" in result else result
        return f"Пробую включить: {query}"
    if "opening youtube music" in normalized:
        return "Открываю YouTube Music."
    if "toggling playback" in normalized:
        return "Переключаю воспроизведение."
    if "next track" in normalized:
        return "Включаю следующий трек."
    if "previous track" in normalized:
        return "Включаю предыдущий трек."
    if "pause playback" in normalized:
        return "Ставлю музыку на паузу."
    if "start playback" in normalized:
        return "Запускаю воспроизведение."
    return result
