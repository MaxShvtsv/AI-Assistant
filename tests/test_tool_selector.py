import importlib
import sys
import types


sys.path.insert(0, "app")

ollama_stub = types.ModuleType("ollama")


class DummyClient:
    def __init__(self, *args, **kwargs) -> None:
        pass


ollama_stub.Client = DummyClient
sys.modules.setdefault("ollama", ollama_stub)

tool_selector_module = importlib.import_module("llm.tool_selector")
ToolSelector = tool_selector_module.ToolSelector


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def chat(self, user_message: str, system_prompt: str | None = None) -> str:
        return self.response


def test_tool_selector_rejects_unknown_tool() -> None:
    selector = ToolSelector(FakeLLM('{"use_tool": true, "tool": "unknown_tool", "args": {}}'))

    decision = selector.decide("открой что-нибудь")

    assert decision.use_tool is False
    assert decision.tool is None or decision.tool == "unknown_tool"
    assert decision.response is not None


def test_tool_selector_parses_json_from_code_block() -> None:
    selector = ToolSelector(
        FakeLLM(
            "```json\n"
            '{"use_tool": false, "response": "готово"}\n'
            "```"
        )
    )

    decision = selector.decide("привет")

    assert decision.use_tool is False
    assert decision.response == "готово"
