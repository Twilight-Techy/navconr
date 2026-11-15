import pytest

from navconr.answering import Answer, answer
from navconr.budget import Budget
from navconr.enrichment import Enrichment, enrich
from navconr.models import Limits, NavconrError
from navconr.navigation import Navigator


async def test_atomic_enrichment_keeps_original_evidence(index):
    class Provider:
        name = "mock-enrichment"
        base_url = "mock://local"

        async def structured(self, prompt, schema, budget):
            budget.charge(model_calls=1)
            return Enrichment(summary="A generated navigation hint")

    old = index.store.current()
    response = await enrich(index, Provider(), Budget(Limits(model_calls=1000)))
    assert response["revision"] != old
    card = index.search("30 days").items[0]
    assert "30 days" in index.read(card.span_ids)[0].evidence.text


async def test_invalid_enrichment_does_not_publish(index):
    class Provider:
        name = "invalid-enrichment"
        base_url = "mock://invalid"

        async def structured(self, prompt, schema, budget):
            return Enrichment(summary="Hint", related_node_ids=["invented"])

    old = index.store.current()
    with pytest.raises(NavconrError):
        await enrich(index, Provider(), Budget())
    assert index.store.current() == old


async def test_answer_citations_must_come_from_retrieval(index):
    retrieval = await Navigator(index).retrieve("tokens")

    class InvalidReader:
        async def structured(self, prompt, schema, budget):
            return Answer(text="Unsupported claim", span_ids=["invented"])

    with pytest.raises(NavconrError, match="not retrieved"):
        await answer("tokens", retrieval, InvalidReader(), Budget())
    absent = await Navigator(index).retrieve("qzxnonexistent")
    assert (await answer("qzxnonexistent", absent, InvalidReader(), Budget())).abstained
