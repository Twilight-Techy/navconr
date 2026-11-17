from __future__ import annotations

import asyncio
import time
import uuid
from typing import Literal

from .index import Index, Session
from .model import PolicyProvider
from .models import (
    BudgetExceeded,
    DeadlineExceeded,
    Evidence,
    Limits,
    NavconrError,
    Result,
)
from .search import STOPWORDS
from .util import terms


class Navigator:
    def __init__(
        self,
        index: Index,
        *,
        policy: str = "fixed",
        provider: PolicyProvider | None = None,
        search_mode: str = "lexical",
        summaries: bool = True,
        references: bool = True,
        global_search: bool = True,
    ):
        if policy not in {"fixed", "adaptive", "model"}:
            raise NavconrError("policy must be fixed, adaptive, or model")
        if policy == "model" and provider is None:
            raise NavconrError("model policy requires an explicit provider")
        self.index, self.policy, self.provider = index, policy, provider
        self.search_mode, self.summaries, self.references = search_mode, summaries, references
        self.global_search = global_search

    async def retrieve(
        self, query: str, *, revision: str | None = None, limits: Limits | None = None
    ) -> Result:
        if not query.strip() or len(query) > 1000:
            raise NavconrError("query must contain 1..1000 characters")
        session = self.index.session(revision, limits)
        evidence: dict[str, Evidence] = {}
        error: str | None = None
        reason: Literal[
            "completed",
            "budget_exhausted",
            "deadline_exceeded",
            "insufficient_evidence",
            "cancelled",
            "failed",
        ] = "completed"
        try:
            if self.policy == "model":
                await self._model(query, session, evidence)
            else:
                await self._local(query, session, evidence)
            if not evidence:
                reason = "insufficient_evidence"
        except BudgetExceeded as exc:
            reason, error = "budget_exhausted", str(exc)
        except DeadlineExceeded as exc:
            reason, error = "deadline_exceeded", str(exc)
        except TimeoutError:
            reason, error = "deadline_exceeded", "provider exceeded session deadline"
        except asyncio.CancelledError:
            reason, error = "cancelled", "retrieval cancelled"
        except (NavconrError, ValueError) as exc:
            reason, error = "failed", str(exc)
        if error:
            session._record("stop", {"reason": reason}, {"error": error}, time.monotonic())
        result = Result(
            run_id=uuid.uuid4().hex,
            revision=session.data.revision,
            query=query,
            evidence=list(evidence.values()),
            trace=session.events,
            usage=session.budget.usage.model_copy(deep=True),
            stop_reason=reason,
            error=error,
            policy=self.policy,
        )
        self.index.store.save_run(result)
        return result

    def _read_node(self, session: Session, nid: str, evidence: dict):
        node = session.node(nid)
        span_ids = [sid for sid in node.span_ids if sid not in evidence]
        if not span_ids:
            return
        for offset in range(0, len(span_ids), 20):
            for item in session.read(span_ids[offset : offset + 20]):
                if item.evidence:
                    evidence[item.id] = item.evidence
                elif item.error and "budget insufficient" in item.error:
                    raise BudgetExceeded(item.error)

    async def _local(self, query: str, session: Session, evidence: dict[str, Evidence]):
        keywords = set(terms(query)) - STOPWORDS

        def relevance(card):
            text = card.title + (" " + card.summary if self.summaries else "")
            return len(set(terms(text)) & keywords)

        page = session.overview(limit=20)
        frontier = [(relevance(c), c.id) for c in page.items]
        visited = set()
        followed = set()
        # Inspect a bounded part of the map; global search recovers branches absent from this page.
        map_expansions = 0
        expansion_limit = (
            min(8, max(1, session.budget.limits.source_bytes // 1024))
            if self.policy == "adaptive"
            else 8
        )
        while frontier and map_expansions < expansion_limit:
            await asyncio.sleep(0)
            session.budget.check()
            frontier.sort(key=lambda item: (-item[0], item[1]))
            score, nid = frontier.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = session.node(nid)
            if node.kind == "block":
                if score:
                    self._read_node(session, nid, evidence)
                    if self.references and nid not in followed:
                        followed.add(nid)
                        related = session.follow(nid)
                        frontier.extend((1, c.id) for c in related.items)
                continue
            children = session.expand([nid], limit=20)
            frontier.extend((relevance(c), c.id) for c in children.items)
            map_expansions += 1
        if not self.global_search:
            return
        page = session.search(query, mode=self.search_mode, limit=20)
        no_gain = 0
        for card in page.items:
            await asyncio.sleep(0)
            session.budget.check()
            before = len(evidence)
            self._read_node(session, card.id, evidence)
            if self.references and card.id not in followed:
                followed.add(card.id)
                for linked in session.follow(card.id).items:
                    descendants = session.descendants(linked.id)
                    for target in descendants:
                        if session.node(target).kind == "block":
                            self._read_node(session, target, evidence)
            no_gain = no_gain + 1 if len(evidence) == before else 0
            if self.policy == "adaptive" and no_gain >= 2:
                break

    async def _model(self, query: str, session: Session, evidence: dict[str, Evidence]):
        assert self.provider is not None
        observation = session.overview(limit=10).model_dump()
        while True:
            session.budget.check()
            started = time.monotonic()
            action = await self.provider.action(
                {
                    "task": "Find original evidence for the query using bounded tools. Choose stop when finished. Never invent IDs.",
                    "query": query,
                    "observation": observation,
                    "collected_span_ids": list(evidence),
                    "usage": session.budget.usage.model_dump(),
                    "limits": session.budget.limits.model_dump(),
                },
                session.budget,
            )
            session._record("model", {"provider": self.provider.name}, action.model_dump(), started)
            if action.action == "stop":
                return
            if action.action == "search":
                observation = session.search(action.query or query, limit=10).model_dump()
            elif action.action == "expand":
                observation = session.expand(action.ids, limit=10).model_dump()
            elif action.action == "follow":
                if len(action.ids) != 1:
                    raise NavconrError("follow action requires exactly one node")
                observation = session.follow(action.ids[0], limit=10).model_dump()
            elif action.action == "read":
                items = session.read(action.ids)
                for item in items:
                    if item.evidence:
                        evidence[item.id] = item.evidence
                observation = {"items": [i.model_dump() for i in items]}
