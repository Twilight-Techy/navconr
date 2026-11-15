import json
import sys
import threading
from http.server import HTTPServer

import httpx
import pytest

from navconr import Limits, NavconrError
from navconr.integrations import AgentTools, ToolRequest
from navconr.server import make_handler


def test_agent_tools_share_budget_and_limit_operations(index):
    tools = AgentTools(index)
    session = tools.begin(Limits(steps=1))
    request = ToolRequest(
        session_id=session["session_id"], operation="search", arguments={"query": "tokens"}
    )
    assert tools.call(request)["result"]["items"]
    with pytest.raises(NavconrError, match="budget exhausted"):
        tools.call(request)
    with pytest.raises(NavconrError, match="unsupported"):
        tools.call(request.model_copy(update={"operation": "execute_shell"}))
    assert tools.close(session["session_id"])["usage"]["steps"] == 1


def test_agent_arguments_are_schema_validated(index):
    tools = AgentTools(index)
    session = tools.begin()
    request = ToolRequest(
        session_id=session["session_id"], operation="read", arguments={"span_ids": "not-a-list"}
    )
    with pytest.raises(NavconrError, match="arguments"):
        tools.call(request)
    assert "arguments" in tools.schemas()


def test_loopback_bridge_and_root_boundaries(index, tmp_path):
    candidate = index.search("tokens").items[0]
    index.group("Token map", [candidate.id])
    viewer = tmp_path / "viewer"
    viewer.mkdir()
    (viewer / "index.html").write_text("<h1>Inspector</h1>")
    server = HTTPServer(("127.0.0.1", 0), make_handler(index.store.path, viewer))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with httpx.Client(base_url=base) as client:
            assert client.get("/").status_code == 200
            assert client.get("/api/status").json()["sources"] == 3
            assert (
                client.get("/api/overview?view=semantic").json()["items"][0]["title"] == "Token map"
            )
            assert client.get("/api/search", params={"q": "tokens"}).json()["items"]
            assert (
                client.get("/api/status", headers={"Host": "attacker.example"}).status_code == 403
            )
            assert (
                client.get(
                    "/api/status", headers={"Origin": "https://attacker.example"}
                ).status_code
                == 403
            )
            assert client.get("/api/status?revision=missing").status_code == 400
            assert client.get("/%2e%2e/secret").status_code == 403
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


async def test_real_mcp_stdio_transport(index):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "navconr.cli", "mcp", "--db", str(index.store.path)]
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            available = await session.list_tools()
            assert {"begin_session", "navigate", "close_session"} <= {
                tool.name for tool in available.tools
            }
            response = await session.call_tool("begin_session", {"limits": {"steps": 2}})
            payload = json.loads(response.content[0].text)
            result = await session.call_tool(
                "navigate",
                {
                    "session_id": payload["session_id"],
                    "operation": "search",
                    "arguments": {"query": "tokens"},
                },
            )
            assert not result.isError
            assert json.loads(result.content[0].text)["result"]["items"]
            invalid = await session.call_tool(
                "navigate",
                {
                    "session_id": payload["session_id"],
                    "operation": "execute_shell",
                    "arguments": {},
                },
            )
            assert invalid.isError
