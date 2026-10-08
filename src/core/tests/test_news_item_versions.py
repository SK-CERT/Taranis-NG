"""News item versions: a newer revision of a stored item updates it instead of duplicating it.

A versioned item (a CSAF advisory, say) arrives with a `version_key` shared by all of its
revisions and a `hash` of the exact revision. Core keeps the newest revision on the item and
the ones it replaced as history. These tests pin the three decisions that matter - skip,
update, insert - and what an update does to the item and to the aggregates showing it.

Core tests run without a database, so the model runs on transient objects and the few
queries involved are replaced.
"""

from __future__ import annotations

import types
from datetime import UTC, datetime

import pytest
from model import news_item as news_item_module
from model.news_item import (
    VERSION_SCOPED_ATTRIBUTE_KEYS,
    NewNewsItemDataSchema,
    NewsItem,
    NewsItemAggregate,
    NewsItemAggregateSearchIndex,
    NewsItemAttribute,
    NewsItemData,
    NewsItemDataVersion,
    NewsItemVote,
)
from model.osint_source import OSINTSource
from model.tag_cloud import TagCloud


def make_data(
    *,
    version: str = "1.0.0",
    published: str = "01.09.2026 - 10:00",
    title: str = "Advisory",
    attributes: list | None = None,
    **fields: str,
) -> NewsItemData:
    """A transient news item data holding one revision of a versioned item."""
    return NewsItemData(
        id=fields.get("id", "item-1"),
        hash=fields.get("hash", f"hash-{version}"),
        title=title,
        review=fields.get("review", f"Review {version}"),
        source="https://example.com/csaf",
        link=fields.get("link", f"https://example.com/advisory/{version}"),
        published=published,
        author="Example PSIRT",
        collected=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        content=f"<p>Content {version}</p>",
        osint_source_id=fields.get("osint_source_id", "source-1"),
        attributes=attributes if attributes is not None else [],
        version=version,
        version_key=fields.get("version_key", "key-1"),
    )


def attribute(key: str, value: str) -> NewsItemAttribute:
    return NewsItemAttribute(key, value, "", None)


# --- apply_new_version -----------------------------------------------------------------


def test_a_new_version_moves_the_current_revision_to_history() -> None:
    stored = make_data(version="1.0.0")
    stored.apply_new_version(make_data(version="1.1.0", published="05.09.2026 - 08:00", title="Advisory, updated"))

    assert [version.version for version in stored.versions] == ["1.0.0"]
    snapshot = stored.versions[0]
    assert isinstance(snapshot, NewsItemDataVersion)
    assert (snapshot.hash, snapshot.title, snapshot.content) == ("hash-1.0.0", "Advisory", "<p>Content 1.0.0</p>")
    assert snapshot.superseded is not None


def test_a_new_version_takes_over_the_item_in_place() -> None:
    stored = make_data(version="1.0.0")
    stored.apply_new_version(make_data(version="1.1.0", published="05.09.2026 - 08:00", title="Advisory, updated", id="ignored"))

    # Same row: everything pointing at the item follows it to the new revision.
    assert stored.id == "item-1"
    assert (stored.version, stored.hash, stored.title) == ("1.1.0", "hash-1.1.0", "Advisory, updated")
    assert stored.published == "05.09.2026 - 08:00"
    assert stored.link == "https://example.com/advisory/1.1.0"


def test_attributes_of_a_new_version_are_merged_without_duplicates() -> None:
    stored = make_data(attributes=[attribute("CVE", "CVE-2026-0001"), attribute("Analyst note", "check vendor")])
    incoming = make_data(version="1.1.0", attributes=[attribute("CVE", "CVE-2026-0001"), attribute("CVE", "CVE-2026-0002")])

    stored.apply_new_version(incoming)

    pairs = sorted((a.key, a.value) for a in stored.attributes)
    # The user's attribute stays; the new CVE is added; the repeated one is not doubled.
    assert pairs == [("Analyst note", "check vendor"), ("CVE", "CVE-2026-0001"), ("CVE", "CVE-2026-0002")]


def test_attributes_describing_one_revision_are_replaced_not_merged() -> None:
    stored = make_data(attributes=[attribute("TLP", "AMBER"), attribute("CSAF_HASH", "mismatch"), attribute("CVE", "CVE-2026-0001")])
    incoming = make_data(version="1.1.0", attributes=[attribute("TLP", "CLEAR"), attribute("CSAF_HASH", "valid")])

    stored.apply_new_version(incoming)

    pairs = sorted((a.key, a.value) for a in stored.attributes)
    assert pairs == [("CSAF_HASH", "valid"), ("CVE", "CVE-2026-0001"), ("TLP", "CLEAR")]


def test_a_version_scoped_attribute_the_new_revision_lacks_is_dropped() -> None:
    # The integrity result of 1.0.0 says nothing about 1.1.0, even when 1.1.0 was not checked.
    stored = make_data(attributes=[attribute("CSAF_SIGNATURE", "valid")])
    stored.apply_new_version(make_data(version="1.1.0"))
    assert [a.key for a in stored.attributes] == []
    assert {"TLP", "CSAF_HASH", "CSAF_SIGNATURE"} == VERSION_SCOPED_ATTRIBUTE_KEYS


def test_the_remote_path_can_leave_attributes_to_its_own_handling() -> None:
    stored = make_data(attributes=[attribute("TLP", "AMBER")])
    stored.apply_new_version(make_data(version="1.1.0", attributes=[attribute("TLP", "CLEAR")]), merge_attributes=False)
    assert [(a.key, a.value) for a in stored.attributes] == [("TLP", "AMBER")]


# --- is_newer --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stored", "incoming", "expected"),
    [
        ("01.09.2026 - 10:00", "05.09.2026 - 08:00", True),
        ("05.09.2026 - 08:00", "01.09.2026 - 10:00", False),
        # The same minute: a second revision within a minute is still taken.
        ("01.09.2026 - 10:00", "01.09.2026 - 10:00", True),
        # Unreadable on either side: take the incoming revision, it was sent because it changed.
        ("yesterday", "01.09.2026 - 10:00", True),
        ("01.09.2026 - 10:00", "", True),
    ],
)
def test_revisions_are_ordered_by_publication_date(stored: str, incoming: str, expected: bool) -> None:
    assert make_data(published=stored).is_newer(make_data(published=incoming)) is expected


# --- add_news_items --------------------------------------------------------------------


class FakeSession:
    """Records what add_news_items asks the session to do."""

    def __init__(self) -> None:
        """Start with nothing added, executed or committed."""
        self.added: list = []
        self.executed: list[tuple[str, dict]] = []
        self.commits = 0

    def add(self, item: object) -> None:
        """Record an added object."""
        self.added.append(item)

    def execute(self, statement: object, params: dict | None = None) -> None:
        """Record a statement and its parameters."""
        self.executed.append((str(statement), params or {}))

    def commit(self) -> None:
        """Count a commit."""
        self.commits += 1


@pytest.fixture
def ingest(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Run add_news_items against a fake store instead of the database."""
    state = types.SimpleNamespace(
        session=FakeSession(),
        known_hashes=set(),
        by_key={},
        created=[],
        resurfaced=[],
        refreshed=[],
        collected=[],
        tag_cloud=[],
    )
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=state.session))
    monkeypatch.setattr(NewsItemData, "hash_known", classmethod(lambda _cls, value: value in state.known_hashes))
    monkeypatch.setattr(NewsItemData, "find_by_version_key", classmethod(lambda _cls, key: state.by_key.get(key)))
    monkeypatch.setattr(NewsItemAggregate, "create_new_for_all_groups", classmethod(lambda _cls, data: state.created.append(data)))
    monkeypatch.setattr(
        NewsItemAggregate,
        "_resurface",
        classmethod(lambda _cls, data, title, review: state.resurfaced.append((data, title, review))),
    )
    monkeypatch.setattr(
        NewsItemAggregate,
        "_refresh",
        classmethod(lambda _cls, data, title, review: state.refreshed.append((data, title, review))),
    )
    monkeypatch.setattr(TagCloud, "add_words", classmethod(lambda _cls, counts: state.tag_cloud.append(dict(counts))))
    monkeypatch.setattr(OSINTSource, "update_collected", classmethod(lambda _cls, source_id: state.collected.append(source_id)))

    def run(*items: NewsItemData) -> set:
        schema = types.SimpleNamespace(load=lambda _payload: list(items))
        monkeypatch.setattr(news_item_module, "NewNewsItemDataSchema", lambda **_kwargs: schema)
        return NewsItemAggregate.add_news_items([{} for _ in items])

    state.run = run
    return state


def test_a_known_revision_is_skipped(ingest: types.SimpleNamespace) -> None:
    ingest.known_hashes.add("hash-1.0.0")
    assert ingest.run(make_data(version="1.0.0")) == set()
    assert ingest.session.added == []
    assert ingest.created == []


def test_an_item_without_a_version_key_is_inserted_as_before(ingest: types.SimpleNamespace) -> None:
    item = make_data(version_key=None)
    item.version_key = None
    assert ingest.run(item) == {"source-1"}
    assert ingest.session.added == [item]
    assert ingest.created == [item]


def test_the_words_of_a_batch_reach_the_tag_cloud_at_once(ingest: types.SimpleNamespace) -> None:
    first = make_data(title="Kernel update", version_key=None, hash="h1")
    first.content = "<p>kernel kernel openssl</p>"
    second = make_data(title="OpenSSL update", version_key=None, hash="h2")
    second.content = "<p>openssl</p>"
    ingest.run(first, second)
    # One write per batch; a word counts once per item however often the item repeats it.
    (counts,) = ingest.tag_cloud
    assert (counts["kernel"], counts["openssl"], counts["update"]) == (1, 2, 2)


def test_a_batch_locks_its_identities_once_and_commits_once(ingest: types.SimpleNamespace) -> None:
    first = make_data(hash="h1", version_key="k1")
    second = make_data(hash="h2", version_key=None, id="item-2")
    ingest.run(first, second)

    ((statement, params),) = ingest.session.executed
    assert "pg_advisory_xact_lock" in statement
    # Two hashes and one version key, in one sorted pass.
    assert params["lock_ids"] == news_item_module._ingest_lock_ids([first, second])
    assert len(params["lock_ids"]) == 3
    assert params["lock_ids"] == sorted(params["lock_ids"])
    assert ingest.session.commits == 1


def test_lock_ids_depend_only_on_the_identities() -> None:
    one = make_data(hash="same", version_key="same")
    again = make_data(hash="same", version_key="same", id="item-2")
    # A hash and a version key with the same text are different identities.
    assert len(news_item_module._ingest_lock_ids([one])) == 2
    assert news_item_module._ingest_lock_ids([one, again]) == news_item_module._ingest_lock_ids([one])


def test_the_first_revision_of_a_versioned_item_is_inserted(ingest: types.SimpleNamespace) -> None:
    item = make_data()
    assert ingest.run(item) == {"source-1"}
    assert ingest.created == [item]
    assert ingest.collected == ["source-1"]


def test_a_newer_revision_updates_the_stored_item(ingest: types.SimpleNamespace) -> None:
    stored = make_data(version="1.0.0", title="Old title")
    ingest.by_key["key-1"] = stored
    incoming = make_data(version="1.1.0", published="05.09.2026 - 08:00", title="New title")

    assert ingest.run(incoming) == {"source-1"}

    # Nothing new is inserted: the stored item takes the revision and resurfaces.
    assert ingest.session.added == []
    assert ingest.created == []
    assert stored.version == "1.1.0"
    assert ingest.resurfaced == [(stored, "Old title", "Review 1.0.0")]
    assert ingest.collected == ["source-1"]


def test_an_older_revision_arriving_late_is_skipped(ingest: types.SimpleNamespace) -> None:
    stored = make_data(version="1.1.0", published="05.09.2026 - 08:00")
    ingest.by_key["key-1"] = stored

    assert ingest.run(make_data(version="1.0.0", published="01.09.2026 - 10:00")) == set()
    assert stored.version == "1.1.0"
    assert stored.versions == []
    assert ingest.resurfaced == []


def test_a_republished_copy_of_the_stored_revision_refreshes_it_in_place(ingest: types.SimpleNamespace) -> None:
    # Red Hat republishes an advisory under the same version every few hours, with a new date.
    stored = make_data(version="3", published="26.09.2026 - 12:18", title="RHSA-2026:9109: Update")
    ingest.by_key["key-1"] = stored
    incoming = make_data(version="3", published="29.09.2026 - 12:58", title="RHSA-2026:9109: Update", hash="hash-republished")
    incoming.content = "<p>Content 3, now with a CWE</p>"

    assert ingest.run(incoming) == {"source-1"}

    # The item takes the copy, but history does not repeat version 3 and nothing resurfaces.
    assert stored.versions == []
    assert (stored.hash, stored.published, stored.content) == ("hash-republished", "29.09.2026 - 12:58", "<p>Content 3, now with a CWE</p>")
    assert ingest.resurfaced == []
    assert ingest.refreshed == [(stored, "RHSA-2026:9109: Update", "Review 3")]


def test_a_new_revision_from_a_source_that_does_not_resurface_only_refreshes(ingest: types.SimpleNamespace) -> None:
    stored = make_data(version="1.0.0", title="Old title")
    ingest.by_key["key-1"] = stored
    incoming = make_data(version="1.1.0", published="05.09.2026 - 08:00", title="New title")
    incoming.resurface = False

    assert ingest.run(incoming) == {"source-1"}

    # The revision is stored and the one it replaced kept, but the item stays where it was.
    assert stored.version == "1.1.0"
    assert [version.version for version in stored.versions] == ["1.0.0"]
    assert ingest.resurfaced == []
    assert ingest.refreshed == [(stored, "Old title", "Review 1.0.0")]


def test_collected_items_resurface_unless_they_say_otherwise() -> None:
    payload = {
        "hash": "h",
        "title": "Advisory",
        "review": "",
        "source": "",
        "link": "",
        "published": "",
        "author": "",
        "collected": "01.09.2026 - 10:00",
        "content": "",
        "attributes": [],
    }
    schema = NewNewsItemDataSchema()
    # Collectors without the setting send nothing: their items resurface, as before.
    assert schema.load(payload).resurface is True
    assert schema.load({**payload, "resurface": False}).resurface is False


@pytest.mark.parametrize(("stored", "incoming", "expected"), [("3", "3", True), ("3", "4", False), (None, None, False), ("", "", False)])
def test_a_revision_is_named_by_its_version_label(stored: str | None, incoming: str | None, *, expected: bool) -> None:
    held, arrived = make_data(), make_data()
    held.version, arrived.version = stored, incoming
    assert held.is_same_revision(arrived) is expected


# --- _resurface ------------------------------------------------------------------------


@pytest.fixture
def aggregates(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Aggregates and news items showing one item, with the status updates recorded."""
    state = types.SimpleNamespace(news_items=[], aggregates={}, status_updates=[], indexed=[], index_commits=[], created=[])
    monkeypatch.setattr(NewsItem, "get_all_with_data", classmethod(lambda _cls, _data_id: state.news_items))
    monkeypatch.setattr(NewsItemAggregate, "find", classmethod(lambda _cls, aggregate_id: state.aggregates.get(aggregate_id)))
    monkeypatch.setattr(NewsItemAggregate, "update_status", classmethod(lambda _cls, aggregate_id: state.status_updates.append(aggregate_id)))

    def prepare(_cls: type, aggregate: object, *, commit: bool = True) -> None:
        state.indexed.append(aggregate)
        state.index_commits.append(commit)

    monkeypatch.setattr(NewsItemAggregateSearchIndex, "prepare", classmethod(prepare))
    monkeypatch.setattr(NewsItemAggregate, "create_new_for_all_groups", classmethod(lambda _cls, data: state.created.append(data)))

    def show(aggregate_id: int, *, title: str, description: str, members: int = 1) -> types.SimpleNamespace:
        news_item = types.SimpleNamespace(read=True, news_item_aggregate_id=aggregate_id)
        aggregate = types.SimpleNamespace(
            id=aggregate_id,
            title=title,
            description=description,
            created=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            news_items=[news_item] + [object() for _ in range(members - 1)],
        )
        state.news_items.append(news_item)
        state.aggregates[aggregate_id] = aggregate
        return aggregate

    state.show = show
    return state


def test_an_updated_item_becomes_unread_and_moves_to_its_new_time(aggregates: types.SimpleNamespace) -> None:
    aggregate = aggregates.show(1, title="Old title", description="Old review")
    data = make_data(title="New title", review="New review")
    data.collected = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)

    NewsItemAggregate._resurface(data, "Old title", "Old review")

    assert aggregates.news_items[0].read is False
    assert aggregate.created == datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
    assert (aggregate.title, aggregate.description) == ("New title", "New review")
    assert aggregates.status_updates == [1]
    assert aggregates.indexed == [aggregate]
    # Resurfacing is part of storing a batch, which commits once at its end.
    assert aggregates.index_commits == [False]


def test_a_title_an_analyst_changed_is_kept(aggregates: types.SimpleNamespace) -> None:
    aggregate = aggregates.show(1, title="Renamed by analyst", description="Old review")
    NewsItemAggregate._resurface(make_data(title="New title", review="New review"), "Old title", "Old review")
    assert aggregate.title == "Renamed by analyst"
    assert aggregate.description == "New review"


def test_a_grouped_aggregate_keeps_its_title(aggregates: types.SimpleNamespace) -> None:
    aggregate = aggregates.show(1, title="Old title", description="Old review", members=3)
    NewsItemAggregate._resurface(make_data(title="New title", review="New review"), "Old title", "Old review")
    assert (aggregate.title, aggregate.description) == ("Old title", "Old review")
    assert aggregates.news_items[0].read is False


def test_every_group_showing_the_item_is_updated(aggregates: types.SimpleNamespace) -> None:
    aggregates.show(1, title="Old title", description="Old review")
    aggregates.show(2, title="Old title", description="Old review")
    NewsItemAggregate._resurface(make_data(), "Old title", "Old review")
    assert aggregates.status_updates == [1, 2]
    assert all(news_item.read is False for news_item in aggregates.news_items)


def test_a_refreshed_item_takes_the_new_text_without_resurfacing(aggregates: types.SimpleNamespace) -> None:
    aggregate = aggregates.show(1, title="Old title", description="Old review")
    created = aggregate.created

    NewsItemAggregate._refresh(make_data(title="New title", review="New review"), "Old title", "Old review")

    assert (aggregate.title, aggregate.description) == ("New title", "New review")
    assert aggregates.news_items[0].read is True
    assert aggregate.created == created
    assert aggregates.status_updates == []
    assert aggregates.indexed == [aggregate]
    assert aggregates.index_commits == [False]


def test_a_new_revision_of_a_deleted_item_shows_it_again(aggregates: types.SimpleNamespace) -> None:
    data = make_data()
    NewsItemAggregate._resurface(data, "Old title", "Old review")
    assert aggregates.created == [data]
    assert aggregates.status_updates == []


def test_a_refreshed_deleted_item_stays_deleted(aggregates: types.SimpleNamespace) -> None:
    NewsItemAggregate._refresh(make_data(), "Old title", "Old review")
    assert aggregates.created == []
    assert aggregates.indexed == []


# --- remote nodes ----------------------------------------------------------------------


def test_a_newer_revision_from_a_remote_node_updates_the_item(monkeypatch: pytest.MonkeyPatch) -> None:
    remote = types.SimpleNamespace(id=7, name="partner")
    node_attribute = attribute("TLP", "AMBER")
    node_attribute.remote_node_id = 7
    user_attribute = attribute("Analyst note", "check vendor")
    stored = make_data(version="1.0.0", attributes=[node_attribute, user_attribute])
    incoming = make_data(version="1.1.0", published="05.09.2026 - 08:00", hash="remote-hash", attributes=[attribute("TLP", "CLEAR")])

    deleted, resurfaced, status_updates = [], [], []
    session = types.SimpleNamespace(add=lambda _item: None, delete=deleted.append, commit=lambda: None, execute=lambda *_args: None)
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=session))
    monkeypatch.setattr(news_item_module, "NewNewsItemDataSchema", lambda **_kwargs: types.SimpleNamespace(load=lambda _payload: [incoming]))
    monkeypatch.setattr(NewsItemData, "find_by_hash", classmethod(lambda _cls, _value: None))
    monkeypatch.setattr(NewsItemData, "hash_known", classmethod(lambda _cls, _value: False))
    monkeypatch.setattr(NewsItemData, "find_by_version_key", classmethod(lambda _cls, _key: stored))
    monkeypatch.setattr(NewsItemAggregate, "_resurface", classmethod(lambda _cls, data, title, _review: resurfaced.append((data, title))))
    news_item = types.SimpleNamespace(id=3, relevance=0, likes=0, dislikes=0, news_item_aggregate_id=5)
    monkeypatch.setattr(NewsItem, "get_all_with_data", classmethod(lambda _cls, _data_id: [news_item]))
    monkeypatch.setattr(NewsItemVote, "delete_for_remote_node", classmethod(lambda _cls, _item_id, _node_id: 0))
    monkeypatch.setattr(NewsItemAggregate, "update_status", classmethod(lambda _cls, aggregate_id: status_updates.append(aggregate_id)))

    NewsItemAggregate.add_remote_news_items([{"relevance": 0}], remote, "group-1")

    assert stored.version == "1.1.0"
    assert [version.version for version in stored.versions] == ["1.0.0"]
    # The node's own attribute is replaced by what it sent; the user's stays.
    assert sorted((a.key, a.value) for a in stored.attributes) == [("Analyst note", "check vendor"), ("TLP", "CLEAR")]
    assert deleted == [node_attribute]
    assert resurfaced == [(stored, "Advisory")]
    assert status_updates == [5]


def test_items_from_a_remote_node_count_in_the_tag_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    remote = types.SimpleNamespace(id=7, name="partner")
    incoming = make_data(title="Ransomware campaign", hash="remote-new", version_key=None)
    counted = []
    session = types.SimpleNamespace(add=lambda _item: None, delete=lambda _item: None, commit=lambda: None, execute=lambda *_args: None)
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=session))
    monkeypatch.setattr(news_item_module, "NewNewsItemDataSchema", lambda **_kwargs: types.SimpleNamespace(load=lambda _payload: [incoming]))
    monkeypatch.setattr(NewsItemData, "find_by_hash", classmethod(lambda _cls, _value: None))
    monkeypatch.setattr(NewsItemAggregate, "create_new_for_group", classmethod(lambda _cls, _data, _group_id: None))
    monkeypatch.setattr(NewsItem, "get_all_with_data", classmethod(lambda _cls, _data_id: []))
    monkeypatch.setattr(TagCloud, "add_words", classmethod(lambda _cls, counts: counted.append(dict(counts))))

    NewsItemAggregate.add_remote_news_items([{"relevance": 0}], remote, "group-1")

    (counts,) = counted
    assert counts["ransomware"] == 1
    assert counts["campaign"] == 1


def test_a_republished_copy_from_a_remote_node_refreshes_the_item(monkeypatch: pytest.MonkeyPatch) -> None:
    remote = types.SimpleNamespace(id=7, name="partner")
    stored = make_data(version="3", published="26.09.2026 - 12:18")
    incoming = make_data(version="3", published="29.09.2026 - 12:58", hash="remote-republished")
    refreshed, resurfaced = [], []
    session = types.SimpleNamespace(add=lambda _item: None, delete=lambda _item: None, commit=lambda: None, execute=lambda *_args: None)
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=session))
    monkeypatch.setattr(news_item_module, "NewNewsItemDataSchema", lambda **_kwargs: types.SimpleNamespace(load=lambda _payload: [incoming]))
    monkeypatch.setattr(NewsItemData, "find_by_hash", classmethod(lambda _cls, _value: None))
    monkeypatch.setattr(NewsItemData, "hash_known", classmethod(lambda _cls, _value: False))
    monkeypatch.setattr(NewsItemData, "find_by_version_key", classmethod(lambda _cls, _key: stored))
    monkeypatch.setattr(NewsItemAggregate, "_refresh", classmethod(lambda _cls, data, _title, _review: refreshed.append(data)))
    monkeypatch.setattr(NewsItemAggregate, "_resurface", classmethod(lambda _cls, data, _title, _review: resurfaced.append(data)))
    monkeypatch.setattr(NewsItem, "get_all_with_data", classmethod(lambda _cls, _data_id: []))

    NewsItemAggregate.add_remote_news_items([{"relevance": 0}], remote, "group-1")

    assert stored.versions == []
    assert stored.published == "29.09.2026 - 12:58"
    assert (refreshed, resurfaced) == ([stored], [])
