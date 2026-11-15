"""Reproducible retrieval experiments. Synthetic checks are not research evidence."""

from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import statistics
import time
from pathlib import Path

from pydantic import Field, model_validator

from .answering import answer
from .budget import Budget
from .index import Index
from .models import BudgetExceeded, Evidence, Limits, NavconrError, Record, Result, Usage
from .navigation import Navigator
from .providers import OllamaProvider
from .util import digest, identity, terms

METHODS = [
    "lexical",
    "vector",
    "hybrid",
    "parent_child",
    "structural",
    "fixed",
    "adaptive",
    "no_summaries",
    "no_references",
]


class Passage(Record):
    source: str
    text: str = Field(min_length=1)


class Question(Record):
    id: str
    query: str
    family: str
    split: str
    category: str
    evidence_groups: list[list[Passage]]
    expected_answers: list[str] = Field(default_factory=list)


class Dataset(Record):
    provenance: str
    review_status: str
    questions: list[Question]

    @model_validator(mode="after")
    def valid_splits(self):
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate question IDs")
        families: dict[str, str] = {}
        source_splits: dict[str, str] = {}
        for question in self.questions:
            if question.split not in {"dev", "heldout"}:
                raise ValueError("unknown split")
            if question.family in families and families[question.family] != question.split:
                raise ValueError("document family leaks across splits")
            families[question.family] = question.split
            for group in question.evidence_groups:
                if not group:
                    raise ValueError("an evidence group needs at least one alternative")
                for passage in group:
                    if (
                        passage.source in source_splits
                        and source_splits[passage.source] != question.split
                    ):
                        raise ValueError("evidence source leaks across splits")
                    source_splits[passage.source] = question.split
        return self


def score(question: Question, evidence: list[Evidence]) -> dict:
    recovered = 0
    by_source: dict[str, list[str]] = {}
    # Merge contiguous evidence intervals to allow a gold passage crossing a split boundary.
    groups: dict[tuple[str, str], list[Evidence]] = {}
    for item in evidence:
        groups.setdefault((item.span.source, item.span.blob), []).append(item)
    for (source, _), items in groups.items():
        ordered = sorted(items, key=lambda e: e.span.start)
        merged = []
        end, content = None, b""
        for item in ordered:
            if end is None or item.span.start > end:
                if end is not None:
                    merged.append(content.decode())
                end, content = item.span.end, item.text.encode()
            elif item.span.end > end:
                content += item.text.encode()[end - item.span.start :]
                end = item.span.end
        if end is not None:
            merged.append(content.decode())
        by_source.setdefault(source, []).extend(merged)
    for group in question.evidence_groups:
        if any(
            any(passage.text in text for text in by_source.get(passage.source, []))
            for passage in group
        ):
            recovered += 1
    required = len(question.evidence_groups)
    return {
        "evidence_recall": recovered / required if required else None,
        "complete_evidence": recovered == required if required else None,
        "correct_abstention": not evidence if not required else None,
        "source_count": len(by_source),
        "evidence_bytes": sum(len(e.text.encode()) for e in evidence),
        "answer_correctness": None,
        "citation_support": None,
    }


async def retrieve_method(index: Index, query: str, method: str, byte_budget: int):
    limits = Limits(
        source_bytes=byte_budget, map_bytes=512000, steps=256, expansions=256, seconds=120
    )
    if method in {"fixed", "adaptive", "no_summaries", "no_references", "structural"}:
        navigator = Navigator(
            index,
            policy="adaptive" if method == "adaptive" else "fixed",
            summaries=method != "no_summaries",
            references=method != "no_references",
            global_search=method != "structural",
        )
        result = await navigator.retrieve(query, limits=limits)
        return result.evidence, result.usage.model_dump(), result.stop_reason, result.run_id
    session = index.session(limits=limits)
    candidates = session.search(
        query, mode="lexical" if method == "parent_child" else method, limit=100
    ).items
    evidence: dict[str, Evidence] = {}
    seen = set()
    for candidate in candidates:
        targets = [candidate.id]
        if method == "parent_child":
            parent = session.node(candidate.id).parent
            if parent:
                targets = session.descendants(parent)
        for nid in targets:
            node = session.node(nid)
            if node.kind != "block" or nid in seen:
                continue
            seen.add(nid)
            unread = [sid for sid in node.span_ids if sid not in evidence]
            if unread:
                try:
                    items = session.read(unread)
                except BudgetExceeded:
                    return (
                        list(evidence.values()),
                        session.budget.usage.model_dump(),
                        "budget_exhausted",
                        None,
                    )
                for item in items:
                    if item.evidence:
                        evidence[item.id] = item.evidence
    return (
        list(evidence.values()),
        session.budget.usage.model_dump(),
        "completed" if evidence else "insufficient_evidence",
        None,
    )


async def evaluate(
    index: Index,
    dataset_path: Path,
    output: Path,
    *,
    split: str = "dev",
    budgets: list[int] | None = None,
    methods: list[str] | None = None,
    repeats: int = 1,
    reader: OllamaProvider | None = None,
) -> dict:
    dataset = Dataset.model_validate_json(dataset_path.read_text())
    data = index.store.load()
    for question in dataset.questions:
        for group in question.evidence_groups:
            for passage in group:
                if passage.source not in data.sources:
                    raise NavconrError(f"missing annotated source: {passage.source}")
                extracted = [
                    artifact for artifact in data.artifacts if artifact.source == passage.source
                ]
                texts = (
                    [index.store.blob(artifact.blob).decode() for artifact in extracted]
                    if extracted
                    else [index.store.blob(data.sources[passage.source].blob).decode()]
                )
                if not any(passage.text in text for text in texts):
                    raise NavconrError(f"gold passage absent from original source: {question.id}")
    methods = methods or METHODS
    if any(method not in METHODS for method in methods) or repeats < 1:
        raise NavconrError("unsupported method or repeat count")
    budgets = budgets or [512, 2048]
    if any(value < 0 for value in budgets):
        raise NavconrError("source budgets must be nonnegative")
    code_hash = digest(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py"))))
    manifest = {
        "schema_version": 1,
        "dataset_hash": digest(dataset_path.read_bytes()),
        "revision": data.revision,
        "code_hash": code_hash,
        "methods": methods,
        "budgets": budgets,
        "split": split,
        "repeats": repeats,
        "seed": 0,
        "python": platform.python_version(),
        "versions": dict(
            sorted(
                (distribution.metadata["Name"].lower(), distribution.version)
                for distribution in importlib.metadata.distributions()
                if distribution.metadata.get("Name")
            )
        ),
        "provenance": dataset.provenance,
        "review_status": dataset.review_status,
        "cache": "warm source index; each method creates its own search session",
        "reader": {
            "name": reader.name,
            "endpoint": reader.base_url,
            "limits": Limits().model_dump(),
        }
        if reader
        else None,
        "model_calls": "none for local methods",
        "semantic_encoder": None,
    }
    run_key = identity(manifest)
    destination = output / run_key
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    raw_path = destination / "results.jsonl"
    rows = []
    if raw_path.exists():
        for line in raw_path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise NavconrError(
                    "partial/corrupt result row; recover the last write before resuming"
                ) from exc
    done = {(r["id"], r["method"], r["budget"], r["repeat"]) for r in rows}
    with raw_path.open("a") as stream:
        for question in dataset.questions:
            if question.split != split:
                continue
            for method in methods:
                for budget in budgets:
                    for repeat in range(repeats):
                        key = (question.id, method, budget, repeat)
                        if key in done:
                            continue
                        started = time.perf_counter()
                        error = None
                        response = None
                        reader_usage = None
                        try:
                            evidence, usage, reason, trace = await retrieve_method(
                                index, question.query, method, budget
                            )
                            if reader:
                                reader_budget = Budget()
                                reader_input = Result(
                                    run_id=identity(question.id, method, budget, repeat),
                                    revision=data.revision,
                                    query=question.query,
                                    evidence=evidence,
                                    trace=[],
                                    usage=Usage.model_validate(usage),
                                    stop_reason="completed"
                                    if evidence
                                    else "insufficient_evidence",
                                    policy=method,
                                )
                                response = await answer(
                                    question.query, reader_input, reader, reader_budget
                                )
                                reader_usage = reader_budget.usage.model_dump()
                        except (NavconrError, ValueError) as exc:
                            evidence, usage, reason, trace = [], {}, "failed", None
                            error = str(exc)
                        metrics = score(question, evidence)
                        if response and question.expected_answers:
                            metrics["answer_correctness"] = any(
                                terms(response.text) == terms(expected)
                                for expected in question.expected_answers
                            )
                        row = {
                            "id": question.id,
                            "method": method,
                            "budget": budget,
                            "repeat": repeat,
                            "category": question.category,
                            "metrics": metrics,
                            "answer": response.model_dump() if response else None,
                            "reader_usage": reader_usage,
                            "usage": usage,
                            "stop_reason": reason,
                            "trace": trace,
                            "error": error,
                            "latency_ms": (time.perf_counter() - started) * 1000,
                            "spans": [e.span.model_dump() for e in evidence],
                        }
                        if row["metrics"]["evidence_bytes"] > budget:
                            raise NavconrError("method violated evidence byte budget")
                        rows.append(row)
                        stream.write(json.dumps(row) + "\n")
                        stream.flush()
    summary = []
    for method in methods:
        for budget in budgets:
            subset = [row for row in rows if row["method"] == method and row["budget"] == budget]

            def mean(metric, subset=subset):
                values = [r["metrics"][metric] for r in subset if r["metrics"][metric] is not None]
                return statistics.mean(values) if values else None

            latencies = sorted(r["latency_ms"] for r in subset)
            summary.append(
                {
                    "method": method,
                    "budget": budget,
                    "questions": len(subset),
                    "evidence_recall": mean("evidence_recall"),
                    "complete_evidence": mean("complete_evidence"),
                    "correct_abstention": mean("correct_abstention"),
                    "mean_evidence_bytes": mean("evidence_bytes"),
                    "p50_ms": statistics.median(latencies) if latencies else None,
                    "p95_ms": latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)]
                    if latencies
                    else None,
                    "failures": sum(r["stop_reason"] == "failed" for r in subset),
                }
            )
    report = {
        "run_key": run_key,
        "path": str(destination.resolve()),
        "manifest": manifest,
        "summary": summary,
        "external_comparisons": {
            name: {"status": "not_run", "reason": "upstream setup/model checks not configured"}
            for name in ["PageIndex", "RAPTOR", "NavTree"]
        },
        "limitations": [
            "Authored synthetic fixtures; no independent human review.",
            "TF-IDF is lexical vector search, not a semantic embedding baseline.",
            "No answer-quality study was run."
            if reader is None
            else "Configured common reader; exact answer matching is not a synthesis-quality or entailment assessment.",
            "Local methods use no LLM; these are software smoke results, not a scientific pilot.",
        ],
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2))
    lines = [
        "# Local retrieval smoke report",
        "",
        *[f"- {s}" for s in report["limitations"]],
        "",
        "| Method | Bytes | Recall | Complete evidence | Abstention | Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['method']} | {row['budget']} | {row['evidence_recall']} | {row['complete_evidence']} | {row['correct_abstention']} | {row['failures']} |"
        )
    (destination / "report.md").write_text("\n".join(lines) + "\n")
    return {
        "run_key": run_key,
        "path": str(destination.resolve()),
        "rows": len(rows),
        "summary": summary,
    }
