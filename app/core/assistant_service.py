from llm.ollama_client import OllamaClient, OllamaConfig
from llm.tool_selector import ToolSelector
from tools.executor import ToolExecutionError, execute_tool


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
            return self._format_tool_reply(user_input, decision.tool, tool_result)
        except ToolExecutionError as exc:
            return f"Ошибка инструмента: {exc}"

    def _format_tool_reply(self, user_input: str, tool_name: str, tool_result: str) -> str:
        prompt = (
            "Ты локальный голосовой ассистент.\n"
            "Отвечай кратко, естественно и на русском языке.\n\n"
            f"Запрос пользователя: {user_input}\n"
            f"Использованный инструмент: {tool_name}\n"
            f"Результат инструмента: {tool_result}"
        )
        return self.llm.chat(prompt)
