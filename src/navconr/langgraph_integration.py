"""Optional LangGraph/LangChain integration; all retrieval remains inside bounded sessions."""

from typing import TypedDict

from .index import Index
from .integrations import AgentTools, ToolRequest
from .models import Limits, NavconrError
from .navigation import Navigator


class RetrievalState(TypedDict):
    query: str
    retrieval: dict


def langchain_tools(index: Index):
    try:
        from langchain_core.tools import tool
    except ImportError as exc:
        raise NavconrError("install navconr[langgraph] for framework tools") from exc
    registry = AgentTools(index)

    @tool
    async def knowledge_begin(limits: dict | None = None, revision: str | None = None) -> dict:
        """Begin a bounded knowledge session pinned to one source index revision."""
        return registry.begin(Limits.model_validate(limits or {}), revision)

    @tool
    async def knowledge_navigate(session_id: str, operation: str, arguments: dict) -> dict:
        """Call overview, expand, search, follow or read inside the shared session budget."""
        return registry.call(
            ToolRequest(session_id=session_id, operation=operation, arguments=arguments)
        )

    @tool
    async def knowledge_close(session_id: str) -> dict:
        """Release a knowledge session and return its final usage."""
        return registry.close(session_id)

    return [knowledge_begin, knowledge_navigate, knowledge_close]


def retrieval_graph(index: Index, limits: Limits | None = None):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise NavconrError("install navconr[langgraph] for the reference workflow") from exc

    async def retrieve(state: RetrievalState):
        result = await Navigator(index).retrieve(state["query"], limits=limits)
        return {"retrieval": result.model_dump()}

    builder = StateGraph(RetrievalState)
    builder.add_node("retrieve_context", retrieve)
    builder.add_edge(START, "retrieve_context")
    builder.add_edge("retrieve_context", END)
    return builder.compile()
