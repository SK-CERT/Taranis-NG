"""What a single pytest run from the repo root is allowed to promise.

Editors discover tests by issuing one pytest invocation per workspace folder, so the root
config decides what they can see. It is tempting to list every service there, and it does not
work: each service has a flat layout with its own top-level `managers`, `api`, `model` and
`remote`, and one interpreter binds each of those names once. Collecting several services
together means whichever conftest reaches sys.path last decides where `managers` resolves, and
the rest of the suites fail to import - not one assertion failure, but the whole run refusing
to collect.

So the root config may only list suites that its own `pythonpath` makes importable. The
complete set is `PYTEST_SUITES` in scripts/run_tests.py, which gives each service a process of
its own.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _root_pytest_config() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["pytest"]["ini_options"]


def test_every_root_testpath_is_importable_from_the_root_pythonpath() -> None:
    config = _root_pytest_config()
    on_path = {Path(entry).as_posix() for entry in config["pythonpath"]}

    # "src/core/tests" is served by the pythonpath entry "src/core".
    orphans = [path for path in config["testpaths"] if Path(path).parent.as_posix() not in on_path]

    assert orphans == [], (
        f"root testpaths lists {orphans}, whose service roots are not on the root pythonpath. "
        f"Adding a service here does not make it run - it makes the whole root run fail to "
        f"collect, because the services share top-level package names. Run the full set with "
        f"scripts/run_tests.py --suite pytest instead."
    )


def test_the_runner_still_covers_every_service() -> None:
    # Narrowing the root config is only acceptable because nothing was dropped: the runner is
    # what pre-commit and CI invoke, and it is the list that has to stay complete.
    runner = (REPO_ROOT / "scripts" / "run_tests.py").read_text(encoding="utf-8")
    declared = next(line for line in runner.splitlines() if line.startswith("PYTEST_SUITES"))

    for service in ("core", "shared", "collectors", "presenters", "public_web", "publishers"):
        assert f'"{service}"' in declared, f"{service} is no longer run by scripts/run_tests.py"
        assert (REPO_ROOT / "src" / service / "tests").is_dir()
