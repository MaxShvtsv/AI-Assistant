"""TODO"""
from ollama_client import OllamaConfig, OllamaClient

def main():
    """TODO"""
    config = OllamaConfig(
        host="http://localhost:11434",
        model="gemma3",
        is_streaming=False,
        system_prompt="""
            Your name is Intel.
            You are a local desktop voice assistant.
            Your job is to help the user with short voice interactions.
            Be concise.
            If the user asks for a simple desktop action, describe it briefly.
            Avoid long explanations unless asked.
            Prefer short responses suitable for speech output.
        """,
    )

    client = OllamaClient(
        config=config
    )

    while True:
        user_input = input("Me: ").strip()

        if user_input.lower() in ("exit", "quit"):
            break

        response = client.chat(user_input)

        print("Intel:", response)


if __name__ == '__main__':
    main()
