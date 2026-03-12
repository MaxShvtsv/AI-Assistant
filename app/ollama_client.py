"""
Adapter for Ollama SDK
"""
from dataclasses import dataclass

from ollama import Client

@dataclass
class OllamaConfig:
    """Config for Ollama instance."""
    host: str: = "http://localhost:11434"
    model: str = "gemma3"
    is_streaming: bool = False
    system_prompt: str = """
        Your name is Intel.
        You are a local desktop voice assistant.
        Your job is to help the user with short voice interactions.
        Be concise.
        If the user asks for a simple desktop action, describe it briefly.
        Avoid long explanations unless asked.
        Prefer short responses suitable for speech output.
    """

class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = Client(host=config.host)
    
    def chat(self):
        return self.client.chat