"""Every satellite endpoint stays behind the shared API-key policy.

:mod:`shared.auth` holds the policy, and ``test_auth.py`` proves the policy itself is
right. This file proves the services actually *apply* it - which is a separate failure
mode, and the one that matters: for a long time the liveness endpoints were the single
exception, answering any caller. In a distributed deployment that endpoint is published
on the internet, so an accidental revert is a real exposure rather than a style slip.

Static analysis rather than HTTP: the satellites are not part of ``PYTEST_SUITES``
(scripts/run_tests.py runs core and shared), and standing each service's Flask app up
here would need its Docker secrets. Reading the source catches a removed decorator just
as well, and costs nothing.
"""

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parents[2]
SATELLITES = ("collectors", "bots", "presenters", "publishers")
DECORATOR = "api_key_required"


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _decorator_names(node: ast.FunctionDef) -> set[str]:
    """Names of the decorators applied to a function, however they are spelled."""
    names = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _resource_methods(module: ast.Module) -> list[ast.FunctionDef]:
    """Every HTTP handler defined on a Resource class in the module."""
    handlers = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef):
            handlers += [
                child for child in node.body if isinstance(child, ast.FunctionDef) and child.name in {"get", "post", "put", "delete", "patch"}
            ]
    return handlers


@pytest.mark.parametrize("service", SATELLITES)
def test_the_liveness_endpoint_requires_the_api_key(service: str) -> None:
    """An open isalive advertises the node to anyone who finds the host."""
    path = SRC_ROOT / service / "api" / "isalive.py"
    assert path.is_file(), f"{service} has no api/isalive.py"

    handlers = _resource_methods(_module(path))
    assert handlers, f"{service}: no HTTP handler found in isalive.py"
    for handler in handlers:
        assert DECORATOR in _decorator_names(handler), (
            f"{service}: isalive.{handler.name}() is not decorated with @{DECORATOR} - "
            f"that endpoint would answer unauthenticated, and in a distributed "
            f"deployment it is published on the internet."
        )


@pytest.mark.parametrize("service", SATELLITES)
def test_the_service_takes_its_policy_from_shared(service: str) -> None:
    """One implementation, not five: the copies had already begun to diverge."""
    source = (SRC_ROOT / service / "managers" / "auth_manager.py").read_text(encoding="utf-8")
    assert "from shared.auth import" in source, (
        f"{service}: managers/auth_manager.py no longer builds its decorator from shared.auth - the policy has been forked again."
    )
    assert "def api_key_required" not in source, f"{service}: managers/auth_manager.py defines its own api_key_required again."


@pytest.mark.parametrize("service", SATELLITES)
def test_no_endpoint_module_is_left_undecorated(service: str) -> None:
    """The other endpoint modules were already protected; keep them that way."""
    api_dir = SRC_ROOT / service / "api"
    for path in sorted(api_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for handler in _resource_methods(_module(path)):
            assert DECORATOR in _decorator_names(handler), f"{service}: {path.name}::{handler.name}() is unauthenticated"
