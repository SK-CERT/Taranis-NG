"""News items entered by hand go into a group the user chooses; there are no manual sources.

An item typed in Assess used to need a "manual" OSINT source (of a MANUAL_COLLECTOR) in every
group it should land in. Now the dialog names the group: core checks that the user may access it,
stores the item without a source, records who entered it, and runs the attribute extraction rules
of that group on it.

The handlers are tested through ``__wrapped__`` with the caller injected the way ``auth_required``
would; the database is replaced by stand-ins.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from api import assess
from flask import Flask
from model.attribute_extraction_rule import AttributeExtractionRule
from model.news_item import NewsItemAggregate, NewsItemData, news_item_acl_conditions
from model.osint_source import OSINTSourceGroup
from sqlalchemy import or_
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Callable

# What the Add news item dialog sends.
ITEM = {
    "title": "Phishing wave",
    "review": "",
    "source": "",
    "link": "",
    "content": "",
    "author": "Alice",
    "hash": "",
    "published": "08.11.2026 - 10:00",
    "collected": "08.11.2026 - 10:00",
    "attributes": [],
}


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def caller(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    user = types.SimpleNamespace(id=7, username="alice", name="Alice Analyst")
    monkeypatch.setattr(assess.auth_manager, "get_user_from_jwt", lambda: user)
    monkeypatch.setattr(assess.log_manager, "store_user_auth_error_activity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(assess.sse_manager, "news_items_updated", lambda: None)
    return user


@pytest.fixture
def groups(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """The groups that exist, and whether the caller may access each."""
    access: dict[str, bool] = {}
    monkeypatch.setattr(
        OSINTSourceGroup,
        "find",
        classmethod(lambda _cls, group_id: types.SimpleNamespace(id=group_id) if group_id in access else None),
    )
    monkeypatch.setattr(
        OSINTSourceGroup,
        "allowed_with_acl",
        classmethod(lambda _cls, group_id, _user, **_kwargs: access.get(group_id, False)),
    )
    return access


@pytest.fixture
def added(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []

    def fake_add(_cls: type, data: dict, group_id: str, user: object) -> types.SimpleNamespace:
        calls.append((data, group_id, user))
        return types.SimpleNamespace(id=42)

    monkeypatch.setattr(NewsItemAggregate, "add_news_item", classmethod(fake_add))
    return calls


def _post(app: Flask, body: object) -> tuple[dict, HTTPStatus]:
    resource = assess.AddNewsItem()
    handler: Callable[[], tuple[dict, HTTPStatus]] = resource.post.__wrapped__.__get__(resource)
    with app.test_request_context("/", method="POST", json=body):
        return handler()


def test_the_item_goes_into_the_chosen_group(app: Flask, caller: types.SimpleNamespace, groups: dict, added: list) -> None:
    groups["g-intel"] = True

    body, status = _post(app, {**ITEM, "osint_source_group_id": "g-intel"})

    assert status == HTTPStatus.CREATED
    assert body == {"id": 42, "osint_source_group_id": "g-intel"}
    assert [(group_id, user) for _data, group_id, user in added] == [("g-intel", caller)]


@pytest.mark.usefixtures("caller", "groups")
@pytest.mark.parametrize("body", [ITEM, {**ITEM, "osint_source_group_id": ""}, {**ITEM, "osint_source_group_id": 5}, ["not", "an", "item"]])
def test_an_item_without_a_group_is_refused(app: Flask, added: list, body: object) -> None:
    _body, status = _post(app, body)

    assert status == HTTPStatus.BAD_REQUEST
    assert added == []


@pytest.mark.usefixtures("caller", "groups")
def test_an_unknown_group_is_refused(app: Flask, added: list) -> None:
    _body, status = _post(app, {**ITEM, "osint_source_group_id": "nope"})

    assert status == HTTPStatus.NOT_FOUND
    assert added == []


@pytest.mark.usefixtures("caller")
def test_a_group_the_user_may_not_access_is_refused(app: Flask, groups: dict, added: list) -> None:
    # The dialog only offers accessible groups, but the request may name any.
    groups["g-restricted"] = False

    _body, status = _post(app, {**ITEM, "osint_source_group_id": "g-restricted"})

    assert status == HTTPStatus.FORBIDDEN
    assert added == []


# ── the stored item ───────────────────────────────────────────────────────────────


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> list:
    """Run add_news_item for real, without a database: collect what it would store."""
    added_rows: list = []
    session = types.SimpleNamespace(added=added_rows, add=added_rows.append, commit=lambda: None)
    monkeypatch.setattr("model.news_item.db", types.SimpleNamespace(session=session))
    groups_created: list[str] = []
    monkeypatch.setattr(
        NewsItemAggregate,
        "create_new_for_group",
        classmethod(lambda _cls, _data, group_id: groups_created.append(group_id) or types.SimpleNamespace(id=1)),
    )
    monkeypatch.setattr("model.news_item.TagCloud.generate_tag_cloud_words", lambda _data: None)
    monkeypatch.setattr(AttributeExtractionRule, "get_all_enabled", classmethod(lambda _cls: []))
    session.groups_created = groups_created
    return session


def test_the_item_has_no_source_and_names_who_entered_it(stored: types.SimpleNamespace) -> None:
    user = types.SimpleNamespace(id=7, username="alice", name="Alice Analyst")

    # A source id sent by an older GUI is ignored: there are no manual sources any more.
    NewsItemAggregate.add_news_item({**ITEM, "osint_source_id": "old-manual-source"}, "g-intel", user)

    (data,) = [row for row in stored.added if isinstance(row, NewsItemData)]
    assert data.osint_source_id is None
    assert (data.entered_by, data.entered_by_user_id) == ("Alice Analyst", 7)
    assert stored.groups_created == ["g-intel"]


def test_a_user_without_a_display_name_is_named_by_username(stored: types.SimpleNamespace) -> None:
    NewsItemAggregate.add_news_item(ITEM, "g-intel", types.SimpleNamespace(id=8, username="bob", name=""))

    (data,) = [row for row in stored.added if isinstance(row, NewsItemData)]
    assert data.entered_by == "bob"


def test_a_migrated_item_shows_its_old_source_name() -> None:
    data = NewsItemData(None, "h", "t", "", "", "", "", "", None, "", None, [])
    data.source_label = "Manual - CSIRT"

    assert data.osint_source_name == "Manual - CSIRT"


# ── attribute extraction for items entered by hand ────────────────────────────────


def _rule(name: str, groups: list[str], pattern: str = r"CVE-\d{4}-\d{4,}") -> AttributeExtractionRule:
    return types.SimpleNamespace(
        name=name,
        attribute_key="cve",
        pattern=pattern,
        capture_group=0,
        max_matches=10,
        osint_source_groups=[types.SimpleNamespace(id=group_id) for group_id in groups],
        applies_to_source=lambda source: AttributeExtractionRule.applies_to_source(_rule(name, groups), source),
        applies_to_group=lambda group_id: AttributeExtractionRule.applies_to_group(
            types.SimpleNamespace(osint_source_groups=[types.SimpleNamespace(id=g) for g in groups]),
            group_id,
        ),
    )


@pytest.mark.parametrize(
    ("rule_groups", "group_id", "applies"),
    [([], "g1", True), ([], None, True), (["g1", "g2"], "g2", True), (["g1"], "g2", False), (["g1"], None, False)],
)
def test_a_rule_applies_to_an_item_entered_into_its_group(rule_groups: list[str], group_id: str | None, applies: bool) -> None:
    rule = types.SimpleNamespace(osint_source_groups=[types.SimpleNamespace(id=g) for g in rule_groups])

    assert AttributeExtractionRule.applies_to_group(rule, group_id) is applies


def test_the_rules_of_the_chosen_group_extract_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        AttributeExtractionRule,
        "get_all_enabled",
        classmethod(lambda _cls: [_rule("intel only", ["g-intel"]), _rule("other group", ["g-other"], r"INC-\d+")]),
    )
    data = NewsItemData(None, "h", "Exploited CVE-2026-12345 (INC-7)", "", "", "", "", "", None, "", None, [])

    NewsItemAggregate._apply_attribute_extraction(data, "g-intel")

    assert [(attribute.key, attribute.value) for attribute in data.attributes] == [("cve", "CVE-2026-12345")]


# ── who may see an item entered by hand ───────────────────────────────────────────


def test_the_group_acl_governs_an_item_without_a_source() -> None:
    # A manual item has no source or collector whose ACL entries could restrict it: the group
    # it is in stands in, for the item and its attachments (checked on a database copy too).
    sql = str(or_(*news_item_acl_conditions()).compile(dialect=postgresql.dialect()))

    assert "news_item_data.osint_source_id IS NULL" in sql
    assert "news_item_data.remote_source IS NULL" in sql
    assert "news_item_aggregate.osint_source_group_id = acl_entry.item_id" in sql
    assert sql.count("acl_entry.item_type =") == 3


# ── the link ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("link", "valid"),
    [
        ("https://example.com/advisory", True),
        ("http://10.0.0.1:8080/x?y=1", True),
        ("example.com", False),
        ("javascript:alert(1)", False),
        ("ftp://example.com/file", False),
        ("https://", False),
        ("https://exa mple.com", False),
        ("  ", False),
        (42, False),
    ],
)
def test_a_link_must_be_a_web_address(link: object, valid: bool) -> None:
    assert assess.is_web_link(link) is valid


@pytest.mark.usefixtures("caller")
def test_an_item_with_a_link_that_is_not_a_web_address_is_refused(app: Flask, groups: dict, added: list) -> None:
    groups["g-intel"] = True

    body, status = _post(app, {**ITEM, "osint_source_group_id": "g-intel", "link": "not a link"})

    assert status == HTTPStatus.BAD_REQUEST
    assert body["field"] == "link"
    assert added == []


@pytest.mark.usefixtures("caller", "added")
def test_an_item_without_a_link_is_fine(app: Flask, groups: dict) -> None:
    groups["g-intel"] = True

    _body, status = _post(app, {**ITEM, "osint_source_group_id": "g-intel", "link": ""})

    assert status == HTTPStatus.CREATED
