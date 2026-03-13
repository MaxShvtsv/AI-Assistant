import json
from dataclasses import dataclass
from typing import Any, Optional

from tools.schema import TOOLS_SCHEMA
from llm.ollama_client import OllamaClient


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
                response="Could not regognize the command",
                raw_output=raw,
            )

        return ToolDecision(
            use_tool=data.get("use_tool", False),
            tool=data.get("tool"),
            args=data.get("args", {}),
            response=data.get("response"),
            raw_output=raw,
        )

    def _build_system_prompt(self) -> str:
        return (
            "Ты - локальный помощник под названием Intel.\n"
            "Твоя задача — решить, требует ли запрос пользователя использования одного из доступных инструментов.\n\n"
            "Возвращай только валидный JSON.\n"
            "Не используй markdown.\n"
            "Не добавляй пояснения.\n"
            "Не добавляй текст до или после JSON.\n\n"
            "Если необходимо использовать инструмент, возвращай именно этот формат:\n"
            '{"use_tool": true, "tool": "tool_name", "args": {...}}\n\n'
            "Если инструмент не должен использоваться, верни именно этот формат:\n"
            '{"use_tool": false, "response": "short reply in Russian"}\n\n'
            f"Доступные инструменты:\n{json.dumps(TOOLS_SCHEMA, ensure_ascii=False)}"
        )

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()

        # Clear JSON
        if raw.startswith("{") and raw.endswith("}"):
            return json.loads(raw)

        # Created JSON
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

        # Fallback
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(raw[start:end + 1])

        raise ValueError("No valid JSON found in LLM response")
