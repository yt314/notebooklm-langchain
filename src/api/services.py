"""Backend services: translate API requests into the LangChain code.

This is the thin layer between the stable API contract and the per-stage implementations.
Source management and notes are product glue (in-memory); chat is powered by the stage-2
agent; Studio artifacts raise ``ComingSoon`` until structured output lands in stage 3.
"""

from __future__ import annotations

import uuid

from api.schemas import (
    ArtifactKind,
    ChatRequest,
    ChatResponse,
    Citation,
    Note,
    SourceDetail,
    SourceInfo,
)
from agents import chat
from core.store import store


class ComingSoon(Exception):
    """Raised for a product capability that is advertised but not wired up yet."""


# -- sources -------------------------------------------------------------------


def _to_info(source) -> SourceInfo:
    return SourceInfo(
        id=source.id, name=source.name, chars=len(source.content), active=source.active
    )


def list_sources() -> list[SourceInfo]:
    return [_to_info(s) for s in store.list()]


def get_source(source_id: str) -> SourceDetail | None:
    source = store.get(source_id)
    if source is None:
        return None
    return SourceDetail(
        id=source.id,
        name=source.name,
        chars=len(source.content),
        active=source.active,
        content=source.content,
    )


def add_source(name: str | None, content: str) -> SourceInfo:
    name = (name or "").strip() or _auto_name(content)
    return _to_info(store.add(name=name, content=content))


def set_source_active(source_id: str, active: bool) -> SourceInfo | None:
    source = store.set_active(source_id, active)
    return _to_info(source) if source else None


def remove_source(source_id: str) -> bool:
    return store.remove(source_id)


def _auto_name(content: str) -> str:
    first_line = content.strip().splitlines()[0] if content.strip() else "Pasted source"
    first_line = first_line.lstrip("# ").strip()
    return (first_line[:40] or "Pasted source") + ".txt"


# -- chat ----------------------------------------------------------------------


def run_chat(req: ChatRequest) -> ChatResponse:
    """Answer a chat turn with the stage-2 agent, grounded in the active sources."""
    if not store.active_ids():
        return ChatResponse(
            answer="No active sources. Enable at least one source on the left to chat.",
            engine="chat",
        )

    result = chat.answer(req.message, thread_id=req.thread_id or "default")
    citations = [Citation(source=name) for name in result.sources]
    return ChatResponse(answer=result.text, citations=citations, engine="chat")


# -- studio (artifacts) --------------------------------------------------------

ARTIFACTS: list[ArtifactKind] = [
    ArtifactKind(key="infographic", title="Infographic", icon="📊", status="planned"),
    ArtifactKind(key="powerpoint", title="PowerPoint", icon="📑", status="planned"),
    ArtifactKind(key="summary", title="Summary", icon="📄", status="planned"),
    ArtifactKind(key="faq", title="FAQ", icon="❓", status="planned"),
]

_ARTIFACTS_BY_KEY = {a.key: a for a in ARTIFACTS}


def list_artifacts() -> list[ArtifactKind]:
    return ARTIFACTS


def generate_artifact(kind: str, impl: str) -> Note:
    # Artifact generation lands with structured output; until then it's "coming soon".
    artifact = _ARTIFACTS_BY_KEY.get(kind)
    title = artifact.title if artifact else "This artifact"
    raise ComingSoon(f"{title} generation is coming soon.")


# -- notes ---------------------------------------------------------------------

_NOTES: dict[str, Note] = {}


def list_notes() -> list[Note]:
    return list(_NOTES.values())


def add_note(title: str, content: str) -> Note:
    note = Note(id=uuid.uuid4().hex[:8], title=title.strip() or "Untitled note", content=content)
    _NOTES[note.id] = note
    return note


def remove_note(note_id: str) -> bool:
    return _NOTES.pop(note_id, None) is not None
