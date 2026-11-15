from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Paging(ToolArguments):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None
    max_bytes: int = Field(default=16384, ge=512, le=65536)


class Overview(Paging):
    view: Literal["physical", "semantic"] = "physical"


class Expand(Paging):
    node_ids: list[str] = Field(min_length=1, max_length=20)


class Search(Paging):
    query: str = Field(min_length=1, max_length=1000)
    mode: Literal["lexical", "vector", "hybrid", "semantic"] = "lexical"
    scope: str | None = None


class Follow(Paging):
    node_id: str
    relation: str = Field(default="reference", max_length=100)
    inverse: bool = False
    origin: Literal["parsed", "manual", "similarity", "inferred"] | None = None


class Read(ToolArguments):
    span_ids: list[str] = Field(min_length=1, max_length=20)
    ranges: dict[str, tuple[int, int]] | None = None


ARGUMENTS: dict[str, type[ToolArguments]] = {
    "overview": Overview,
    "expand": Expand,
    "search": Search,
    "follow": Follow,
    "read": Read,
}
