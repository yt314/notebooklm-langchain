"""FastAPI backend: exposes the LangChain features to the web client over HTTP.

The client only ever talks to this layer. Each stage plugs its implementation(s) in
behind a stable contract (see ``schemas.py``) so the client never changes as features land.
"""
