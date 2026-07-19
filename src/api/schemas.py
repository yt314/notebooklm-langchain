"""The API contract shared between backend and client.

These Pydantic models are the *stable* boundary: the web client is written against them,
and each stage fills in the backend behind them. Keep them additive.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Impl = Literal["A", "B"]


# -- sources -------------------------------------------------------------------


class SourceInfo(BaseModel):
    """A document in the notebook (list view — no content)."""

    id: str
    name: str
    chars: int
    active: bool


class SourceDetail(SourceInfo):
    """A source with its full text (for the viewer)."""

    content: str


class AddSourceRequest(BaseModel):
    """Add a source by pasting text."""

    name: str | None = None
    content: str


class SetActiveRequest(BaseModel):
    active: bool


# -- chat ----------------------------------------------------------------------


class Citation(BaseModel):
    """A source the answer was grounded on."""

    source: str
    snippet: str | None = None


class ChatRequest(BaseModel):
    """A grounded-chat turn."""

    message: str
    thread_id: str | None = None  # used from stage 4 (short-term memory)


class ChatResponse(BaseModel):
    """The model's grounded answer plus the sources it was based on."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    engine: str


# -- studio (artifacts) --------------------------------------------------------


class ArtifactKind(BaseModel):
    """A generatable artifact shown in the Studio panel."""

    key: str
    title: str
    icon: str
    status: Literal["ready", "planned"]


class GenerateArtifactRequest(BaseModel):
    kind: str
    impl: Impl = "A"


# -- notes ---------------------------------------------------------------------


class Note(BaseModel):
    id: str
    title: str
    content: str


class AddNoteRequest(BaseModel):
    title: str
    content: str

