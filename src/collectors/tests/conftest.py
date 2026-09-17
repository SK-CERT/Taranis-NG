"""Pytest bootstrap for the collectors package.

Importing a collector reaches ``remote.core_api``, which reads the Docker secret
``/run/secrets/api_key`` (``config.Config``) and ``TARANIS_NG_CORE_URL`` at import time.
Tests have neither, so a stub ``config`` module and a placeholder URL are put in place
before any application import, exactly as the presenters and publishers suites do.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

# Make the service importable when the suite runs from the repo root (the aggregate
# testpaths config) as well as from src/collectors: `collectors` then resolves to the
# inner package at src/collectors/collectors. Appended, not prepended, so a root-level
# pythonpath keeps priority for any same-named top-level module.
_SERVICE_ROOT = str(Path(__file__).resolve().parents[1])
if _SERVICE_ROOT not in sys.path:
    sys.path.append(_SERVICE_ROOT)

# remote/core_api.py calls .removesuffix() on this at import time, so it must be a string.
os.environ.setdefault("TARANIS_NG_CORE_URL", "http://core.test")

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
