import argparse
import json
from pathlib import Path

from navconr import Index
from navconr.external import score_external

parser = argparse.ArgumentParser()
parser.add_argument("predictions")
parser.add_argument("--dataset", default="benchmarks/dataset.json")
parser.add_argument("--db", default=".navconr/benchmark.sqlite")
parser.add_argument("--split", choices=["dev", "heldout"], default="dev")
parser.add_argument("--output", required=True)
args = parser.parse_args()
with Index(args.db) as index:
    report = score_external(index, Path(args.dataset), Path(args.predictions), args.split)
Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
print(
    f"Scored {len(report['rows'])} supplied predictions; {len(report['missing_questions'])} missing."
)
