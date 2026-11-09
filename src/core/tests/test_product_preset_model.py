"""Product preset validation, public-web visibility and ACL routing.

Deliveries combine languages, formats and channels freely: one format may go to several
channels, several formats to one channel and several languages to one channel, but the same
delivery only once. These tests run the model's checks against a stand-in session, so they need
neither an application nor a database.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

import pytest
from api import config as config_api
from flask import Flask
from flask_restful import Api
from model import product_preset as product_preset_module
from model.product import Product
from model.product_format import ProductFormat
from model.product_preset import ProductPreset, ProductPresetDelivery, ProductPresetPublicWeb, ProductPresetValidationError
from model.public_web import PublicWeb
from model.publishing_channel import PublishingChannel

if TYPE_CHECKING:
    from collections.abc import Callable


class _FakeSession:
    """Answers ``get`` from primed rows and records commits."""

    def __init__(self, rows: dict[tuple[type, object], object]) -> None:
        self.rows = rows
        self.commits = 0

    def __call__(self) -> _FakeSession:
        # Flask-SQLAlchemy's query property calls the session (a scoped session) when read.
        return self

    def get(self, model: type, key: object) -> object | None:
        return self.rows.get((model, key))

    def add(self, _row: object) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1


class _FakeQuery:
    """A name-clash query: ``filter(...).first()`` answers ``clash``."""

    def __init__(self, clash: object | None) -> None:
        self.clash = clash

    def filter(self, *_criteria: object) -> _FakeQuery:
        return self

    def first(self) -> object | None:
        return self.clash


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> Callable[..., _FakeSession]:
    """Prime the formats, channels and webs that exist, and an optional name clash."""

    def _prime(*, clash: object | None = None, extra: dict | None = None) -> _FakeSession:
        from managers import db_manager  # noqa: PLC0415 - after the stub config is in place

        rows: dict[tuple[type, object], object] = {}
        for format_id in (1, 2, 3):
            rows[ProductFormat, format_id] = types.SimpleNamespace(id=format_id)
        for channel_id in ("mail-1", "mail-2", "sftp"):
            rows[PublishingChannel, channel_id] = types.SimpleNamespace(id=channel_id)
        for web_id in (10, 11):
            web = PublicWeb(node_id=1, name=f"web {web_id}")
            web.id = web_id
            rows[PublicWeb, web_id] = web
        rows.update(extra or {})
        fake = _FakeSession(rows)
        monkeypatch.setattr(db_manager.db, "session", fake)
        monkeypatch.setattr(ProductPreset, "query", _FakeQuery(clash))
        return fake

    return _prime


def _data(*deliveries: tuple, **fields: object) -> dict:
    """Deliveries as ``(format, channel)`` or ``(format, channel, language)``."""
    return {
        "name": "Advisory",
        "deliveries": [
            {"product_format_id": delivery[0], "publishing_channel_id": delivery[1], "language": delivery[2] if len(delivery) > 2 else None}
            for delivery in deliveries
        ],
        **fields,
    }


def _pairs(deliveries: list[ProductPresetDelivery]) -> list[tuple[int, str | None, int]]:
    return [(delivery.product_format_id, delivery.publishing_channel_id, delivery.position) for delivery in deliveries]


def test_one_format_to_several_channels_and_several_formats_to_one(session: Callable[..., _FakeSession]) -> None:
    session()

    fields, deliveries, webs = ProductPreset._checked(
        _data((1, "mail-1"), (1, "mail-2"), (2, "sftp"), (3, "sftp"), (3, None)),
    )

    assert fields == {"name": "Advisory", "description": "", "icon": None, "public_web_enabled": False}
    assert _pairs(deliveries) == [(1, "mail-1", 0), (1, "mail-2", 1), (2, "sftp", 2), (3, "sftp", 3), (3, None, 4)]
    assert webs == []


def test_an_empty_channel_is_format_only(session: Callable[..., _FakeSession]) -> None:
    session()

    _fields, deliveries, _webs = ProductPreset._checked(_data((1, "")))

    assert _pairs(deliveries) == [(1, None, 0)]


@pytest.mark.parametrize(
    ("icon", "stored"),
    [
        ("mdi-rss", "mdi-rss"),
        ("  mdi-rss  ", "mdi-rss"),
        ("", None),
        (None, None),
        ("mdi-" + "x" * 60, "mdi-" + "x" * 46),
    ],
)
def test_the_icon_is_trimmed_and_an_empty_one_is_none(session: Callable[..., _FakeSession], icon: str | None, stored: str | None) -> None:
    session()

    fields, _deliveries, _webs = ProductPreset._checked(_data((1, None), icon=icon))

    assert fields["icon"] == stored


def test_a_product_preset_and_its_products_show_its_icon_or_the_default() -> None:
    preset = ProductPreset("Advisory")
    product = types.SimpleNamespace(product_preset=preset)
    assert preset.tag == Product.tag.fget(product) == "mdi-package-variant-closed"

    preset.icon = "mdi-rss"
    assert preset.tag == Product.tag.fget(product) == "mdi-rss"

    product.product_preset = None
    assert Product.tag.fget(product) == "mdi-package-variant-closed"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (_data((1, None), name="  "), "needs a name"),
        (_data((9, None)), "Format 9"),
        (_data((1, "gone")), "Channel gone"),
        (_data((1, "mail-1"), (1, "mail-1")), "twice"),
        (_data((1, None), (1, "")), "twice"),
        (_data((1, "mail-1", "cs"), (1, "mail-1", "cs")), "twice"),
        (_data((1, "mail-1", "Czech")), "Unknown language code"),
        (_data((1, None), public_web_ids=[10, 99]), "Public web 99"),
        (_data(), "at least one format"),
    ],
)
def test_what_cannot_be_saved_says_why(session: Callable[..., _FakeSession], data: dict, message: str) -> None:
    session()

    with pytest.raises(ProductPresetValidationError, match=message):
        ProductPreset._checked(data)


def test_names_are_unique_ignoring_case(session: Callable[..., _FakeSession]) -> None:
    session(clash=types.SimpleNamespace(id=4))

    with pytest.raises(ProductPresetValidationError, match="already exists"):
        ProductPreset._checked(_data((1, None), name="advisory"))


def test_a_public_web_only_product_preset_needs_no_format(session: Callable[..., _FakeSession]) -> None:
    session()

    fields, deliveries, webs = ProductPreset._checked(_data(public_web_enabled=True, public_web_ids=[11, 10, 11]))

    assert fields["public_web_enabled"] is True
    assert deliveries == []
    assert [web.id for web in webs] == [11, 10]


def test_an_update_keeps_the_rows_of_deliveries_that_stay(session: Callable[..., _FakeSession]) -> None:
    stored = ProductPreset("Advisory")
    kept = ProductPresetDelivery(1, "mail-1", 0)
    dropped = ProductPresetDelivery(2, "sftp", 1)
    stored.deliveries = [kept, dropped]
    fake = session(extra={(ProductPreset, 5): stored})

    updated = ProductPreset.update(5, _data((3, None), (1, "mail-1")), "admin")

    assert updated is stored
    assert updated.deliveries[1] is kept
    assert _pairs(updated.deliveries) == [(3, None, 0), (1, "mail-1", 1)]
    assert dropped not in updated.deliveries
    assert updated.updated_by == "admin"
    assert fake.commits == 1


def test_the_languages_of_one_format_go_to_one_channel_each_on_its_own(session: Callable[..., _FakeSession]) -> None:
    """Cyberfeed: English and Czech to one address, the product's own language to another."""
    session()

    _fields, deliveries, _webs = ProductPreset._checked(_data((1, "mail-1", "en"), (1, "mail-1", "cs"), (1, "mail-2", "")))

    assert [(delivery.language, delivery.product_format_id, delivery.publishing_channel_id) for delivery in deliveries] == [
        ("en", 1, "mail-1"),
        ("cs", 1, "mail-1"),
        (None, 1, "mail-2"),
    ]


def test_an_update_tells_deliveries_apart_by_language(session: Callable[..., _FakeSession]) -> None:
    stored = ProductPreset("Cyberfeed")
    czech = ProductPresetDelivery(1, "mail-1", 0, "cs")
    english = ProductPresetDelivery(1, "mail-1", 1, "en")
    stored.deliveries = [czech, english]
    session(extra={(ProductPreset, 5): stored})

    updated = ProductPreset.update(5, _data((1, "mail-1", "en"), (1, "mail-1", "sk")), "admin")

    assert updated.deliveries[0] is english
    assert updated.deliveries[1] not in (czech, english)
    assert [(delivery.language, delivery.position) for delivery in updated.deliveries] == [("en", 0), ("sk", 1)]


def _foreign_keys(table: object) -> dict[str, str | None]:
    return {f"{key.parent.name}->{key.column.table.name}": key.ondelete for key in table.foreign_keys}


def test_references_restrict_deletes_that_would_widen_or_drop_a_delivery() -> None:
    """Deleting a format, a channel or a targeted web must fail rather than change where products go."""
    assert _foreign_keys(ProductPresetDelivery.__table__) == {
        "product_preset_id->product_preset": "CASCADE",
        "product_format_id->product_format": None,
        "publishing_channel_id->publishing_channel": None,
    }
    assert _foreign_keys(ProductPresetPublicWeb.__table__) == {
        "product_preset_id->product_preset": "CASCADE",
        "public_web_id->public_web": None,
    }
    assert _foreign_keys(Product.__table__)["product_preset_id->product_preset"] is None
    assert not Product.__table__.c.product_preset_id.nullable


def test_updating_a_missing_product_preset_finds_nothing(session: Callable[..., _FakeSession]) -> None:
    session()

    assert ProductPreset.update(5, _data((1, None)), "admin") is None


# -- public web ---------------------------------------------------------------


def _web_settings(enabled: bool, targets: list[int]) -> types.SimpleNamespace:
    return types.SimpleNamespace(public_web_enabled=enabled, public_web_ids=targets)


@pytest.mark.parametrize(
    ("enabled", "targets", "web_id", "shown"),
    [
        (False, [], None, False),
        (False, [10], 10, False),
        (True, [], None, True),
        (True, [], 10, True),
        (True, [10], 10, True),
        (True, [10], 11, False),
        (True, [10], None, True),
    ],
)
def test_where_products_appear(enabled: bool, targets: list[int], web_id: int | None, shown: bool) -> None:
    assert ProductPreset.shown_on_web(_web_settings(enabled, targets), web_id) is shown


def test_formats_are_distinct_in_delivery_order() -> None:
    json, mail = types.SimpleNamespace(id=2), types.SimpleNamespace(id=1)
    deliveries = [
        types.SimpleNamespace(product_format_id=2, product_format=json),
        types.SimpleNamespace(product_format_id=1, product_format=mail),
        types.SimpleNamespace(product_format_id=2, product_format=json),
    ]

    assert ProductPreset.formats.fget(types.SimpleNamespace(deliveries=deliveries)) == [json, mail]


# -- ACL ------------------------------------------------------------------------


def test_product_access_is_the_access_to_its_product_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    from managers import db_manager  # noqa: PLC0415 - after the stub config is in place
    from model.product import Product  # noqa: PLC0415

    asked = []
    monkeypatch.setattr(
        ProductPreset,
        "allowed_with_acl",
        classmethod(lambda _cls, *args: asked.append(args) or True),
    )
    monkeypatch.setattr(db_manager.db, "session", _FakeSession({(Product, 7): types.SimpleNamespace(product_preset_id=3)}))

    assert ProductPreset.allowed_product_with_acl(7, "user", see=True, access=False, modify=True) is True
    assert asked == [(3, "user", True, False, True)]
    assert ProductPreset.allowed_product_with_acl(8, "user", see=True, access=False, modify=False) is False


def test_the_acl_join_uses_the_product_preset_item_type() -> None:
    from shared.schema.acl_entry import ItemType  # noqa: PLC0415

    assert ItemType.PRODUCT_PRESET.name == "PRODUCT_PRESET"
    assert not hasattr(ItemType, "PRODUCT_TYPE")
    assert product_preset_module.ItemType is ItemType


# -- configuration API ----------------------------------------------------------


def _required_permissions(method: Callable) -> set[str]:
    return {cell.cell_contents for cell in method.__closure__ or () if isinstance(cell.cell_contents, str)}


def test_the_configuration_routes_are_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_api, "Permission", types.SimpleNamespace(add=lambda *_args, **_kwargs: None))
    app = Flask(__name__)
    config_api.initialize(Api(app))
    rules = {str(rule): rule.endpoint for rule in app.url_map.iter_rules()}

    assert rules["/api/v1/config/product-presets"] == "productpresetsresource"
    assert rules["/api/v1/config/product-presets/<int:product_preset_id>"] == "productpresetresource"
    assert rules["/api/v1/config/product-presets/options"] == "productpresetoptionsresource"


@pytest.mark.parametrize(
    ("method", "permission"),
    [
        (config_api.ProductPresetsResource.get, "CONFIG_PRODUCT_PRESET_ACCESS"),
        (config_api.ProductPresetsResource.post, "CONFIG_PRODUCT_PRESET_CREATE"),
        (config_api.ProductPresetResource.put, "CONFIG_PRODUCT_PRESET_UPDATE"),
        (config_api.ProductPresetResource.delete, "CONFIG_PRODUCT_PRESET_DELETE"),
        (config_api.ProductPresetOptionsResource.get, "CONFIG_PRODUCT_PRESET_ACCESS"),
    ],
)
def test_each_endpoint_needs_its_permission(method: Callable, permission: str) -> None:
    assert _required_permissions(method) == {permission}


def test_a_product_preset_that_cannot_be_saved_answers_400_with_the_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(_data: dict, _user: str) -> None:
        message = "A format is listed twice with the same channel."
        raise ProductPresetValidationError(message)

    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: types.SimpleNamespace(name="admin"))
    monkeypatch.setattr(config_api.product_preset.ProductPreset, "add", staticmethod(refuse))

    with Flask(__name__).test_request_context(json={}):
        body, status = config_api.ProductPresetsResource.post.__wrapped__(config_api.ProductPresetsResource())

    assert status == 400
    assert body == {"error": "A format is listed twice with the same channel."}
