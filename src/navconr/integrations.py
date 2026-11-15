"""Framework-neutral agent tools and optional MCP transport."""

from __future__ import annotations

import uuid

from .index import Index, Session
from .models import Limits, NavconrError, Record
from .tool_schemas import ARGUMENTS


class ToolRequest(Record):
    session_id: str
    operation: str
    arguments: dict


class AgentTools:
    """One budget and pinned revision per agent session. No shell/filesystem tools."""

    def __init__(self, index: Index):
        self.index = index
        self.sessions: dict[str, Session] = {}

    def begin(self, limits: Limits | None = None, revision: str | None = None) -> dict:
        self.sessions = {
            key: value for key, value in self.sessions.items() if value.budget.remaining_seconds > 0
        }
        if len(self.sessions) >= 32:
            raise NavconrError("too many open sessions; close or expire an existing session")
        key = uuid.uuid4().hex
        session = self.index.session(revision, limits)
        self.sessions[key] = session
        return {
            "session_id": key,
            "revision": session.data.revision,
            "limits": session.budget.limits.model_dump(),
        }

    def close(self, session_id: str) -> dict:
        session = self.sessions.pop(session_id, None)
        if session is None:
            raise NavconrError("unknown session")
        return {"usage": session.budget.usage.model_dump()}

    def call(self, request: ToolRequest) -> dict:
        session = self.sessions.get(request.session_id)
        if session is None:
            raise NavconrError("unknown session; begin a navigation session first")
        allowed = {"overview", "expand", "search", "follow", "read"}
        if request.operation not in allowed:
            raise NavconrError("unsupported agent operation")
        session.budget.check()
        try:
            arguments = ARGUMENTS[request.operation].model_validate(request.arguments).model_dump()
            result = getattr(session, request.operation)(**arguments)
        except (TypeError, ValueError) as exc:
            raise NavconrError("invalid tool arguments") from exc
        payload = (
            {"items": [item.model_dump() for item in result]}
            if isinstance(result, list)
            else result.model_dump()
        )
        return {
            "result": payload,
            "usage": session.budget.usage.model_dump(),
            "revision": session.data.revision,
        }

    @staticmethod
    def schemas():
        return {
            "begin": Limits.model_json_schema(),
            "call": ToolRequest.model_json_schema(),
            "operations": ["overview", "expand", "search", "follow", "read"],
            "arguments": {name: schema.model_json_schema() for name, schema in ARGUMENTS.items()},
        }


def run_mcp(index: Index):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise NavconrError("install navconr[mcp] (SDK 1.x) for MCP transport") from exc
    tools = AgentTools(index)
    server = FastMCP("navconr")

    @server.tool()
    def begin_session(limits: dict | None = None, revision: str | None = None) -> dict:
        """Open a bounded session pinned to an immutable index revision."""
        return tools.begin(Limits.model_validate(limits or {}), revision)

    @server.tool()
    def navigate(session_id: str, operation: str, arguments: dict) -> dict:
        """Call overview, expand, search, follow, or read within the shared session budget."""
        return tools.call(
            ToolRequest(session_id=session_id, operation=operation, arguments=arguments)
        )

    @server.tool()
    def close_session(session_id: str) -> dict:
        """Release session state and return final usage."""
        return tools.close(session_id)

    server.run(transport="stdio")
