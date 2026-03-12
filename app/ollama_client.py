"""
Adapter for Ollama SDK
"""
from typing import Optional
from dataclasses import dataclass

from ollama import Client, ChatResponse

@dataclass
class OllamaConfig:
    """Config for Ollama instance."""
    host: str = "http://localhost:11434"
    model: str = "gemma3"
    is_streaming: bool = False
    system_prompt: Optional[str] = None

class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = Client(host=config.host)
    
    def chat(self, user_message: str) -> ChatResponse:
        messages = [
            {
                "role": "system",
                "content": self.config.system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        response = self.client.chat(
            model=self.config.model,
            messages=messages
        )

        return response.message.content
