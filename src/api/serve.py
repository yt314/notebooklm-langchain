"""Entry point for running the backend: ``uv run notebooklm-serve``."""

from __future__ import annotations

from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()

from dotenv import load_dotenv
load_dotenv()

import os

import uvicorn


def main() -> None:
    host = os.getenv("NOTEBOOKLM_HOST", "127.0.0.1")
    port = int(os.getenv("NOTEBOOKLM_PORT", "4040"))
    reload = os.getenv("NOTEBOOKLM_RELOAD", "0") == "1"
    print(f"NotebookLM running at http://{host}:{port}")
    uvicorn.run("api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
