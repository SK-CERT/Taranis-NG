"""Publishing a product runs the deliveries of its product preset.

A product preset sends the product in languages and product formats to publishing channels,
combined freely. Publishing renders each language of each format once and sends the output to
every channel it goes to, one publisher call per delivery; a failing delivery does not stop the
others. These tests pin that fan-out on the shapes product presets are made of: one format to
several channels, several formats to one channel, several languages to one channel, and a mix.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import publish
from flask import Flask

FORMATS = {
    1: "e-mail CZ",
    2: "JSON",
    3: "Mastodon post CZ",
    4: "PDF",
    5: "HTML",
}


def _delivery(delivery_id: int, format_id: int, channel: str | None, language: str | None = None) -> types.SimpleNamespace:
    product_format = types.SimpleNamespace(id=format_id, title=FORMATS[format_id])
    return types.SimpleNamespace(
        id=delivery_id,
        language=language,
        product_format_id=format_id,
        product_format=product_format,
        product_format_title=product_format.title,
        publishing_channel_id=channel,
        publishing_channel=types.SimpleNamespace(id=channel, name=channel) if channel else None,
    )


def _product(*deliveries: types.SimpleNamespace) -> types.SimpleNamespace:
    product_preset = types.SimpleNamespace(deliveries=list(deliveries))
    product_preset.formats = list({delivery.product_format_id: delivery.product_format for delivery in deliveries}.values())
    return types.SimpleNamespace(title="Advisory", links=[], language="en", product_preset=product_preset)


class _Calls:
    """What the endpoint rendered and sent."""

    def __init__(self) -> None:
        self.rendered: list[str] = []
        self.languages: list[str | None] = []
        self.sent: list[tuple[str, str]] = []


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Publish a product, rendering and sending through recording stubs.

    Returns a function ``(product, body, failing_formats, failing_channels) -> (calls, body, status)``.
    """

    def _run(
        product: types.SimpleNamespace,
        body: dict | None = None,
        *,
        failing_formats: tuple[str, ...] = (),
        failing_channels: tuple[str, ...] = (),
        raising_channels: tuple[str, ...] = (),
    ) -> tuple[_Calls, dict, HTTPStatus]:
        calls = _Calls()

        def render(_product: object, product_format: types.SimpleNamespace, language: str | None, _translations: object) -> tuple:
            calls.rendered.append(product_format.title)
            calls.languages.append(language)
            if product_format.title in failing_formats:
                return {"error": f"{product_format.title} failed"}, HTTPStatus.INTERNAL_SERVER_ERROR, None
            return {}, HTTPStatus.OK, {"data": f"rendered {product_format.title}"}

        def send(channel: types.SimpleNamespace, data: dict, *_args: object) -> tuple:
            calls.sent.append((data["data"], channel.name))
            if channel.name in raising_channels:
                message = "connection refused"
                raise ConnectionError(message)
            if channel.name in failing_channels:
                return {"error": "refused"}, HTTPStatus.INTERNAL_SERVER_ERROR
            return {}, HTTPStatus.OK

        monkeypatch.setattr(publish.auth_manager, "get_user_from_jwt", lambda: None)
        monkeypatch.setattr(publish, "load_product", lambda *_args: ({}, HTTPStatus.OK, product, None))
        monkeypatch.setattr(publish, "render_product", render)
        monkeypatch.setattr(publish.publishers_manager, "publish", send)

        app = Flask(__name__)
        with app.test_request_context(json={"product": {"id": 7}, **(body or {})}):
            response, status = publish.PublishProduct.post.__wrapped__(publish.PublishProduct())
        return calls, response, status

    return _run


def test_one_format_to_two_addresses_renders_once_and_sends_twice(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 1, "address 1"), _delivery(2, 1, "address 2"))

    calls, body, status = run(product)

    assert status == HTTPStatus.OK
    assert calls.rendered == ["e-mail CZ"]
    assert calls.sent == [("rendered e-mail CZ", "address 1"), ("rendered e-mail CZ", "address 2")]
    assert body["overall_success"] is True
    assert [(result["delivery_id"], result["format"], result["channel_name"]) for result in body["results"]] == [
        (1, "e-mail CZ", "address 1"),
        (2, "e-mail CZ", "address 2"),
    ]


def test_two_formats_to_one_sftp_render_and_send_each(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 4, "sftp"), _delivery(2, 5, "sftp"))

    calls, body, status = run(product)

    assert status == HTTPStatus.OK
    assert calls.rendered == ["PDF", "HTML"]
    assert calls.sent == [("rendered PDF", "sftp"), ("rendered HTML", "sftp")]
    assert all(result["success"] for result in body["results"])


def test_mixed_product_preset_makes_four_sends_from_three_renders(run) -> None:  # noqa: ANN001
    product = _product(
        _delivery(1, 2, "sftp"),
        _delivery(2, 1, "address 1"),
        _delivery(3, 1, "address 2"),
        _delivery(4, 3, "mastodon"),
    )

    calls, body, status = run(product, failing_channels=("address 1",))

    assert calls.rendered == ["JSON", "e-mail CZ", "Mastodon post CZ"]
    assert calls.sent == [
        ("rendered JSON", "sftp"),
        ("rendered e-mail CZ", "address 1"),
        ("rendered e-mail CZ", "address 2"),
        ("rendered Mastodon post CZ", "mastodon"),
    ]
    # The failing address does not stop the deliveries after it.
    assert [result["success"] for result in body["results"]] == [True, False, True, True]
    assert body["overall_success"] is False
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR


def test_a_publisher_that_raises_fails_only_its_delivery(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 1, "address 1"), _delivery(2, 1, "address 2"))

    calls, body, _status = run(product, raising_channels=("address 1",))

    assert len(calls.sent) == 2
    assert [result["success"] for result in body["results"]] == [False, True]
    assert body["results"][0]["result"] == {"error": "connection refused"}


def test_a_format_that_fails_to_render_fails_only_its_deliveries(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 2, "sftp"), _delivery(2, 1, "address 1"), _delivery(3, 1, "address 2"))

    calls, body, status = run(product, failing_formats=("e-mail CZ",))

    assert calls.rendered == ["JSON", "e-mail CZ"]
    assert calls.sent == [("rendered JSON", "sftp")]
    assert [result["success"] for result in body["results"]] == [True, False, False]
    assert body["results"][1]["result"] == {"error": "e-mail CZ failed"}
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR


def test_format_only_deliveries_are_not_published(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 4, None), _delivery(2, 2, "sftp"))

    calls, body, status = run(product)

    assert status == HTTPStatus.OK
    assert calls.rendered == ["JSON"]
    assert [result["delivery_id"] for result in body["results"]] == [2]


def test_only_the_ticked_deliveries_are_published(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 1, "address 1"), _delivery(2, 1, "address 2"), _delivery(3, 2, "sftp"))

    calls, body, _status = run(product, {"delivery_ids": [2]})

    assert calls.rendered == ["e-mail CZ"]
    assert calls.sent == [("rendered e-mail CZ", "address 2")]
    assert [result["delivery_id"] for result in body["results"]] == [2]


def test_a_delivery_without_a_language_renders_the_product_in_its_own(run) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 1, "address 1"), _delivery(2, 2, "sftp"))

    calls, body, status = run(product)

    assert status == HTTPStatus.OK
    assert calls.languages == ["en", "en"]
    assert [result["language"] for result in body["results"]] == ["en", "en"]


def test_each_language_of_a_format_is_rendered_once_and_sent_on_its_own(run) -> None:  # noqa: ANN001
    """Cyberfeed: Czech to two Mastodon accounts, English and Czech to one address, Slovak as PDF and HTML."""
    product = _product(
        _delivery(1, 3, "Mastodon CZ", "cs"),
        _delivery(2, 3, "Mastodon SK", "cs"),
        _delivery(3, 3, "address", "en"),
        _delivery(4, 3, "address", "cs"),
        _delivery(5, 4, "sftp", "sk"),
        _delivery(6, 5, "sftp", "sk"),
    )

    calls, body, status = run(product)

    assert status == HTTPStatus.OK
    assert list(zip(calls.rendered, calls.languages, strict=True)) == [
        ("Mastodon post CZ", "cs"),
        ("Mastodon post CZ", "en"),
        ("PDF", "sk"),
        ("HTML", "sk"),
    ]
    assert calls.sent == [
        ("rendered Mastodon post CZ", "Mastodon CZ"),
        ("rendered Mastodon post CZ", "Mastodon SK"),
        ("rendered Mastodon post CZ", "address"),
        ("rendered Mastodon post CZ", "address"),
        ("rendered PDF", "sftp"),
        ("rendered HTML", "sftp"),
    ]
    assert [result["language"] for result in body["results"]] == ["cs", "cs", "en", "cs", "sk", "sk"]


def test_the_language_of_the_request_is_not_the_one_published_in(run) -> None:  # noqa: ANN001
    """The deliveries say the languages; an older dialog's one language does not override them."""
    product = _product(_delivery(1, 1, "address 1", "cs"))

    calls, _body, status = run(product, {"language": "sk"})

    assert status == HTTPStatus.OK
    assert calls.languages == ["cs"]


@pytest.mark.parametrize("body", [None, {"delivery_ids": []}])
def test_nothing_to_send_is_refused_before_rendering(run, body: dict | None) -> None:  # noqa: ANN001
    product = _product(_delivery(1, 4, None), _delivery(2, 1, "address 1"))
    if body is None:
        product.product_preset.deliveries = product.product_preset.deliveries[:1]

    calls, response, status = run(product, body)

    assert status == HTTPStatus.BAD_REQUEST
    assert "Nothing to publish" in response["error"]
    assert calls.rendered == []


def test_a_product_that_cannot_be_loaded_is_not_published(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publish.auth_manager, "get_user_from_jwt", lambda: None)
    monkeypatch.setattr(publish, "load_product", lambda *_args: ({"error": "nope"}, HTTPStatus.UNAUTHORIZED, None, None))

    with Flask(__name__).test_request_context(json={"product": {"id": 7}}):
        body, status = publish.PublishProduct.post.__wrapped__(publish.PublishProduct())

    assert (body, status) == ({"error": "nope"}, HTTPStatus.UNAUTHORIZED)


# -- preview ----------------------------------------------------------------


def test_preview_defaults_to_the_first_format() -> None:
    product = _product(_delivery(1, 2, "sftp"), _delivery(2, 1, None))

    assert publish.preview_format(product, None).title == "JSON"
    assert publish.preview_format(product, "").title == "JSON"


@pytest.mark.parametrize("asked", [1, "1"])
def test_preview_renders_the_format_asked_for(asked: object) -> None:
    product = _product(_delivery(1, 2, "sftp"), _delivery(2, 1, None))

    assert publish.preview_format(product, asked).title == "e-mail CZ"


def test_preview_refuses_a_format_outside_the_product_preset() -> None:
    product = _product(_delivery(1, 2, "sftp"))

    assert publish.preview_format(product, 3) is None
    assert publish.preview_format(_product(), None) is None


# -- loading and rendering ---------------------------------------------------


def test_an_unsaved_product_needs_an_existing_product_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publish.ProductPreset, "find", classmethod(lambda _cls, _id: None))

    body, status, product, _translations = publish.load_product({"id": -1, "product_preset_id": 9}, None, "token")

    assert status == HTTPStatus.NOT_FOUND
    assert product is None
    assert "Product preset" in body["error"]


def test_a_refused_product_preset_answers_with_every_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ACL refusal used to return two values, which every caller failed to unpack."""
    stored = types.SimpleNamespace(product_preset_id=9)
    monkeypatch.setattr(publish.Product, "find", classmethod(lambda _cls, _id: stored))
    monkeypatch.setattr(publish.ProductPreset, "allowed_with_acl", classmethod(lambda _cls, *_args, **_kwargs: False))
    monkeypatch.setattr(publish.log_manager, "store_auth_error_activity", lambda *_args: None)

    body, status, product, _translations = publish.load_product({"id": 7}, None, "token")

    assert status == HTTPStatus.UNAUTHORIZED
    assert product is None
    assert body["error"]


def test_render_uses_the_format_it_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """The product no longer has one product format; the presenter input takes the delivery's."""
    seen = {}

    class _Input:
        def __init__(self, presenter_type: str, product: object, product_format: object) -> None:
            seen.update(presenter_type=presenter_type, product=product, product_format=product_format)

    class _Schema:
        def dump(self, _data: object) -> dict:
            return {"product": {}}

    class _Presenters:
        def __init__(self, url: str, key: str) -> None:
            seen["node"] = (url, key)

        def generate(self, data: dict) -> tuple:
            seen["generated_from"] = data
            return {"data": "x"}, HTTPStatus.OK

    monkeypatch.setattr(publish, "PresenterInput", _Input)
    monkeypatch.setattr(publish, "PresenterInputSchema", _Schema)
    monkeypatch.setattr(publish, "PresentersApi", _Presenters)
    monkeypatch.setattr(publish, "render_presenter_input", lambda payload, links: {**payload, "links": links})
    node = types.SimpleNamespace(api_url="http://presenters", api_key="key")
    presenter = types.SimpleNamespace(type="PDF_PRESENTER", node=node)
    product_format = types.SimpleNamespace(title="PDF", presenter=presenter, language=None, language_templates={})
    product = types.SimpleNamespace(links=[{"key": "k1", "url": "https://example.org"}])

    body, status, generated = publish.render_product(product, product_format)

    assert (body, status, generated) == ({}, HTTPStatus.OK, {"data": "x"})
    assert seen["product_format"] is product_format
    assert seen["presenter_type"] == "PDF_PRESENTER"
    assert seen["node"] == ("http://presenters", "key")
    assert seen["generated_from"]["links"] == product.links
    assert seen["generated_from"]["product"]["language"] is None


def test_a_format_without_a_presenter_is_refused() -> None:
    product_format = types.SimpleNamespace(title="PDF", presenter=None)

    body, status, generated = publish.render_product(types.SimpleNamespace(links=[]), product_format)

    assert status == HTTPStatus.BAD_REQUEST
    assert generated is None
    assert "PDF" in body["error"]
