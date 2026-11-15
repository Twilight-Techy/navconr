import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
destination = ROOT / "paper" / "figures"
destination.mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
styles = {
    "lexical": ("#54749c", "o"),
    "fixed": ("#2d7861", "s"),
    "adaptive": ("#c97b49", "^"),
    "no_summaries": ("#8f6a9d", "D"),
}
for axis, split in zip(axes, ["dev", "heldout"], strict=True):
    report = json.loads((ROOT / "reports" / f"smoke-{split}.json").read_text())
    for method, (color, marker) in styles.items():
        rows = sorted(
            (r for r in report["summary"] if r["method"] == method), key=lambda r: r["budget"]
        )
        axis.plot(
            [r["budget"] for r in rows],
            [r["evidence_recall"] for r in rows],
            color=color,
            marker=marker,
            label=method,
            linewidth=1,
            markersize=6,
        )
    axis.set(
        title=f"{split} fixture partition",
        xlabel="Source-evidence byte budget",
        xticks=[512, 2048],
        ylim=(0, 1.04),
    )
    axis.grid(alpha=0.2)
axes[0].set_ylabel("Required-evidence group recall")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
fig.suptitle("Authored software fixtures — no independent human review", fontsize=11)
fig.tight_layout(rect=(0, 0.10, 1, 0.94))
for suffix in ["png", "svg"]:
    fig.savefig(destination / f"recall.{suffix}", dpi=180)
print("Wrote paper/figures/recall.png and .svg.")
