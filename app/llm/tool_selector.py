from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from llm.ollama_client import OllamaClient
from tools.applications import get_catalog_prompt
from tools.registry import TOOLS_REGISTRY
from tools.schema import TOOLS_SCHEMA


@dataclass
class ToolDecision:
    use_tool: bool
    tool: Optional[str] = None
    args: Optional[dict[str, Any]] = None
    response: Optional[str] = None
    raw_output: Optional[str] = None


TOOL_ACTION_HINTS = (
    "открой",
    "запусти",
    "переключи",
    "перейди",
    "покажи файлы",
    "покажи содержимое",
    "список файлов",
    "создай",
    "создать",
    "удали",
    "скопируй",
    "перемести",
    "переименуй",
    "прочитай файл",
    "запиши",
    "допиши",
    "открой в проводнике",
    "открой приложение",
    "открой сайт",
    "открой вкладку",
    "найди в браузере",
    "youtube music",
    "ютуб мьюзик",
)

CONVERSATION_HINTS = (
    "что такое",
    "кто такой",
    "кто такая",
    "кто ты",
    "что ты",
    "расскажи",
    "объясни",
    "почему",
    "зачем",
    "как работает",
    "как устроен",
    "как устроена",
    "как устроено",
    "что думаешь",
    "как ты думаешь",
    "какие эмоции",
    "что чувствуешь",
    "что ты чувствуешь",
    "умеешь",
    "можешь рассказать",
    "в чем разница",
    "чем отличается",
    "сколько",
)

TOOL_OBJECT_HINTS = (
    "файл",
    "папк",
    "директори",
    "директория",
    "диск",
    "проводник",
    "браузер",
    "вкладк",
    "сайт",
    "приложени",
    "telegram",
    "телеграм",
    "steam",
    "chrome",
    "хром",
    "vscode",
    "код",
    "youtube music",
    "ютуб",
)


class ToolSelector:
    def __init__(self, llm: OllamaClient) -> None:
        self.llm = llm
        self._cached_system_prompt = self._build_system_prompt()

    def decide(self, user_input: str) -> ToolDecision:
        fast_path_decision = self._try_fast_path(user_input)
        if fast_path_decision is not None:
            return fast_path_decision

        conversational_decision = self._try_conversation_fast_path(user_input)
        if conversational_decision is not None:
            return conversational_decision

        raw = self.llm.chat(user_message=user_input, system_prompt=self._cached_system_prompt)

        try:
            data = self._parse_json(raw)
        except Exception:
            return ToolDecision(
                use_tool=False,
                response="Не удалось распознать команду.",
                raw_output=raw,
            )

        use_tool = bool(data.get("use_tool", False))
        tool_name = data.get("tool")
        args = data.get("args", {})

        if not isinstance(args, dict):
            args = {}

        if use_tool and tool_name not in TOOLS_REGISTRY:
            return ToolDecision(
                use_tool=False,
                response="Я не смог подобрать подходящий инструмент.",
                raw_output=raw,
            )

        return ToolDecision(
            use_tool=use_tool,
            tool=tool_name,
            args=args,
            response=data.get("response"),
            raw_output=raw,
        )

    def _build_system_prompt(self) -> str:
        app_catalog_prompt = get_catalog_prompt(limit=80)
        return (
            "Ты локальный помощник по имени Intel.\n"
            "Твоя задача — решить, нужен ли ровно один инструмент для ответа.\n\n"
            "Используй инструмент только если пользователь просит выполнить действие во внешнем мире:\n"
            "- открыть или переключить приложение, сайт, вкладку или проводник\n"
            "- показать содержимое папки или прочитать файл\n"
            "- создать, записать, скопировать, переместить или изменить файл/папку\n"
            "- управлять YouTube Music\n\n"
            "Не используй инструмент, если пользователь:\n"
            "- просит что-то объяснить, рассказать, сравнить или обсудить\n"
            "- задает обычный вопрос\n"
            "- хочет просто пообщаться\n"
            "- спрашивает о твоих возможностях, логике работы или мнении\n\n"
            "Возвращай только валидный JSON.\n"
            "Не используй markdown.\n"
            "Не добавляй пояснения.\n"
            "Не добавляй текст до или после JSON.\n\n"
            "Если нужен инструмент, верни именно такой формат:\n"
            '{"use_tool": true, "tool": "tool_name", "args": {...}}\n\n'
            "Если инструмент не нужен, верни именно такой формат:\n"
            '{"use_tool": false, "response": "короткий ответ на русском"}\n\n'
            "Для tool open_app сначала выбери ровно одно приложение из списка доступных приложений.\n"
            "Не придумывай app_name, которого нет в списке.\n\n"
            f"Доступные приложения для open_app:\n{app_catalog_prompt}\n\n"
            f"Доступные инструменты:\n{json.dumps(TOOLS_SCHEMA, ensure_ascii=False)}"
        )

    def _try_fast_path(self, user_input: str) -> Optional[ToolDecision]:
        normalized = _normalize_text(user_input)
        if not normalized:
            return None

        if any(phrase in normalized for phrase in ("youtube music", "ютуб мьюзик", "ютуб music")):
            return _match_youtube_music_command(normalized)

        if _contains_any(normalized, ("следующ", "вперед")) and "трек" in normalized:
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "next_track"})
        if "предыдущ" in normalized and "трек" in normalized:
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "previous_track"})
        if _contains_any(normalized, ("пауза", "поставь музыку", "останови музыку")):
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "pause"})
        if _contains_any(normalized, ("продолжи музыку", "включи музыку", "запусти музыку")):
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "play"})

        if "переключ" in normalized and "вкладк" in normalized:
            if "следующ" in normalized:
                return ToolDecision(use_tool=True, tool="switch_browser_tab", args={"direction": "next"})
            if "предыдущ" in normalized:
                return ToolDecision(use_tool=True, tool="switch_browser_tab", args={"direction": "previous"})
            number_match = re.search(r"\b(\d+)\b", normalized)
            if number_match:
                return ToolDecision(
                    use_tool=True,
                    tool="switch_browser_tab",
                    args={"index": int(number_match.group(1))},
                )

        app_name = _match_known_app(normalized)
        if app_name:
            return ToolDecision(use_tool=True, tool="open_app", args={"app_name": app_name})

        if _contains_any(normalized, ("открой вкладку", "открой сайт", "открой браузер", "найди в браузере")):
            target = _extract_browser_target(user_input)
            if target:
                if _looks_like_url(target):
                    return ToolDecision(use_tool=True, tool="open_browser_tab", args={"url": target})
                return ToolDecision(use_tool=True, tool="open_browser_tab", args={"query": target})

        if _contains_any(normalized, ("открой в проводнике", "открой проводник", "покажи в проводнике")):
            path = _extract_path_tail(user_input)
            if path:
                return ToolDecision(use_tool=True, tool="open_explorer", args={"path": path})
            return ToolDecision(use_tool=True, tool="open_explorer", args={})

        if _contains_any(normalized, ("покажи файлы", "покажи содержимое", "какие файлы", "список файлов")):
            path = _extract_path_tail(user_input)
            if path:
                return ToolDecision(use_tool=True, tool="list_dir", args={"path": path})

        return None

    def _try_conversation_fast_path(self, user_input: str) -> Optional[ToolDecision]:
        normalized = _normalize_text(user_input)
        if not normalized:
            return None

        if any(hint in normalized for hint in CONVERSATION_HINTS):
            return ToolDecision(use_tool=False)

        if "?" in user_input and not _looks_like_tool_request(normalized):
            return ToolDecision(use_tool=False)

        return None

    def _parse_json(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()

        if raw.startswith("{") and raw.endswith("}"):
            return json.loads(raw)

        if "```json" in raw:
            start = raw.find("```json") + len("```json")
            end = raw.rfind("```")
            json_part = raw[start:end].strip()
            return json.loads(json_part)

        if "```" in raw:
            start = raw.find("```") + len("```")
            end = raw.rfind("```")
            json_part = raw[start:end].strip()
            return json.loads(json_part)

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(raw[start : end + 1])

        raise ValueError("No valid JSON found in LLM response")


def _normalize_text(value: str) -> str:
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"[^a-zа-я0-9\s.:/\\-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _contains_any(text: str, variants: tuple[str, ...]) -> bool:
    return any(variant in text for variant in variants)


def _looks_like_tool_request(normalized: str) -> bool:
    return any(hint in normalized for hint in TOOL_ACTION_HINTS) or any(
        hint in normalized for hint in TOOL_OBJECT_HINTS
    )


def _match_known_app(normalized: str) -> Optional[str]:
    app_aliases = {
        "Telegram": ("телеграм", "telegram"),
        "Visual Studio Code": ("vscode", "vs code", "visual studio code", "код"),
        "Google Chrome": ("chrome", "хром", "браузер"),
        "Steam": ("steam", "стим"),
        "File Explorer": ("проводник",),
    }
    for app_name, aliases in app_aliases.items():
        if _contains_any(normalized, aliases):
            return app_name
    return None


def _extract_browser_target(user_input: str) -> Optional[str]:
    text = user_input.strip()
    patterns = [
        r"(?i)открой (?:новую )?вкладку(?: с сайтом| с поиском)?\s+(.+)$",
        r"(?i)открой сайт\s+(.+)$",
        r"(?i)найди(?: в браузере)?\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" .")
    return None


def _extract_path_tail(user_input: str) -> Optional[str]:
    text = user_input.strip()
    patterns = [
        r"(?i)по такому пути\s+(.+)$",
        r"(?i)путь\s+(.+)$",
        r"(?i)в папке\s+(.+)$",
        r"(?i)на диске\s+(.+)$",
        r"(?i)директори(?:ю|я)?\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" .")
    return None


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "." in value.split()[0]


def _match_youtube_music_command(normalized: str) -> ToolDecision:
    if _contains_any(normalized, ("открой", "запусти")):
        return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "open"})
    if _contains_any(normalized, ("найди", "ищи")):
        query = _extract_after_keywords(normalized, ("найди", "ищи"))
        if query:
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "search", "query": query})
    if _contains_any(normalized, ("включи", "пусти", "поставь")):
        query = _extract_after_keywords(normalized, ("включи", "пусти", "поставь"))
        if query and "пауз" not in query and "музык" not in query:
            return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "play_song", "query": query})
    if "пауз" in normalized:
        return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "pause"})
    return ToolDecision(use_tool=True, tool="youtube_music_control", args={"action": "play_pause"})


def _extract_after_keywords(text: str, keywords: tuple[str, ...]) -> Optional[str]:
    for keyword in keywords:
        if keyword in text:
            tail = text.split(keyword, 1)[1].strip(" .")
            tail = re.sub(r"(?i)\bв youtube music\b", "", tail).strip(" .")
            tail = re.sub(r"(?i)\bв ютуб мьюзик\b", "", tail).strip(" .")
            if tail:
                return tail
    return None
