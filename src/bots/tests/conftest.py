"""Pytest bootstrap for the bots package.

Importing a bot reaches ``remote.core_api``, which reads the Docker secret
``/run/secrets/api_key`` (``config.Config``) and ``TARANIS_NG_CORE_URL`` at import time.
Tests have neither, so a stub ``config`` module and a placeholder URL are put in place
before any application import, as in the collectors and publishers suites.

``src/bots/__init__.py`` makes the service root a package called ``bots``, the same name as
the inner package; the inner one is bound first, the way the running service imports it
(its PYTHONPATH is /app). See the publishers suite for the long story.
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path

_SERVICE_ROOT = str(Path(__file__).resolve().parents[1])
if sys.path[:1] != [_SERVICE_ROOT]:
    sys.path.insert(0, _SERVICE_ROOT)

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

importlib.import_module("bots")
