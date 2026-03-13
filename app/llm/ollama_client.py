from dataclasses import dataclass
from typing import Optional

from ollama import Client


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "gemma3"
    system_prompt: Optional[str] = None


class OllamaClient:
    def __init__(self, config: OllamaConfig) -> None:
        self.config = config
        self.client = Client(host=config.host)

    def chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
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

        response = self.client.chat(
            model=self.config.model,
            messages=messages,
        )

        return response["message"]["content"].strip()
