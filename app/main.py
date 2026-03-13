"""TODO"""
from core.assistant_service import AssistantService

def main():
    assistant = AssistantService()

    print("Intel is ready. Type 'exit' to quit.")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        answer = assistant.handle_text(user_input)
        print("Intel:", answer)


if __name__ == '__main__':
    main()
