"""Build local release artifacts. Does not publish or select a license."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(arguments, cwd=ROOT):
    subprocess.run(arguments, cwd=cwd, check=True)


def main():
    run(["npm", "run", "build"], ROOT / "viewer")
    # Ship the verified static inspector with the Python wheel; retain JS sources in sdist.
    target = ROOT / "src" / "navconr" / "_viewer"
    if target.exists():
        # This generated directory is owned exclusively by this build script.
        shutil.rmtree(target)
    shutil.copytree(ROOT / "viewer" / "dist", target)
    run([sys.executable, "-m", "build", "--no-isolation"])
    artifacts = []
    for path in sorted((ROOT / "dist").glob("navconr-*")):
        if path.suffix not in {".whl", ".gz"}:
            continue
        artifacts.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (ROOT / "reports" / "release-artifacts.json").write_text(
        json.dumps(
            {
                "artifacts": artifacts,
                "publication": "not published",
                "license": "unresolved; no public distribution authorized",
                "live_model_checks": "deferred by user",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
