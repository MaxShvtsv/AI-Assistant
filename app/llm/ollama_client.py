from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ollama import Client


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "gemma3"
    system_prompt: Optional[str] = None
    keep_alive: str = "30m"
    options: dict[str, Any] = field(default_factory=lambda: {"temperature": 0})


class OllamaClient:
    def __init__(self, config: OllamaConfig) -> None:
        self.config = config
        self.client = Client(host=config.host)

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> str:
        messages = []

        effective_system_prompt = system_prompt or self.config.system_prompt
        if effective_system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": effective_system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        effective_options = dict(self.config.options)
        if options:
            effective_options.update(options)

        response = self.client.chat(
            model=self.config.model,
            messages=messages,
            keep_alive=self.config.keep_alive,
            options=effective_options,
        )

        return response["message"]["content"].strip()
