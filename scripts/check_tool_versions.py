#!/usr/bin/env python3
"""Enforce version lockstep for dev/CI tooling across repository files.

Canonical source: ``[dependency-groups] dev`` in ``pyproject.toml``.
See ``scripts/README.md`` for the full flow and update workflow.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tool name (as it appears in the dev group) -> pre-commit repo URL substring.
PRE_COMMIT_REPOS: dict[str, str] = {
    "ruff": "astral-sh/ruff-pre-commit",
    "djlint": "djlint/djLint",
}


class DriftedFile(NamedTuple):
    """A file whose pinned version disagrees with the source of truth."""

    path: Path
    tool: str
    expected: str
    found: str


def strip_leading_v(version: str) -> str:
    """Strip a leading 'v' (pre-commit tags)."""
    return version.removeprefix("v")


def load_dev_group_versions(pyproject: Path) -> dict[str, str]:
    """Return ``{tool: version}`` for ruff/djlint from the dev group."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    dev_deps = data.get("dependency-groups", {}).get("dev", [])

    versions: dict[str, str] = {}
    for spec in dev_deps:
        for tool in PRE_COMMIT_REPOS:
            # Match either "ruff==0.15.21" or "ruff==0.15.21".
            match = re.match(rf"^{re.escape(tool)}==(.+)$", spec)
            if match:
                versions[tool] = strip_leading_v(match.group(1))
    return versions


def extract_pre_commit_revs(precommit: Path) -> dict[str, str]:
    """Return ``{tool: rev}`` (leading 'v' stripped) from .pre-commit-config.yaml."""
    text = precommit.read_text(encoding="utf-8")
    revs: dict[str, str] = {}
    pattern = re.compile(
        r"- repo:\s*https://github\.com/(?P<repo>\S+)\s*\n\s*rev:\s*(?P<rev>\S+)",
    )
    for match in pattern.finditer(text):
        repo = match.group("repo")
        for tool, expected_repo in PRE_COMMIT_REPOS.items():
            if repo == expected_repo:
                revs[tool] = strip_leading_v(match.group("rev"))
    return revs


def extract_ruff_required_version(pyproject: Path) -> str | None:
    """Return ``[tool.ruff] required-version`` value (or None)."""
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^\[tool\.ruff\][^\n]*\n(?:[^\[]*\n)*?required-version\s*=\s*"(?P<val>[^"]+)"', text, re.MULTILINE)
    if match:
        return strip_leading_v(match.group("val"))
    return None


def check_lockstep(*, fix: bool = False) -> list[DriftedFile]:
    """Verify all pins agree with the dev group, rewriting them if ``fix``."""
    pyproject = REPO_ROOT / "pyproject.toml"
    precommit = REPO_ROOT / ".pre-commit-config.yaml"

    source_versions = load_dev_group_versions(pyproject)
    pre_commit_revs = extract_pre_commit_revs(precommit)
    ruff_pin = extract_ruff_required_version(pyproject)

    drifted: list[DriftedFile] = []

    # ruff required-version must equal the dev-group ruff pin exactly.
    if ruff_pin is not None and ruff_pin != source_versions.get("ruff"):
        drifted.append(DriftedFile(pyproject, "ruff", source_versions.get("ruff", ""), ruff_pin))

    # pre-commit rev: for both tools must match the dev-group version.
    for tool, rev in pre_commit_revs.items():
        if rev != source_versions.get(tool):
            drifted.append(DriftedFile(precommit, tool, source_versions.get(tool, ""), rev))

    if fix and drifted:
        apply_fixes(drifted, source_versions)

    return drifted


def apply_fixes(drifted: list[DriftedFile], expected: dict[str, str]) -> None:
    """Rewrite drifted files to match the dev group."""
    pyproject = REPO_ROOT / "pyproject.toml"
    precommit = REPO_ROOT / ".pre-commit-config.yaml"

    for drift in drifted:
        new_version = expected[drift.tool]
        if drift.path == pyproject and drift.tool == "ruff":
            text = pyproject.read_text(encoding="utf-8")
            text = re.sub(
                r'(\[tool\.ruff\][^\n]*\n(?:[^\[]*\n)*?required-version\s*=\s*")[^"]+(")',
                lambda m, v=new_version: m.group(1) + v + m.group(2),
                text,
                count=1,
            )
            pyproject.write_text(text, encoding="utf-8")
        elif drift.path == precommit:
            text = precommit.read_text(encoding="utf-8")
            repo_url = PRE_COMMIT_REPOS[drift.tool]
            newer = "v" + new_version
            pattern = re.compile(
                r"(- repo:\s*https://github\.com/" + re.escape(repo_url) + r"\s*\n\s*rev:\s*)(\S+)",
            )
            text, _ = pattern.subn(lambda m, v=newer: m.group(1) + v, text, count=1)
            precommit.write_text(text, encoding="utf-8")


def main() -> int:
    """CLI entry point: check (or ``--fix``) lockstep."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="realign drifted files to the dev group")
    args = parser.parse_args()

    drifted = check_lockstep(fix=args.fix)
    if not drifted or args.fix:
        return 0

    print(
        "Tool version lockstep check failed. The following pins disagree with the source of truth in pyproject.toml [dependency-groups] dev:",
        file=sys.stderr,
    )
    for drift in drifted:
        print(
            f"  {drift.path.relative_to(REPO_ROOT)} :: {drift.tool} expected {drift.expected!r}, found {drift.found!r}",
            file=sys.stderr,
        )
    print(
        "\nRe-run with --fix to align them, or update .pre-commit-config.yaml / pyproject.toml [tool.ruff] required-version to match.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
