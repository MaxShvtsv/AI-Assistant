from tools.registry import TOOLS_REGISTRY


class ToolExecutionError(Exception):
    """Tool execution exception."""
    pass


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by registry name."""
    if tool_name not in TOOLS_REGISTRY:
        raise ToolExecutionError(f"Unknown tool: {tool_name}")

    tool_func = TOOLS_REGISTRY[tool_name]

    try:
        return tool_func(**args)
    except TypeError as e:
        raise ToolExecutionError(f"Invalid tool arguments: {e}") from e
    except Exception as e:
        raise ToolExecutionError(f"Tool execution failed: {e}") from e
