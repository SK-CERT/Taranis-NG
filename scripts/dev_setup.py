#!/usr/bin/env python3
"""Install everything needed to run this repository's test suites.

Run from the repository root. Builds one root ``.venv`` (dev tooling, pytest, and every
service's runtime dependencies) plus ``src/gui-v3/node_modules``. See ``docs/testing.md``
for why one environment rather than one per service.

Service dependencies go in with ``uv pip install`` rather than ``uv sync``: the services
are independent uv projects, so ``uv sync`` run from a service directory would build a
*separate* ``src/<service>/.venv``. Their exported requirement sets are merged and
installed additively into the one root environment instead. Where two services pin the
same transitive package differently the newer wins, which is safe because this venv only
runs tests — shipped images build from each service's own frozen ``uv.lock``.

Exits non-zero if any step fails.

Usage::

    python3 scripts/dev_setup.py            # python + gui deps (the common case)
    python3 scripts/dev_setup.py --all      # + playwright browsers + ansible tooling
    python3 scripts/dev_setup.py --check    # report what is missing, install nothing
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV = REPO_ROOT / ".venv"
VENV_BIN = VENV / "bin"
GUI_DIR = REPO_ROOT / "src" / "gui-v3"

# Backend services with their own pyproject + uv.lock. Their runtime dependencies are
# merged into the root .venv so the test suites can import them.
SERVICES: tuple[str, ...] = ("bots", "collectors", "core", "presenters", "publishers")

PIN_RE = re.compile(r"^([A-Za-z0-9._-]+)==([^ ;]+)(.*)$")

# The normalised PEP 440 subset uv emits in `uv export` pins, e.g. 1!2.3.4rc1.post2.dev3+local.
VERSION_RE = re.compile(
    r"^(?:(?P<epoch>\d+)!)?"
    r"(?P<release>\d+(?:\.\d+)*)"
    r"(?:(?P<pre_letter>a|b|rc)(?P<pre_num>\d+)?)?"
    r"(?:\.post(?P<post>\d+)?)?"
    r"(?:\.dev(?P<dev>\d+)?)?"
    r"(?:\+(?P<local>.+))?$",
)
PRE_RANK = {"a": 0, "b": 1, "rc": 2}

# epoch, release, pre-release, post-release, dev-release, local — see version_key().
VersionKey = tuple[int, tuple[int, ...], tuple[int, int], int, float, tuple[tuple[int, int, str], ...]]


def die(msg: str, code: int = 1) -> NoReturn:
    """Print an error and exit."""
    print(f"dev_setup: error: {msg}", file=sys.stderr)
    sys.exit(code)


def run(command: list[str], *, cwd: Path | None = None, quiet: bool = False) -> None:
    """Run a command, exiting with its output on failure."""
    result = subprocess.run(command, cwd=cwd, check=False, capture_output=quiet, text=True)
    if result.returncode != 0:
        if quiet and result.stdout:
            print(result.stdout, file=sys.stderr)
        if quiet and result.stderr:
            print(result.stderr, file=sys.stderr)
        die(f"command failed ({result.returncode}): {' '.join(command)}")


def find_uv() -> str:
    """Return the uv executable, preferring the repo-local one."""
    candidate = VENV_BIN / "uv"
    if candidate.is_file():
        return str(candidate)
    binary = shutil.which("uv")
    if binary is None:
        die(
            "uv not found on PATH or in .venv/bin.\n"
            "Bootstrap it once with your system package manager or:\n"
            "    curl -LsSf https://astral.sh/uv/install.sh | sh",
        )
    return binary


def version_key(version: str) -> VersionKey:
    """Order a PEP 440 version string the way ``packaging.version.Version`` would.

    Hand-rolled rather than imported: this script bootstraps the environment, so it runs
    on whatever bare interpreter the contributor (or CI) invoked it with, where nothing
    third-party — ``packaging`` included — is importable yet. It only has to order the
    normalised pins ``uv export`` emits; anything it cannot parse sorts lowest, so a
    version it does understand always wins.

    Ordering within one release follows PEP 440: ``1.0.dev1 < 1.0rc1 < 1.0 < 1.0.post1``.
    """
    match = VERSION_RE.match(version)
    if match is None:
        return (-1, (), (-1, 0), -1, 0.0, ())

    release = tuple(int(part) for part in match["release"].split("."))
    while len(release) > 1 and release[-1] == 0:  # 1.2.0 and 1.2 are the same version
        release = release[:-1]

    if match["pre_letter"]:
        pre = (PRE_RANK[match["pre_letter"]], int(match["pre_num"] or 0))
    elif match["dev"] is not None and match["post"] is None:
        pre = (-1, 0)  # a plain .devN precedes every pre-release of the same version
    else:
        pre = (len(PRE_RANK), 0)  # a final release follows every pre-release

    # A local segment ("1.0+cpu") outranks the same version without one; numeric parts of
    # it outrank alphanumeric ones, hence the (is_numeric, number, text) triples.
    local = tuple(
        (1, int(part), "") if part.isdigit() else (0, 0, part) for part in (match["local"] or "").replace("_", ".").split(".") if part
    )

    return (
        int(match["epoch"] or 0),
        release,
        pre,
        int(match["post"] or 0) if match["post"] is not None else -1,
        float(match["dev"] or 0) if match["dev"] is not None else float("inf"),
        local,
    )


def merge_service_requirements(uv: str, verbose: bool) -> Path:
    """Export every service's locked requirements and merge them into one file.

    Where two services pin the same package to different versions, the higher version
    wins — see the module docstring for why that is safe here.
    """
    best: dict[str, tuple[VersionKey, str]] = {}
    for service in SERVICES:
        service_dir = REPO_ROOT / "src" / service
        exported = subprocess.run(
            [uv, "export", "--no-hashes", "--no-emit-project", "--quiet"],
            cwd=service_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if exported.returncode != 0:
            print(exported.stderr, file=sys.stderr)
            die(f"uv export failed for src/{service}")

        for line in exported.stdout.splitlines():
            stripped = line.strip()
            # Skip comments, blanks, and the `../shared` path requirement (installed
            # separately and editable, so edits to src/shared reach the tests).
            if not stripped or stripped.startswith(("#", "..", "-e", "/")):
                continue
            match = PIN_RE.match(stripped)
            if match is None:
                continue
            name, version, remainder = match.group(1).lower(), match.group(2), match.group(3)
            # Drop environment-marker lines: this venv is one concrete platform, and the
            # markers are mostly win32/PyPy variants that would never install anyway.
            if ";" in remainder:
                continue
            parsed = version_key(version)
            if name not in best or parsed > best[name][0]:
                best[name] = (parsed, f"{name}=={version}")

    if verbose:
        print(f"dev_setup: merged {len(best)} pins from {len(SERVICES)} services")

    handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)  # noqa: SIM115
    with handle:
        handle.write("\n".join(pin for _, pin in sorted(best.values(), key=lambda item: item[1])) + "\n")
    return Path(handle.name)


def setup_python(uv: str, verbose: bool, *, with_ansible: bool) -> None:
    """Populate the root .venv with dev tooling, pytest and all service dependencies.

    Every dependency group goes into ONE ``uv sync``. A second sync would not add to the
    environment, it would redefine it: uv makes the venv match exactly the groups named,
    so syncing `ansible` afterwards would remove pytest and every service dependency
    installed below. For the same reason `dev` is always present — dropping it prunes
    ``.venv/bin/uv``, and no other uv exists to run the command that would restore it.
    """
    groups = ["--group", "dev", "--group", "test"]
    if with_ansible:
        groups += ["--group", "ansible"]
    print(f"dev_setup: syncing root .venv ({' + '.join(groups[1::2])} groups)...")
    run([uv, "sync", *groups, "--no-install-project"], cwd=REPO_ROOT)

    print("dev_setup: installing service runtime dependencies...")
    requirements = merge_service_requirements(uv, verbose)
    try:
        run([uv, "pip", "install", "--python", str(VENV_BIN / "python"), "-r", str(requirements)], cwd=REPO_ROOT)
    finally:
        requirements.unlink(missing_ok=True)

    # Editable so edits in src/shared are picked up by tests without a reinstall.
    print("dev_setup: installing src/shared (editable)...")
    run([uv, "pip", "install", "--python", str(VENV_BIN / "python"), "-e", "src/shared"], cwd=REPO_ROOT)


def setup_gui() -> None:
    """Install the GUI's node_modules (Vitest + Playwright live there)."""
    if shutil.which("npm") is None:
        die("npm not found on PATH. Install Node.js (see .nvmrc for the version) and re-run.")
    print("dev_setup: installing src/gui-v3 node_modules...")
    run(["npm", "ci"], cwd=GUI_DIR)


def setup_playwright() -> None:
    """Download the Playwright browsers used by the e2e suite."""
    print("dev_setup: installing Playwright browsers...")
    run(["npx", "playwright", "install", "--with-deps"], cwd=GUI_DIR)


def report_check() -> int:
    """Report which pieces are present, installing nothing."""
    checks: list[tuple[str, bool, str]] = [
        ("root .venv", (VENV_BIN / "python").is_file(), "python3 scripts/dev_setup.py"),
        ("pytest", _venv_has("pytest"), "python3 scripts/dev_setup.py"),
        ("ruff", (VENV_BIN / "ruff").is_file(), "python3 scripts/dev_setup.py"),
        ("gui node_modules", (GUI_DIR / "node_modules").is_dir(), "python3 scripts/dev_setup.py"),
        ("ansible-playbook", (VENV_BIN / "ansible-playbook").is_file(), "python3 scripts/dev_setup.py --all"),
    ]
    missing = 0
    for label, present, remedy in checks:
        print(f"  {'OK     ' if present else 'MISSING'} {label}" + ("" if present else f"   -> {remedy}"))
        missing += not present
    return 1 if missing else 0


def _venv_has(module: str) -> bool:
    """Whether the root .venv interpreter can import ``module``."""
    python = VENV_BIN / "python"
    if not python.is_file():
        return False
    probe = subprocess.run([str(python), "-c", f"import {module}"], capture_output=True, check=False)
    return probe.returncode == 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="also install Playwright browsers and the ansible tooling")
    parser.add_argument("--check", action="store_true", help="report what is missing without installing anything")
    parser.add_argument("--skip-gui", action="store_true", help="skip npm ci (Python-only contributors)")
    parser.add_argument("--verbose", action="store_true", help="print extra detail")
    args = parser.parse_args()

    if args.check:
        return report_check()

    uv = find_uv()
    setup_python(uv, args.verbose, with_ansible=args.all)
    if not args.skip_gui:
        setup_gui()
    if args.all:
        setup_playwright()

    print("\ndev_setup: done. Run the suites with:  python3 scripts/run_tests.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
