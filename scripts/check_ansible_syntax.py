#!/usr/bin/env python3
"""Syntax-check all Ansible playbooks in this repository.

Run from the repository root. The script:

1. Locates ``ansible-playbook`` on PATH or in the repo-local ``.venv``. Ansible
   is an optional dependency group (see ``pyproject.toml``), so when it is not
   installed the check *skips* rather than failing — pass ``--require-ansible``
   to turn that skip into an error, as the Linting CI workflow does.
2. Installs required Ansible collections (``ansible/requirements.yml``) into
   ``.cache/ansible-collections`` if they are not already present.
3. Runs ``ansible-playbook --syntax-check`` against every playbook under
   ``ansible/playbooks/``.

Exits non-zero on any error. Used by the ``ansible-syntax-check`` pre-commit
hook and the Linting CI workflow.

Usage::

    python3 scripts/check_ansible_syntax.py           # check all playbooks
    python3 scripts/check_ansible_syntax.py --verbose # stream ansible output
    python3 scripts/check_ansible_syntax.py --require-ansible  # never skip
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
ANSIBLE_DIR = REPO_ROOT / "ansible"
PLAYBOOKS_DIR = ANSIBLE_DIR / "playbooks"
REQUIREMENTS_FILE = ANSIBLE_DIR / "requirements.yml"
# Project-local collection cache. Gitignored — not committed.
COLLECTIONS_CACHE = REPO_ROOT / ".cache" / "ansible-collections"
# Repo-local venv that `uv sync --group ansible` populates.
VENV_BIN = REPO_ROOT / ".venv" / "bin"


def die(msg: str, code: int = 1) -> NoReturn:
    """Print an error and exit."""
    print(f"check_ansible_syntax: error: {msg}", file=sys.stderr)
    sys.exit(code)


def find_ansible_binary(name: str) -> str | None:
    """Return the path to an ansible executable, or ``None`` if it is not installed.

    ``uv sync --group ansible`` installs the tooling into the repo-local
    ``.venv``, which is not on PATH unless the venv is activated — so fall back
    to looking there before declaring ansible missing.
    """
    binary = shutil.which(name)
    if binary is not None:
        return binary
    candidate = VENV_BIN / name
    return str(candidate) if candidate.is_file() else None


def require_ansible_binary(name: str) -> str:
    """Return the path to an ansible executable, or exit with instructions."""
    binary = find_ansible_binary(name)
    if binary is None:
        die(
            f"{name} not found on PATH or in {VENV_BIN}. Install with:\n    uv sync --group ansible\nand then re-run.",
        )
    return binary


def required_collection_names() -> list[str]:
    """Return the collection names listed in requirements.yml, e.g. community.docker."""
    names: list[str] = []
    for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*-\s*name:\s*([\w.]+)", line)
        if match:
            names.append(match.group(1))
    return names


def cache_is_complete() -> bool:
    """Return True when every required collection is really installed in the cache.

    Checking the directory alone is not enough. ``ansible-galaxy install -p`` is
    a no-op ("Nothing to do. All requested collections are already installed.")
    when the collections exist anywhere else on the search path — typically
    ~/.ansible/collections after following the README — which leaves the cache
    empty or half-written. The syntax check then pins
    ANSIBLE_COLLECTIONS_PATH to that cache and every module fails to resolve.
    """
    root = COLLECTIONS_CACHE / "ansible_collections"
    return all((root / ns / name / "MANIFEST.json").is_file() for ns, name in (n.split(".", 1) for n in required_collection_names()))


def ensure_collections(verbose: bool) -> None:
    """Install required collections into the project-local cache if missing.

    The cache lives at ``.cache/ansible-collections`` (gitignored). Operators
    can delete it to force a refresh; it is also rebuilt automatically whenever
    it is incomplete.
    """
    if not REQUIREMENTS_FILE.is_file():
        if verbose:
            print(f"check_ansible_syntax: no {REQUIREMENTS_FILE} — skipping collection install")
        return

    if cache_is_complete():
        if verbose:
            print(f"check_ansible_syntax: collections cache complete at {COLLECTIONS_CACHE}")
        return

    COLLECTIONS_CACHE.mkdir(parents=True, exist_ok=True)
    galaxy = require_ansible_binary("ansible-galaxy")
    cmd = [
        galaxy,
        "collection",
        "install",
        "-r",
        str(REQUIREMENTS_FILE),
        "-p",
        str(COLLECTIONS_CACHE),
        # --force: without it galaxy skips collections already present in the
        # user path and leaves this cache empty.
        "--force",
    ]
    if verbose:
        print(f"check_ansible_syntax: installing collections: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=not verbose, text=True, check=False)
    if result.returncode != 0:
        # Clean up partial install so the next run retries.
        shutil.rmtree(COLLECTIONS_CACHE, ignore_errors=True)
        sys.stderr.write(result.stderr if not verbose else "")
        die(
            "ansible-galaxy collection install failed (see above). Remove .cache/ansible-collections and re-run to retry.",
        )


def collect_playbooks() -> list[Path]:
    """Return every ``*.yml`` / ``*.yaml`` playbook under ansible/playbooks/."""
    if not PLAYBOOKS_DIR.is_dir():
        return []
    return sorted(p for p in PLAYBOOKS_DIR.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))


def syntax_check_playbook(
    playbook: Path,
    ansible_playbook: str,
    verbose: bool,
) -> tuple[bool, str]:
    """Run ``ansible-playbook --syntax-check`` on a single playbook.

    Returns ``(success, output)``.
    """
    env = {
        # Force our project-local collections cache to take priority so
        # operators who don't have the collections installed system-wide
        # still pass — and operators who DO have them installed aren't
        # surprised by a stale system install.
        "ANSIBLE_COLLECTIONS_PATH": str(COLLECTIONS_CACHE),
        # Roles live under ansible/roles/.
        "ANSIBLE_ROLES_PATH": str(ANSIBLE_DIR / "roles"),
        # Quiet the "implicit localhost does not match 'all'" noise from
        # site.yml when there's no [core] group in the inventory.
        "ANSIBLE_LOCALHOST_WARNING": "False",
        "ANSIBLE_DEPRECATION_WARNINGS": "False",
    }
    # Inherit PATH + a few essentials so ansible-playbook can find python.
    env["PATH"] = __import__("os").environ.get("PATH", "")
    env["HOME"] = __import__("os").environ.get("HOME", "")

    cmd = [
        ansible_playbook,
        "--syntax-check",
        # Use the tracked default inventory (localhost.yml). The check doesn't
        # need real hosts — syntax errors surface regardless of inventory.
        "-i",
        str(ANSIBLE_DIR / "inventory" / "localhost.yml"),
        str(playbook),
    ]
    if verbose:
        print(f"check_ansible_syntax: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def main() -> int:
    """Syntax-check every playbook and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream ansible-playbook output instead of suppressing it.",
    )
    parser.add_argument(
        "--require-ansible",
        action="store_true",
        help="Fail instead of skipping when ansible-core is not installed. Used by CI.",
    )
    args = parser.parse_args()

    ansible_playbook = find_ansible_binary("ansible-playbook")
    if ansible_playbook is None:
        if args.require_ansible:
            die(
                f"ansible-playbook not found on PATH or in {VENV_BIN}. Install with:\n    uv sync --group ansible\nand then re-run.",
            )
        # Ansible tooling is an optional dependency group (see pyproject.toml):
        # a contributor who never touches deployment shouldn't be blocked from
        # committing just because ansible-core isn't installed. CI passes
        # --require-ansible, so the check is still enforced before anything merges.
        print(
            "check_ansible_syntax: ansible-core not installed — skipping.\n  Run `uv sync --group ansible` to enable this check locally.",
        )
        return 0

    ensure_collections(args.verbose)

    playbooks = collect_playbooks()
    if not playbooks:
        print("check_ansible_syntax: no playbooks found under ansible/playbooks/")
        return 0

    failures: list[tuple[Path, str]] = []
    for playbook in playbooks:
        ok, output = syntax_check_playbook(playbook, ansible_playbook, args.verbose)
        if ok:
            print(f"  OK     {playbook.relative_to(REPO_ROOT)}")
        else:
            print(f"  FAIL   {playbook.relative_to(REPO_ROOT)}")
            failures.append((playbook, output))

    if failures:
        print("\ncheck_ansible_syntax: syntax errors found:", file=sys.stderr)
        for playbook, output in failures:
            print(f"\n--- {playbook.relative_to(REPO_ROOT)} ---", file=sys.stderr)
            print(output, file=sys.stderr)
        return 1

    print(f"\ncheck_ansible_syntax: {len(playbooks)} playbook(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
