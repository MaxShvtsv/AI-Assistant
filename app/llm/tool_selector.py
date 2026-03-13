import json
from dataclasses import dataclass
from typing import Any, Optional

from llm.ollama_client import OllamaClient
from tools.registry import TOOLS_REGISTRY
from tools.schema import TOOLS_SCHEMA


@dataclass
class ToolDecision:
    use_tool: bool
    tool: Optional[str] = None
    args: Optional[dict[str, Any]] = None
    response: Optional[str] = None
    raw_output: Optional[str] = None


class ToolSelector:
    def __init__(self, llm: OllamaClient) -> None:
        self.llm = llm

    def decide(self, user_input: str) -> ToolDecision:
        system_prompt = self._build_system_prompt()
        raw = self.llm.chat(user_message=user_input, system_prompt=system_prompt)

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
        return (
            "Ты локальный помощник под названием Intel.\n"
            "Твоя задача - решить, нужно ли использовать один из доступных инструментов.\n\n"
            "Возвращай только валидный JSON.\n"
            "Не используй markdown.\n"
            "Не добавляй пояснения.\n"
            "Не добавляй текст до или после JSON.\n\n"
            "Если нужен инструмент, верни именно такой формат:\n"
            '{"use_tool": true, "tool": "tool_name", "args": {...}}\n\n'
            "Если инструмент не нужен, верни именно такой формат:\n"
            '{"use_tool": false, "response": "короткий ответ на русском"}\n\n'
            f"Доступные инструменты:\n{json.dumps(TOOLS_SCHEMA, ensure_ascii=False)}"
        )

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
            return json.loads(raw[start:end + 1])

        raise ValueError("No valid JSON found in LLM response")
