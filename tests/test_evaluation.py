import json

import pytest
from pydantic import ValidationError

from navconr.evaluation import Dataset, Passage, Question, evaluate, score


def test_score_requires_all_hops_and_accepts_alternatives(index):
    session = index.session()
    items = session.search("30 days").items
    evidence = [r.evidence for item in items for r in session.read(item.span_ids) if r.evidence]
    question = Question(
        id="q",
        query="refresh",
        family="a",
        split="dev",
        category="multi",
        evidence_groups=[
            [Passage(source="auth.md", text="30 days")],
            [Passage(source="ops.md", text="Redis")],
        ],
    )
    assert score(question, evidence)["evidence_recall"] == 0.5
    assert score(question, evidence)["complete_evidence"] is False


def test_family_leakage_is_rejected():
    q = {
        "id": "a",
        "query": "q",
        "family": "f",
        "split": "dev",
        "category": "lookup",
        "evidence_groups": [],
    }
    with pytest.raises(ValidationError, match="leaks"):
        Dataset(
            provenance="test",
            review_status="fixture",
            questions=[q, {**q, "id": "b", "split": "heldout"}],
        )


async def test_runner_resumes_without_duplicate_results(index, tmp_path):
    dataset = {
        "provenance": "test fixture",
        "review_status": "test",
        "questions": [
            {
                "id": "q",
                "query": "refresh tokens expire",
                "family": "a",
                "split": "dev",
                "category": "lookup",
                "evidence_groups": [[{"source": "auth.md", "text": "30 days"}]],
            }
        ],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset))
    first = await evaluate(
        index, path, tmp_path / "results", methods=["lexical", "fixed"], budgets=[512]
    )
    second = await evaluate(
        index, path, tmp_path / "results", methods=["lexical", "fixed"], budgets=[512]
    )
    assert first["rows"] == second["rows"] == 2
    assert first["run_key"] == second["run_key"]
    assert all(row["failures"] == 0 for row in first["summary"])


async def test_common_reader_uses_only_retrieved_citations(index, tmp_path):
    from navconr.answering import Answer

    class Reader:
        name = "fixture-reader"

        async def structured(self, prompt, schema, budget):
            return Answer(text="30 days", span_ids=[prompt["evidence"][0]["span_id"]])

    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "provenance": "fixture",
                "review_status": "test",
                "questions": [
                    {
                        "id": "reader",
                        "query": "refresh tokens 30 days",
                        "family": "a",
                        "split": "dev",
                        "category": "lookup",
                        "evidence_groups": [[{"source": "auth.md", "text": "30 days"}]],
                        "expected_answers": ["30 days"],
                    }
                ],
            }
        )
    )
    result = await evaluate(
        index, path, tmp_path / "results", methods=["lexical"], budgets=[512], reader=Reader()
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "results" / result["run_key"] / "results.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows[0]["metrics"]["answer_correctness"] is True
    assert rows[0]["answer"]["span_ids"]
