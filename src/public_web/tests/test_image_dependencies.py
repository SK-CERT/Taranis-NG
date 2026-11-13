"""public-web starts with the packages its image has, and no more.

The test environment is one venv with every service's dependencies, but the public-web image
installs only those in ``pyproject.toml`` (and what they need), with the shared package and its
own declared dependencies. ``shared.common`` needs BeautifulSoup, which only core and the
collectors install: importing it from public-web passed every test and crashed the container
at start. Here the app is imported in a process that can load nothing the image would not have.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

PUBLIC_WEB = Path(__file__).parents[1]

IMAGE_ONLY = textwrap.dedent(
    """
    import importlib.abc
    import importlib.metadata as metadata
    import sys
    import tomllib
    from pathlib import Path

    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    def wanted(requirement, extras):
        marker = requirement.marker
        return marker is None or any(marker.evaluate({"extra": extra}) for extra in extras or {""})

    # Every distribution the image installs: the dependencies, theirs, and so on.
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    todo = [Requirement(text) for text in project["dependencies"]]
    installed = set()
    while todo:
        requirement = todo.pop()
        name = canonicalize_name(requirement.name)
        if name in installed:
            continue
        installed.add(name)
        try:
            needs = metadata.requires(name) or []
        except metadata.PackageNotFoundError:
            continue
        todo.extend(need for need in map(Requirement, needs) if wanted(need, requirement.extras))

    # Modules of any other installed distribution cannot be imported.
    absent = {
        module
        for module, distributions in metadata.packages_distributions().items()
        if not any(canonicalize_name(distribution) in installed for distribution in distributions)
    }

    class NotInTheImage(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.partition(".")[0] in absent:
                raise ModuleNotFoundError(f"No module named {fullname!r} in the public-web image")
            return None

    sys.meta_path.insert(0, NotInTheImage())
    import lib.web.app  # noqa: F401
    print("imported")
    """,
)


def test_the_app_imports_with_only_what_the_image_installs() -> None:
    environment = {**os.environ, "PUBLIC_WEB_API_KEY": "test-key", "PYTHONWARNINGS": "ignore"}
    result = subprocess.run(  # noqa: S603 - our own interpreter and script
        [sys.executable, "-c", IMAGE_ONLY],
        cwd=PUBLIC_WEB,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr[-3000:]
    assert result.stdout.strip().endswith("imported")
