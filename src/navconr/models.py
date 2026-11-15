"""Versioned public records. Byte offsets are zero-based and end-exclusive."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    schema_version: Literal[1] = 1


class Source(Record):
    path: str
    blob: str
    parser: str
    media_type: str = "text/plain"


class Artifact(Record):
    blob: str
    original: str
    source: str
    origin: str
    extractor: str


class Span(Record):
    id: str
    blob: str
    source: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    coordinate: Literal["original", "extracted"] = "original"
    origin: str | None = None
    line_start: int = Field(default=1, ge=1)
    line_end: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def valid_range(self) -> Span:
        if self.end < self.start or self.line_end < self.line_start:
            raise ValueError("invalid byte or line range")
        return self


class Node(Record):
    id: str
    title: str = Field(max_length=160)
    summary: str = Field(default="", max_length=600)
    kind: Literal["collection", "group", "document", "section", "block", "symbol"]
    parent: str | None = None
    span_ids: list[str] = Field(default_factory=list)
    source: str | None = None
    anchor: str | None = None


class Edge(Record):
    source: str
    target: str | None = None
    relation: str
    origin: Literal["parsed", "manual", "similarity", "inferred"] = "parsed"
    unresolved: str | None = None
    evidence: list[str] = Field(default_factory=list)
    score: float | None = None
    reference: str | None = None


class IndexData(Record):
    revision: str
    root: str
    fingerprint: str
    sources: dict[str, Source]
    artifacts: list[Artifact] = Field(default_factory=list)
    spans: dict[str, Span]
    nodes: dict[str, Node]
    edges: list[Edge]
    diagnostics: list[str] = Field(default_factory=list)


class Card(Record):
    id: str
    title: str
    summary: str
    kind: str
    children: int
    span_ids: list[str]
    source: str | None
    score: float | None = None
    parent: str | None = None


class Page(Record):
    revision: str
    items: list[Card]
    next_cursor: str | None = None
    unresolved: list[str] = Field(default_factory=list)


class Evidence(Record):
    span: Span
    text: str
    revision: str


class ReadItem(Record):
    id: str
    evidence: Evidence | None = None
    error: str | None = None


class Limits(Record):
    steps: int = Field(default=64, ge=1, le=10000)
    expansions: int = Field(default=100, ge=0)
    map_bytes: int = Field(default=128_000, ge=0)
    source_bytes: int = Field(default=16_000, ge=0)
    model_calls: int = Field(default=8, ge=0)
    model_tokens: int = Field(default=16000, ge=0)
    retries: int = Field(default=1, ge=0, le=5)
    seconds: float = Field(default=60, gt=0, le=3600)
    hard_model_tokens: bool = False


class Usage(Record):
    steps: int = 0
    expansions: int = 0
    map_bytes: int = 0
    source_bytes: int = 0
    model_calls: int = 0
    model_tokens: int = 0
    reserved_tokens: int = 0
    token_accounting: Literal["measured", "estimated", "unavailable"] = "estimated"


class Event(Record):
    sequence: int
    action: str
    arguments: dict
    response: dict
    elapsed_ms: float
    usage: Usage


class Result(Record):
    run_id: str
    revision: str
    query: str
    evidence: list[Evidence]
    trace: list[Event]
    usage: Usage
    stop_reason: Literal[
        "completed",
        "budget_exhausted",
        "deadline_exceeded",
        "insufficient_evidence",
        "cancelled",
        "failed",
    ]
    error: str | None = None
    policy: str


class Action(Record):
    action: Literal["expand", "search", "follow", "read", "stop"]
    ids: list[str] = Field(default_factory=list, max_length=20)
    query: str | None = Field(default=None, max_length=1000)


class NavconrError(Exception):
    """A user-facing contract or storage failure."""


class BudgetExceeded(NavconrError):
    pass


class DeadlineExceeded(NavconrError):
    pass
