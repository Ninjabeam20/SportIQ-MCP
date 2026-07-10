#!/usr/bin/env python3
"""Validate the sdist and wheel against an explicit allowlist (REL-01/REL-02).

This is an allowlist, not a blocklist: every archive member must match one of a
small set of permitted paths, otherwise the build is rejected. A new root-level
file can therefore never ship silently. The check is deterministic — it builds
into a fresh temp dir so stale `dist/` artifacts can't pollute the result — and
also asserts exactly one wheel + one sdist for the pyproject version, a size
ceiling, and the uvx entry-point contract.

Run: uv run python scripts/check_release_build.py
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

# Hard ceiling per archive. The legitimate payload (src package + a handful of
# metadata/data files) is well under this; the historically broken sdist was
# ~89 MiB because media/wiki/.claude leaked in.
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024  # 2 MiB

# Allowlisted members inside the sdist, RELATIVE to the top-level
# `{name}-{version}/` directory. Mirrors [tool.hatch.build.targets.sdist].include
# plus PKG-INFO, which hatchling always generates.
SDIST_ALLOW = [
    "PKG-INFO",
    ".gitignore",  # hatchling force-adds this to every sdist; harmless (no secrets)
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "src/sportiq/*",  # fnmatch: '*' spans '/', so this covers src/sportiq/**
]

# Allowlisted members inside the wheel. The package is flattened to `sportiq/`
# and metadata lives under `{name}-{version}.dist-info/`.
WHEEL_ALLOW = [
    "sportiq/*",
    "*.dist-info/*",
]


def project_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def _matches(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def check_sdist(path: Path, version: str) -> list[str]:
    violations: list[str] = []
    prefix = f"sportiq_mcp-{version}/"
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            if member.isdir():
                continue
            name = member.name
            if not name.startswith(prefix):
                violations.append(f"  sdist: {name!r} lacks expected prefix {prefix!r}")
                continue
            rel = name[len(prefix):]
            if not _matches(rel, SDIST_ALLOW):
                violations.append(f"  sdist: {rel!r} is not on the allowlist")
    return violations


def check_wheel(path: Path) -> list[str]:
    violations: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not _matches(info.filename, WHEEL_ALLOW):
                violations.append(f"  wheel: {info.filename!r} is not on the allowlist")
    return violations


def check_uvx_contract(wheel: Path) -> list[str]:
    """The uvx contract: entry point + package data must survive into the wheel."""
    problems: list[str] = []
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
        ep_files = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
        if not ep_files:
            problems.append("  wheel: missing entry_points.txt")
        else:
            # Normalize whitespace so 'sportiq-mcp = sportiq.server:main' and the
            # spaceless form both match.
            compact = "".join(zf.read(ep_files[0]).decode().split())
            if "sportiq-mcp=sportiq.server:main" not in compact:
                problems.append(
                    "  wheel: entry point 'sportiq-mcp = sportiq.server:main' not found"
                )
        if not any(n.startswith("sportiq/") and n.endswith(".json") and "/data/" in n
                   for n in names):
            problems.append("  wheel: package data '*/data/*.json' missing")
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    version = project_version(root)
    print(f"Project version: {version}")

    with tempfile.TemporaryDirectory(prefix="sportiq-relcheck-") as tmp:
        out_dir = Path(tmp)
        print(f"Building distributions into clean temp dir {out_dir} ...")
        result = subprocess.run(
            ["uv", "build", "--out-dir", str(out_dir)],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Build failed:\n{result.stderr}")
            return 1

        wheels = sorted(out_dir.glob("*.whl"))
        sdists = sorted(out_dir.glob("*.tar.gz"))

        errors: list[str] = []

        if len(wheels) != 1:
            errors.append(f"  expected exactly 1 wheel, got {len(wheels)}: {[w.name for w in wheels]}")
        if len(sdists) != 1:
            errors.append(f"  expected exactly 1 sdist, got {len(sdists)}: {[s.name for s in sdists]}")

        expected_sdist = f"sportiq_mcp-{version}.tar.gz"
        expected_wheel_prefix = f"sportiq_mcp-{version}-"
        for s in sdists:
            if s.name != expected_sdist:
                errors.append(f"  sdist name {s.name!r} != expected {expected_sdist!r}")
        for w in wheels:
            if not w.name.startswith(expected_wheel_prefix):
                errors.append(f"  wheel name {w.name!r} != version {version}")

        for archive in (*wheels, *sdists):
            size = archive.stat().st_size
            if size > MAX_ARCHIVE_BYTES:
                errors.append(
                    f"  {archive.name}: {size} bytes exceeds ceiling {MAX_ARCHIVE_BYTES}"
                )

        for s in sdists:
            errors.extend(check_sdist(s, version))
        for w in wheels:
            errors.extend(check_wheel(w))
            errors.extend(check_uvx_contract(w))

        if errors:
            print("FAIL — release build check:")
            for e in errors:
                print(e)
            return 1

        print(
            f"OK — 1 wheel + 1 sdist for v{version}; every member allowlisted, "
            f"under {MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB, uvx entry point + package data present."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
