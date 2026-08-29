"""Pytest bootstrap for the presenters package.

Importing the application packages reads the Docker secret ``/run/secrets/api_key``
at import time (``config.Config``). Tests have no secrets, so a stub ``config``
module is injected before any application import: every ``Config.<ATTR>``
yields a throwaway string, which is all the import-time code requires. The
core package's conftest does the same for the core service.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# Make the service importable when the suite runs from the repo root (the
# aggregate testpaths config) as well as from src/presenters: `presenters` then
# resolves to the inner package at src/presenters/presenters. Appended, not
# prepended, so a root-level pythonpath (src/core, src/shared) keeps priority
# for any same-named top-level module.
_SERVICE_ROOT = str(Path(__file__).resolve().parents[1])
if _SERVICE_ROOT not in sys.path:
    sys.path.append(_SERVICE_ROOT)

if "config" not in sys.modules:

    class _AnyConfig(type):
        """Metaclass yielding a throwaway value for any Config attribute access."""

        def __getattr__(cls, name: str) -> str:
            return "test-value"

    _module = types.ModuleType("config")

    class Config(metaclass=_AnyConfig):
        """Stub of ``config.Config`` for import-time use in tests."""

    _module.Config = Config
    sys.modules["config"] = _module
