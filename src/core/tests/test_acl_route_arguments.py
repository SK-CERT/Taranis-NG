"""Every ACL-guarded endpoint must receive the id its ACL check reads.

``auth_required(permission, ACLCheck.X)`` looks the checked item up in the view's keyword
arguments under the name ``get_id_name_by_acl(ACLCheck.X)``. When that name is not one of the
route's URL parameters, every request to the endpoint fails with a KeyError (500) before the
view runs - which is what renaming the product checks to DISTRIBUTION_* once did. The unit tests of
the views call them past the decorator, so only this check sees the wiring.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

from api import analyze, assess, publish
from flask import Flask
from flask_restful import Api
from managers.auth_manager import ACLCheck, get_id_name_by_acl

if TYPE_CHECKING:
    import pytest

MODULES = (analyze, assess, publish)


def _acl_checks(method: object) -> tuple[ACLCheck, ...]:
    """The ACL checks the auth decorator closed over for this method."""
    for cell in getattr(method, "__closure__", None) or ():
        value = cell.cell_contents
        if isinstance(value, tuple) and value and all(isinstance(item, ACLCheck) for item in value):
            return value
    return ()


def _guarded_routes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, ACLCheck, set[str]]]:
    app = Flask(__name__)
    api = Api(app)
    for module in MODULES:
        if hasattr(module, "Permission"):
            monkeypatch.setattr(module, "Permission", types.SimpleNamespace(add=lambda *_args, **_kwargs: None))
        module.initialize(api)
    routes = []
    for rule in app.url_map.iter_rules():
        view = app.view_functions[rule.endpoint]
        resource = getattr(view, "view_class", None)
        for method_name in ("get", "post", "put", "delete", "patch"):
            routes.extend(
                (str(rule), f"{resource.__name__}.{method_name}", check, set(rule.arguments))
                for check in _acl_checks(getattr(resource, method_name, None))
            )
    return routes


def test_every_acl_check_names_an_id() -> None:
    assert [check.name for check in ACLCheck if get_id_name_by_acl(check) is None] == []


def test_every_guarded_route_passes_the_id_its_check_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    routes = _guarded_routes(monkeypatch)
    assert any(check is ACLCheck.PRODUCT_PRESET_ACCESS for _route, _view, check, _arguments in routes)

    broken = [
        f"{view} on {route}: {check.name} reads {get_id_name_by_acl(check)!r}"
        for route, view, check, arguments in routes
        if get_id_name_by_acl(check) not in arguments
    ]
    assert broken == []
