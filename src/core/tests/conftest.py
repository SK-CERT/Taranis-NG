"""Pytest bootstrap for the core package.

The core modules read their Docker secrets from ``/run/secrets`` at import time
(``config.Config`` reads them in its class body, and ``managers.crypto_manager``
derives a key from them on import). Tests neither have nor need those secrets, so
a lightweight stub ``config`` module is injected before any application module is
imported: every ``Config.<ATTR>`` yields a throwaway string, which is all the
import-time code requires. This keeps the tests filesystem- and stack-independent
- they never touch ``/run/secrets`` or a database.
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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


@pytest.fixture
def make_authenticator() -> Callable:
    """Return a factory building a SamlAuthenticator around a fake provider row.

    The provider is a lightweight stand-in (id, name, config, secret) so no
    database is involved.
    """

    def _make(config: dict, *, name: str = "Taranis NG", provider_id: int = 1, secret: str | None = None) -> object:
        from auth.saml_authenticator import SamlAuthenticator  # noqa: PLC0415 - after the stub config is in place

        provider = types.SimpleNamespace(id=provider_id, name=name, config=config)
        provider.get_secret_plaintext = lambda: secret
        return SamlAuthenticator(provider)

    return _make


@pytest.fixture(autouse=True)
def _clear_federation_cache() -> Iterator[None]:
    """Isolate the in-process federation metadata cache between tests."""
    yield
    from auth import saml_federation  # noqa: PLC0415

    saml_federation._cache.clear()
