#!/usr/bin/env python3
"""Verify the sdist and wheel don't include sensitive paths.

Run: uv run python scripts/check_release_build.py
"""
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# Substring patterns; a match anywhere in an archive member path is a violation.
# Covers secrets, the whole test tree, dev/eval scaffolding, and every local-only
# planning/strategy doc (step*, remaining*, audit/backlog/changes/plan, go-to-market).
SENSITIVE_PATTERNS = [
    ".env",
    "docs/raw/",
    "docs/graphify/",
    "tests/",
    "evals/",
    "mcp-builder/",
    ".local.md",
    "step5.md",
    "step6.md",
    "step7.md",
    "step8.md",
    "step9.md",
    "step10.md",
    "remaining",
    "AUDIT.md",
    "BACKLOG.md",
    "changes.md",
    "plan.md",
    "launch.md",
    "launch/",
    "new.md",
    "marketing.md",
    "new_websites.md",
]


def check_zip(path: Path, label: str) -> list[str]:
    violations = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            for pat in SENSITIVE_PATTERNS:
                if pat in name:
                    violations.append(f"  {label}: {name!r} matches pattern {pat!r}")
    return violations


def check_tar(path: Path, label: str) -> list[str]:
    violations = []
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            for pat in SENSITIVE_PATTERNS:
                if pat in member.name:
                    violations.append(f"  {label}: {member.name!r} matches {pat!r}")
    return violations


def main() -> int:
    print("Building distributions...")
    result = subprocess.run(["uv", "build"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        return 1

    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))

    if not wheels or not sdists:
        print(f"Expected wheel + sdist in dist/, got: {list(dist_dir.iterdir())}")
        return 1

    all_violations: list[str] = []
    for whl in wheels:
        all_violations.extend(check_zip(whl, f"wheel:{whl.name}"))

    for sdist in sdists:
        all_violations.extend(check_tar(sdist, f"sdist:{sdist.name}"))

    if all_violations:
        print("FAIL — sensitive paths found in build artifacts:")
        for v in all_violations:
            print(v)
        return 1

    print(
        f"OK — {len(wheels)} wheel(s), {len(sdists)} sdist(s) checked. No sensitive paths."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
