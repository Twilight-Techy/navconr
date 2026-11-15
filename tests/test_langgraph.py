import pytest

pytest.importorskip("langgraph")

from navconr.langgraph_integration import langchain_tools, retrieval_graph
from navconr.models import BudgetExceeded


async def test_reference_langgraph_workflow_returns_exact_context(index):
    graph = retrieval_graph(index)
    state = await graph.ainvoke({"query": "refresh tokens revocation"})
    assert state["retrieval"]["evidence"]
    assert any("Redis" in item["text"] for item in state["retrieval"]["evidence"])


async def test_framework_tools_retain_shared_session_limits(index):
    begin, navigate, close = langchain_tools(index)
    session = await begin.ainvoke({"limits": {"steps": 1}})
    request = {
        "session_id": session["session_id"],
        "operation": "search",
        "arguments": {"query": "tokens"},
    }
    assert (await navigate.ainvoke(request))["result"]["items"]
    with pytest.raises(BudgetExceeded):
        await navigate.ainvoke(request)
    assert (await close.ainvoke({"session_id": session["session_id"]}))["usage"]["steps"] == 1
