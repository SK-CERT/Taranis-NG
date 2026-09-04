#!/usr/bin/env python3
"""Run this repository's test suites through one entry point.

Run from the repository root. The same command backs local runs, the pre-commit hooks and
CI, so the three cannot drift apart.

Suites:

======================================================================================
``pytest``          Python unit tests, one pytest run per project (see ``PYTEST_SUITES``)
``vitest``          GUI unit/component tests (``npm run test:unit`` in src/gui-v3)
``ansible``         Playbook syntax check + ansible-lint
``e2e``             Playwright end-to-end tests. NOT in the default set: it builds and
                    boots a Docker stack and takes minutes.
======================================================================================

Every suite *skips* when its tooling is not installed, so a checkout that has only run
part of ``scripts/dev_setup.py`` can still commit. Pass ``--require`` to turn each skip
into a failure — CI does this, so a missing tool there is a red build rather than a
silently green one.

Exits non-zero if any selected suite fails.

Usage::

    python3 scripts/run_tests.py                    # default suites (everything but e2e)
    python3 scripts/run_tests.py --suite pytest     # one suite; repeatable
    python3 scripts/run_tests.py --all              # including e2e
    python3 scripts/run_tests.py --require          # CI: never skip
    python3 scripts/run_tests.py --suite pytest -- -k saml   # extra args go to the tool
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = REPO_ROOT / ".venv" / "bin"
GUI_DIR = REPO_ROOT / "src" / "gui-v3"

# Projects with a pytest suite, as directories under src/. Keep in sync with `testpaths`
# in the root pyproject.toml, which is what editors use. The other services have no
# tests yet - see "Known gaps" in docs/testing.md.
PYTEST_SUITES: tuple[str, ...] = ("core", "shared", "collectors", "presenters", "public_web", "publishers")

DEFAULT_SUITES: tuple[str, ...] = ("pytest", "vitest", "ansible")
ALL_SUITES: tuple[str, ...] = (*DEFAULT_SUITES, "e2e")

# Sentinel for "tooling absent, suite skipped" - distinct from pass (True)/fail (False).
SKIPPED = None


def note(msg: str) -> None:
    """Print a runner-prefixed line."""
    print(f"run_tests: {msg}", flush=True)


def heading(msg: str) -> None:
    """Print a suite banner."""
    print(f"\n=== {msg} ===", flush=True)


def missing(suite: str, what: str, remedy: str, *, require: bool) -> bool | None:
    """Handle absent tooling: fail under --require, otherwise skip."""
    if require:
        print(f"run_tests: error: {suite}: {what} not found. Install with:\n    {remedy}", file=sys.stderr)
        return False
    note(f"{suite}: {what} not installed - skipping (pass --require to make this an error)")
    return SKIPPED


def venv_python() -> Path | None:
    """The root .venv interpreter, if it exists and has pytest."""
    python = VENV_BIN / "python"
    if not python.is_file():
        return None
    probe = subprocess.run([str(python), "-c", "import pytest"], capture_output=True, check=False)
    return python if probe.returncode == 0 else None


def run_pytest(extra: list[str], *, require: bool) -> bool | None:
    """Run each project's pytest suite from its own directory."""
    python = venv_python()
    if python is None:
        return missing("pytest", "pytest", "python3 scripts/dev_setup.py", require=require)

    failed: list[str] = []
    for suite in PYTEST_SUITES:
        heading(f"pytest: src/{suite}")
        # cwd is the project dir so pytest picks up that project's own
        # [tool.pytest.ini_options] - testpaths and the pythonpath that makes its flat
        # layout importable without installing it.
        result = subprocess.run([str(python), "-m", "pytest", *extra], cwd=REPO_ROOT / "src" / suite, check=False)
        if result.returncode != 0:
            failed.append(suite)
    if failed:
        print(f"run_tests: pytest FAILED for: {', '.join(failed)}", file=sys.stderr)
        return False
    return True


def run_vitest(extra: list[str], *, require: bool) -> bool | None:
    """Run the GUI unit/component suite."""
    if not (GUI_DIR / "node_modules").is_dir():
        return missing("vitest", "src/gui-v3/node_modules", "python3 scripts/dev_setup.py", require=require)

    heading("vitest: src/gui-v3")
    # update-version.cjs writes git-info.json, which DashboardView.vue and its specs
    # import; a bare test run without it fails on a fresh checkout.
    subprocess.run(["node", "scripts/update-version.cjs"], cwd=GUI_DIR, check=False, capture_output=True)  # noqa: S607
    result = subprocess.run(["npm", "run", "test:unit", "--", *extra], cwd=GUI_DIR, check=False)  # noqa: S607
    return result.returncode == 0


def run_e2e(extra: list[str], *, require: bool) -> bool | None:
    """Run the Playwright end-to-end suite (boots a Docker stack)."""
    if not (GUI_DIR / "node_modules").is_dir():
        return missing("e2e", "src/gui-v3/node_modules", "python3 scripts/dev_setup.py --all", require=require)
    if shutil.which("docker") is None:
        return missing("e2e", "docker", "install Docker; the e2e stack needs it", require=require)

    heading("playwright e2e: src/gui-v3")
    result = subprocess.run(["npm", "run", "test:e2e", "--", *extra], cwd=GUI_DIR, check=False)  # noqa: S607
    return result.returncode == 0


def run_ansible(*, require: bool) -> bool | None:
    """Run the playbook syntax check and ansible-lint."""
    ansible_lint = VENV_BIN / "ansible-lint"
    playbook = VENV_BIN / "ansible-playbook"
    if not playbook.is_file() and shutil.which("ansible-playbook") is None:
        return missing("ansible", "ansible-core", "python3 scripts/dev_setup.py --all", require=require)

    heading("ansible: syntax check")
    # Delegate rather than reimplement: check_ansible_syntax.py also provisions the
    # collections cache that ansible-lint --offline depends on below.
    syntax_cmd = [sys.executable, str(REPO_ROOT / "scripts" / "check_ansible_syntax.py")]
    if require:
        syntax_cmd.append("--require-ansible")
    ok = subprocess.run(syntax_cmd, cwd=REPO_ROOT, check=False).returncode == 0

    if not ansible_lint.is_file() and shutil.which("ansible-lint") is None:
        result = missing("ansible", "ansible-lint", "python3 scripts/dev_setup.py --all", require=require)
        return ok if result is SKIPPED else False

    heading("ansible: lint")
    linter = str(ansible_lint) if ansible_lint.is_file() else "ansible-lint"
    env = {
        **__import__("os").environ,
        # --offline reads the cache that the syntax check just populated.
        "ANSIBLE_COLLECTIONS_PATH": str(REPO_ROOT / ".cache" / "ansible-collections"),
    }
    lint_ok = (
        subprocess.run(
            [linter, "--offline", "playbooks/", "roles/"],
            cwd=REPO_ROOT / "ansible",
            env=env,
            check=False,
        ).returncode
        == 0
    )
    return ok and lint_ok


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", action="append", choices=ALL_SUITES, help="run this suite (repeatable)")
    parser.add_argument("--all", action="store_true", help="run every suite, including e2e")
    parser.add_argument("--require", action="store_true", help="fail instead of skipping when tooling is missing")
    parser.add_argument("extra", nargs="*", help="extra arguments forwarded to the tool (put them after --)")
    args = parser.parse_args()

    if args.all:
        selected: tuple[str, ...] = ALL_SUITES
    elif args.suite:
        selected = tuple(dict.fromkeys(args.suite))
    else:
        selected = DEFAULT_SUITES

    results: dict[str, bool | None] = {}
    for suite in selected:
        if suite == "pytest":
            results[suite] = run_pytest(args.extra, require=args.require)
        elif suite == "vitest":
            results[suite] = run_vitest(args.extra, require=args.require)
        elif suite == "e2e":
            results[suite] = run_e2e(args.extra, require=args.require)
        elif suite == "ansible":
            results[suite] = run_ansible(require=args.require)

    passed = [name for name, ok in results.items() if ok is True]
    failed = [name for name, ok in results.items() if ok is False]
    skipped = [name for name, ok in results.items() if ok is SKIPPED]

    print()
    if passed:
        note(f"passed:  {', '.join(passed)}")
    if skipped:
        note(f"skipped: {', '.join(skipped)}")
    if failed:
        print(f"run_tests: FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    if not passed:
        note("nothing ran.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
