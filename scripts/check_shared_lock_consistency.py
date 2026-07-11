#!/usr/bin/env python3
"""Verify src/shared dependency pins are reflected in all service uv.lock files.

`src/shared` is a uv workspace member with no ``uv.lock`` of its own. Its
``[project] dependencies`` pins flow into the 5 backend service locks via the
``[tool.uv.sources]`` path source declared in each service's ``pyproject.toml``.

This script catches the drift case where a dependency pin in
``src/shared/pyproject.toml`` is bumped but the service ``uv.lock`` files are not
relocked — by comparing every shared dependency's pinned version against the
version recorded for that package in each service ``uv.lock``.

Exits 0 if all shared deps match across all service locks, exit 1 (with a
drift report) otherwise.

See ``scripts/README.md`` for the overall tooling flow.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_PYPROJECT = REPO_ROOT / "src" / "shared" / "pyproject.toml"
SERVICES = ["bots", "collectors", "core", "presenters", "publishers"]


def normalize_version(version: str) -> str:
    """Normalize a version string for comparison.

    PEP 440 strips leading zeroes (``26.05.1`` -> ``26.5.1``), so a pin in
    ``pyproject.toml`` may not string-equal the version recorded in ``uv.lock``.
    Strip leading zeroes from each numeric segment to match uv's normalization.
    """
    parts = re.split(r"(\.)", version)
    normalized: list[str] = []
    for part in parts:
        if part == ".":
            normalized.append(part)
        elif part.isdigit():
            normalized.append(part.lstrip("0") or "0")
        else:
            normalized.append(part)
    return "".join(normalized)


def load_shared_deps(pyproject: Path) -> dict[str, str]:
    """Return ``{package: pinned_version}`` from src/shared's [project] dependencies."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    versions: dict[str, str] = {}
    for spec in deps:
        # Match "package==1.2.3" or "package[extra]==1.2.3".
        match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==(.+)$", spec)
        if match:
            name = match.group(1).lower().replace("_", "-")
            versions[name] = match.group(2)
    return versions


def load_lock_versions(lockfile: Path) -> dict[str, str]:
    """Return ``{package: version}`` parsed from a uv.lock ``[[package]]`` blocks."""
    if not lockfile.exists():
        return {}
    text = lockfile.read_text(encoding="utf-8")
    versions: dict[str, str] = {}
    # Match `name = "..."` followed (within a few lines) by `version = "..."`.
    for block in text.split("[[package]]"):
        name_match = re.search(r'^name = "([^"]+)"', block, re.MULTILINE)
        version_match = re.search(r'^version = "([^"]+)"', block, re.MULTILINE)
        if name_match and version_match:
            name = name_match.group(1).lower().replace("_", "-")
            versions[name] = version_match.group(1)
    return versions


def main() -> int:
    """Check shared deps against all service locks; return 0 if consistent, 1 otherwise."""
    if not SHARED_PYPROJECT.exists():
        print(f"error: {SHARED_PYPROJECT} not found", file=sys.stderr)
        return 1

    shared_deps = load_shared_deps(SHARED_PYPROJECT)
    if not shared_deps:
        print("No dependencies found in src/shared/pyproject.toml — nothing to check.")
        return 0

    drifts: list[str] = []
    for service in SERVICES:
        lockfile = REPO_ROOT / "src" / service / "uv.lock"
        lock_versions = load_lock_versions(lockfile)
        for dep, pinned in shared_deps.items():
            locked = lock_versions.get(dep)
            if locked is None:
                drifts.append(
                    f"  {service}: '{dep}' (pinned {pinned} in shared) missing from {service}/uv.lock",
                )
            elif normalize_version(locked) != normalize_version(pinned):
                drifts.append(
                    f"  {service}: '{dep}' shared pin {pinned} != lock version {locked}",
                )

    if drifts:
        print("Drift detected: src/shared dependency pins do not match service uv.lock files:", file=sys.stderr)
        for drift in drifts:
            print(drift, file=sys.stderr)
        print(file=sys.stderr)
        print("Re-lock the affected services: cd src/<service> && uv lock", file=sys.stderr)
        return 1

    print(f"OK: {len(shared_deps)} src/shared dependency pin(s) consistent across {len(SERVICES)} service lock(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
