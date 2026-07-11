#!/usr/bin/env python3
"""Bump (or verify) the Taranis-NG release version across the repository.

Canonical source: ``VERSION.md``. Every other location listed below is derived
from it and kept in lockstep:

- ``pyproject.toml`` (root) ``[project] version``
- ``src/shared/pyproject.toml`` ``[project] version``
- ``src/{bots,collectors,core,presenters,publishers}/pyproject.toml``
  ``[project] version`` and the ``taranis-ng-shared==X`` dependency pin
- ``src/gui/package.json`` + ``package-lock.json``
- ``src/gui-v3/package.json`` + ``package-lock.json``

See ``scripts/README.md`` for the full flow and update workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# Release versions follow CalVer: YY.MM.PATCH (e.g. 26.05.1).
VERSION_RE = re.compile(r"^\d{2}\.\d{2}\.\d+$")

SERVICE_DIRS = ["src/bots", "src/collectors", "src/core", "src/presenters", "src/publishers"]

# All pyproject.toml files carrying a [project] version; services also pin taranis-ng-shared.
PYPROJECT_FILES = ["pyproject.toml", "src/shared/pyproject.toml", *(f"{d}/pyproject.toml" for d in SERVICE_DIRS)]

# npm projects: package.json plus the root-package version fields in package-lock.json.
NPM_DIRS = ["src/gui", "src/gui-v3"]

# uv projects whose uv.lock records project/shared versions and must be relocked after a bump.
UV_LOCK_DIRS = [".", *SERVICE_DIRS]


class DriftedPin(NamedTuple):
    """A version pin that disagrees with VERSION.md."""

    path: Path
    what: str
    found: str


def read_canonical_version() -> str:
    """Return the release version recorded in VERSION.md."""
    return (REPO_ROOT / "VERSION.md").read_text(encoding="utf-8").strip()


def collect_pyproject_pins(path: Path) -> list[tuple[str, str]]:
    """Return ``(what, found)`` version pins from a pyproject.toml."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    pins = [("[project] version", data["project"]["version"])]
    for spec in data["project"].get("dependencies", []):
        match = re.match(r"^taranis-ng-shared==(.+)$", spec)
        if match:
            pins.append(("taranis-ng-shared pin", match.group(1)))
    return pins


def collect_npm_pins(directory: Path) -> list[tuple[Path, str, str]]:
    """Return ``(path, what, found)`` version pins from package.json / package-lock.json."""
    pins = []
    package_json = directory / "package.json"
    pins.append((package_json, "version", json.loads(package_json.read_text(encoding="utf-8"))["version"]))
    lock = directory / "package-lock.json"
    if lock.exists():
        data = json.loads(lock.read_text(encoding="utf-8"))
        pins.append((lock, "version", data["version"]))
        pins.append((lock, 'packages."".version', data["packages"][""]["version"]))
    return pins


def check_lockstep(version: str) -> list[DriftedPin]:
    """Return every version pin that disagrees with ``version``."""
    drifted: list[DriftedPin] = []
    for rel in PYPROJECT_FILES:
        path = REPO_ROOT / rel
        drifted.extend(DriftedPin(path, what, found) for what, found in collect_pyproject_pins(path) if found != version)
    for rel in NPM_DIRS:
        drifted.extend(DriftedPin(path, what, found) for path, what, found in collect_npm_pins(REPO_ROOT / rel) if found != version)
    return drifted


def rewrite_pyproject(path: Path, version: str) -> None:
    """Rewrite the [project] version (and taranis-ng-shared pin, if any) in place."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'(?m)^(version\s*=\s*")[^"]+(")', lambda m: m.group(1) + version + m.group(2), text, count=1)
    text = re.sub(r'("taranis-ng-shared==)[^"]+(")', lambda m: m.group(1) + version + m.group(2), text, count=1)
    path.write_text(text, encoding="utf-8")


def rewrite_npm(directory: Path, version: str) -> None:
    """Rewrite the root-package version in package.json and package-lock.json."""
    for name in ("package.json", "package-lock.json"):
        path = directory / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = version
        if "packages" in data and "" in data.get("packages", {}):
            data["packages"][""]["version"] = version
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def relock() -> int:
    """Re-run ``uv lock`` for the root workspace and every service; return exit status."""
    uv = shutil.which("uv")
    if uv is None:
        print("error: uv not found on PATH; run 'uv lock' manually in: " + ", ".join(UV_LOCK_DIRS), file=sys.stderr)
        return 1
    for rel in UV_LOCK_DIRS:
        print(f"Relocking {rel} ...")
        result = subprocess.run([uv, "lock"], cwd=REPO_ROOT / rel, check=False)
        if result.returncode != 0:
            print(f"error: 'uv lock' failed in {rel}", file=sys.stderr)
            return result.returncode
    return 0


def bump(version: str, *, lock: bool) -> int:
    """Write ``version`` to VERSION.md and all derived pins, then relock uv projects."""
    (REPO_ROOT / "VERSION.md").write_text(version + "\n", encoding="utf-8")
    for rel in PYPROJECT_FILES:
        rewrite_pyproject(REPO_ROOT / rel, version)
    for rel in NPM_DIRS:
        rewrite_npm(REPO_ROOT / rel, version)
    print(f"Version pins updated to {version}.")
    if not lock:
        print("Skipped 'uv lock' (--no-lock); the check-locks CI job will fail until the locks are refreshed.")
        return 0
    return relock()


def main() -> int:
    """CLI entry point: bump to a new version, or ``--check`` lockstep with VERSION.md."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="new release version (YY.MM.PATCH), e.g. 26.08.1")
    parser.add_argument("--check", action="store_true", help="verify all pins match VERSION.md instead of bumping")
    parser.add_argument("--no-lock", action="store_true", help="skip running 'uv lock' after a bump")
    args = parser.parse_args()

    if args.check:
        if args.version:
            parser.error("--check takes no version argument (VERSION.md is the source of truth)")
        version = read_canonical_version()
        drifted = check_lockstep(version)
        if not drifted:
            return 0
        print(f"Release version lockstep check failed. VERSION.md says {version!r} but:", file=sys.stderr)
        for drift in drifted:
            print(f"  {drift.path.relative_to(REPO_ROOT)} :: {drift.what} is {drift.found!r}", file=sys.stderr)
        print(f"\nRe-align with: python3 scripts/bump_version.py {version}", file=sys.stderr)
        return 1

    if not args.version:
        parser.error("a new version is required unless --check is given")
    if not VERSION_RE.match(args.version):
        parser.error(f"version {args.version!r} does not match the YY.MM.PATCH scheme (e.g. 26.08.1)")
    return bump(args.version, lock=not args.no_lock)


if __name__ == "__main__":
    raise SystemExit(main())
