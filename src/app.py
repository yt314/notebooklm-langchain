"""Local CLI for exercising the chat agent directly, without the web client."""

from __future__ import annotations

from netfree_unstrict_ssl import unstrict_ssl

unstrict_ssl()

from dotenv import load_dotenv

load_dotenv()

import sys
import uuid

from agents import chat


def _ask(question: str, thread_id: str) -> None:
    result = chat.answer(question, thread_id=thread_id)
    print(result.text)
    if result.sources:
        print(f"\n(sources: {', '.join(result.sources)})")


def main() -> None:
    thread_id = uuid.uuid4().hex
    question = " ".join(sys.argv[1:]).strip()

    if question:
        _ask(question, thread_id)
        return

    print("NotebookLM chat — Ctrl+C to quit")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question:
            _ask(question, thread_id)


if __name__ == "__main__":
    main()
