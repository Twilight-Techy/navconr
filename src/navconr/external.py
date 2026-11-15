"""Score externally produced retrieval spans against the same source revision.

This imports supplied results; it does not execute or claim to reproduce upstream systems.
"""

from pathlib import Path

from pydantic import Field

from .evaluation import Dataset, score
from .index import Index
from .models import Evidence, NavconrError, Record, Span
from .util import exact_slice, identity


class ExternalPrediction(Record):
    question_id: str
    spans: list[Span]
    latency_ms: float = Field(ge=0)
    reported_model_tokens: int | None = Field(default=None, ge=0)


class ExternalRun(Record):
    method: str
    upstream_revision: str
    configuration: dict
    transformations: str
    index_revision: str
    source_byte_budget: int = Field(ge=0)
    predictions: list[ExternalPrediction]


def score_external(index: Index, dataset_path: Path, predictions_path: Path, split: str) -> dict:
    dataset = Dataset.model_validate_json(dataset_path.read_text())
    external = ExternalRun.model_validate_json(predictions_path.read_text())
    data = index.store.load(external.index_revision)
    questions = {q.id: q for q in dataset.questions if q.split == split}
    seen = set()
    rows = []
    for prediction in external.predictions:
        if prediction.question_id not in questions or prediction.question_id in seen:
            raise NavconrError("unknown, wrong-split, or duplicate external question ID")
        seen.add(prediction.question_id)
        evidence = []
        for span in prediction.spans:
            source = data.sources.get(span.source)
            if source is None:
                raise NavconrError("external evidence source is not in the pinned collection")
            if span.coordinate == "original":
                valid = span.blob == source.blob
            else:
                valid = any(
                    a.source == span.source and a.blob == span.blob and a.origin == span.origin
                    for a in data.artifacts
                )
            if not valid:
                raise NavconrError(
                    "external evidence coordinates do not match indexed source/artifact"
                )
            raw = index.store.blob(span.blob)
            text = exact_slice(raw, span.start, span.end)
            evidence.append(Evidence(span=span, text=text, revision=data.revision))
        metrics = score(questions[prediction.question_id], evidence)
        if metrics["evidence_bytes"] > external.source_byte_budget:
            raise NavconrError("external method exceeded its declared source budget")
        rows.append(
            {
                "question_id": prediction.question_id,
                "metrics": metrics,
                "latency_ms": prediction.latency_ms,
                "reported_model_tokens": prediction.reported_model_tokens,
            }
        )
    return {
        "schema_version": 1,
        "method": external.method,
        "upstream_revision": external.upstream_revision,
        "index_revision": data.revision,
        "configuration": external.configuration,
        "transformations": external.transformations,
        "input_fingerprint": identity(external.model_dump()),
        "source_byte_budget": external.source_byte_budget,
        "rows": rows,
        "missing_questions": sorted(questions.keys() - seen),
        "provenance_note": "Scored supplied external spans; upstream execution/usage are reported by the producer, not independently verified by this importer.",
    }
