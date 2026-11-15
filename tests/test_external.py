import json

import pytest

from navconr import NavconrError
from navconr.external import score_external


def test_external_evidence_requires_matching_snapshots_and_budgets(index, tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            {
                "provenance": "test",
                "review_status": "fixture",
                "questions": [
                    {
                        "id": "q",
                        "query": "tokens",
                        "family": "a",
                        "split": "dev",
                        "category": "lookup",
                        "evidence_groups": [[{"source": "auth.md", "text": "30 days"}]],
                    }
                ],
            }
        )
    )
    session = index.session()
    sid = session.search("30 days").items[0].span_ids[0]
    run = {
        "method": "external-fixture",
        "upstream_revision": "test-1",
        "configuration": {},
        "transformations": "none",
        "index_revision": session.data.revision,
        "source_byte_budget": 512,
        "predictions": [
            {"question_id": "q", "spans": [session.data.spans[sid].model_dump()], "latency_ms": 1}
        ],
    }
    path = tmp_path / "predictions.json"
    path.write_text(json.dumps(run))
    report = score_external(index, dataset, path, "dev")
    assert report["rows"][0]["metrics"]["evidence_recall"] == 1
    run["source_byte_budget"] = 1
    path.write_text(json.dumps(run))
    with pytest.raises(NavconrError, match="budget"):
        score_external(index, dataset, path, "dev")
