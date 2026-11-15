"""Run with: python examples/manual_navigation.py"""

from pathlib import Path

from navconr import Index

root = Path(__file__).parent
with Index(root.parent / ".navconr" / "example.sqlite") as index:
    index.ingest(root / "corpus")
    session = index.session()
    print(session.overview().model_dump_json(indent=2))
    for candidate in session.search("refresh tokens").items[:2]:
        for item in session.read(candidate.span_ids):
            if item.evidence:
                print(item.evidence.text)
        for target in session.follow(candidate.id).items:
            print("Reference:", target.title)
