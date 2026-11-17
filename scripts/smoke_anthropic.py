"""Explicitly paid, single-generation smoke check; never run from ordinary CI."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from navconr import Index, Limits
from navconr.answering import answer
from navconr.anthropic import AnthropicProvider
from navconr.budget import Budget
from navconr.models import NavconrError, Result

ROOT = Path(__file__).resolve().parents[1]


def options(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", choices=["claude-haiku-5-5", "claude-opus-5-5"], default="claude-haiku-5-5"
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


async def main(argv=None):
    args = options(argv)
    destination = args.output or ROOT / "reports" / f"anthropic-smoke-{args.model}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # No CLI key argument, saved credential, environment dump, or raw HTTP log.
    api_key = os.environ.get("ANTHROPIC_API_KEY") or getpass.getpass("Anthropic API key (hidden): ")
    budget = Budget(Limits(model_calls=1, model_tokens=4096, retries=0, seconds=45))
    provider = AnthropicProvider(args.model, api_key=api_key)
    input_price, output_price = (0.10, 0.50) if args.model == "claude-haiku-5-5" else (4, 20)
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": provider.model,
        "api_version": provider.api_version,
        "scope": "one authored passage: local retrieval, cited model answer, exact-byte check",
        "max_input_tokens": provider.max_input_tokens,
        "max_output_tokens": provider.max_output_tokens,
        "effort": "low",
        "retries": 0,
        "price_usd_per_million": {"input": input_price, "output": output_price},
        "pricing_source": "https://platform.claude.com/docs/en/about-claude/pricing",
        "status": "failed",
    }
    try:
        with (
            tempfile.TemporaryDirectory() as directory,
            Index(Path(directory) / "index.sqlite") as index,
        ):
            index.ingest(ROOT / "examples/corpus")
            session = index.session(limits=Limits(source_bytes=512, steps=4))
            candidates = session.search(
                "Revoke a session by deleting its Redis session key", limit=1
            )
            evidence = [
                item.evidence
                for item in session.read(candidates.items[0].span_ids)
                if item.evidence
            ]
            assert len(evidence) == 1
            item = evidence[0]
            original = (ROOT / "examples/corpus" / item.span.source).read_bytes()
            assert original[item.span.start : item.span.end] == item.text.encode()
            retrieval = Result(
                run_id="anthropic-smoke",
                revision=session.data.revision,
                query="How do I revoke a session? Answer in at most 12 words.",
                evidence=evidence,
                trace=[],
                usage=session.budget.usage,
                stop_reason="completed",
                policy="fixed",
            )
            response = await answer(retrieval.query, retrieval, provider, budget)
            assert not response.abstained and response.span_ids
            assert "redis" in response.text.lower() and "delet" in response.text.lower()
            report.update(
                status="passed",
                answer=response.model_dump(),
                source=item.span.source,
                span_id=item.span.id,
                source_sha256=hashlib.sha256(original).hexdigest(),
                exact_bytes_verified=True,
                citation_membership_verified=True,
            )
    except (NavconrError, TimeoutError, AssertionError) as exc:
        report["error"] = str(exc) or type(exc).__name__
    finally:
        report["usage"] = provider.last_usage
        report["ledger"] = budget.usage.model_dump()
        report["preflight_input_tokens"] = provider.preflight_input_tokens
        report["provider_stop_reason"] = provider.last_stop_reason
        usage = provider.last_usage
        report["estimated_cost_usd"] = (
            (usage["input_tokens"] * input_price + usage["output_tokens"] * output_price)
            / 1_000_000
            if usage
            else None
        )
        destination.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
