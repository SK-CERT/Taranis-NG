"""Set up and inspect disposable remote-test databases inside either core image.

This helper deliberately uses the running image's reflected schema, never the
current checkout's models. It does not create an application or start listeners.
Synchronization and acknowledgments are performed by the real HTTP/SSE workers.
One JSON command is read from stdin; one JSON result is written to stdout.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from config import Config

COLLECTED = datetime(2026, 7, 15, 10, 0, 12, 123456, tzinfo=UTC)
INITIAL_CURSOR = datetime(2020, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)
PUBLICATION = "15.07.2026 - 11:30"
ATTRIBUTE_VALUE = "15.07.2026 - 11:30"
TABLES = (
    "collector",
    "osint_source",
    "osint_source_group",
    "news_item_data",
    "news_item_attribute",
    "news_item_data_news_item_attribute",
    "report_item_type",
    "attribute",
    "attribute_group",
    "attribute_group_item",
    "report_item",
    "report_item_attribute",
    "remote_access",
    "remote_access_osint_source",
    "remote_access_report_item_type",
    "remote_node",
    "state",
)


def identifier(label: str, kind: str) -> str:
    """Return a stable UUID, distinct for each node and fixture kind."""
    return str(uuid5(NAMESPACE_URL, f"taranis-remote-tests/{label}/{kind}"))


def utc_string(value: datetime | None) -> str | None:
    """Interpret historical naive database timestamps in that node's timezone."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(os.environ.get("TZ", "UTC")))
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Database:
    """Small reflected-table adapter shared by both historical and current nodes."""

    def __init__(self, connection: sa.Connection) -> None:
        """Reflect the actual schema of this disposable node's database."""
        self.connection = connection
        self.metadata = sa.MetaData()
        self.metadata.reflect(connection, only=TABLES)
        self.tables = self.metadata.tables

    def values(self, table: sa.Table, values: dict[str, Any]) -> dict[str, Any]:
        """Adapt only version-dependent columns and naive legacy timestamp storage."""
        result = {}
        for name, value in values.items():
            if name not in table.c:
                if name == "legacy_timezone":
                    continue
                message = f"Required fixture column missing: {table.name}.{name}"
                raise ValueError(message)
            column = table.c[name]
            if isinstance(value, datetime) and isinstance(column.type, sa.DateTime) and not column.type.timezone:
                result[name] = value.astimezone(ZoneInfo(os.environ.get("TZ", "UTC"))).replace(tzinfo=None)
            else:
                result[name] = value
        return result

    def insert(self, name: str, /, **values: Any) -> Any:
        """Insert one fixture row and return its generated or supplied primary key."""
        table = self.tables[name]
        primary_key = next(iter(table.primary_key.columns))
        return self.connection.execute(table.insert().values(**self.values(table, values)).returning(primary_key)).scalar_one()

    def update(self, name: str, row_id: Any, /, **values: Any) -> None:
        """Change one known fixture row."""
        table = self.tables[name]
        self.connection.execute(table.update().where(table.c.id == row_id).values(**self.values(table, values)))

    def find(self, name: str, /, **values: Any) -> dict[str, Any]:
        """Read exactly one fixture row, failing if setup is incomplete."""
        table = self.tables[name]
        return dict(self.connection.execute(sa.select(table).filter_by(**values)).mappings().one())

    def fixture_ids(self, label: str) -> dict[str, Any]:
        """Find fixture database keys without a mutable host-side state file."""
        return {
            "source_id": identifier(label, "source"),
            "excluded_source_id": identifier(label, "excluded-source"),
            "group_id": identifier(label, "group"),
            "report_type_id": self.find("report_item_type", title=f"remote-test-{label}-type")["id"],
            "excluded_report_type_id": self.find("report_item_type", title=f"remote-test-{label}-excluded-type")["id"],
            "news_hash": f"remote-test-{label}-news-1",
            "updated_news_hash": f"remote-test-{label}-news-2",
            "excluded_news_hash": f"remote-test-{label}-excluded-news",
            "report_uuid": identifier(label, "report"),
            "excluded_report_uuid": identifier(label, "excluded-report"),
            "access_id": self.find("remote_access", name=f"remote-test-{label}-access")["id"],
            "node_id": self.find("remote_node", name=f"remote-test-{label}-peer")["id"],
            "event_id": identifier(label, "event"),
        }

    def news(self, label: str, kind: str, source_id: str, collected: datetime = COLLECTED) -> None:
        """Seed a real provider news row with source-owned publication/attribute text."""
        row_id = self.insert(
            "news_item_data",
            id=identifier(label, kind),
            hash=f"remote-test-{label}-{kind}",
            title=f"remote-test-{label}-{kind}",
            review="Remote compatibility fixture",
            source="Remote fixture",
            link=f"https://example.test/{label}/{kind}",
            author="Remote test",
            content="Remote synchronization content",
            collected=collected,
            published=PUBLICATION,
            updated=datetime.now(UTC),
            osint_source_id=source_id,
        )
        attribute_id = self.insert(
            "news_item_attribute",
            key="remote-test-text",
            value=ATTRIBUTE_VALUE,
            binary_mime_type="text/plain",
            created=datetime.now(UTC),
        )
        self.insert("news_item_data_news_item_attribute", news_item_data_id=row_id, news_item_attribute_id=attribute_id)

    def seed(self, command: dict[str, Any]) -> dict[str, Any]:
        """Create allowed and excluded provider fixtures plus an independent consumer."""
        label = command["label"]
        source_id, excluded_source_id = identifier(label, "source"), identifier(label, "excluded-source")
        collector_id = self.insert(
            "collector",
            id=identifier(label, "collector"),
            name=f"remote-test-{label}-collector",
            description="Fixture",
            type="MANUAL_COLLECTOR",
        )
        for source, suffix in ((source_id, "source"), (excluded_source_id, "excluded-source")):
            self.insert("osint_source", id=source, name=f"remote-test-{label}-{suffix}", description="Fixture", collector_id=collector_id)
        group_id = self.insert(
            "osint_source_group",
            id=identifier(label, "group"),
            name=f"remote-test-{label}-group",
            description="Fixture",
            default=False,
        )
        report_type_id = self.insert("report_item_type", title=f"remote-test-{label}-type", description="Shared fixture")
        excluded_type_id = self.insert("report_item_type", title=f"remote-test-{label}-excluded-type", description="Not shared")
        attribute_id = self.insert("attribute", name=f"remote-test-{label}-attribute", description="Opaque text", type="STRING")
        attribute_group_id = self.insert(
            "attribute_group",
            title="Remote fixture group",
            description="",
            index=0,
            report_item_type_id=report_type_id,
        )
        group_item_id = self.insert(
            "attribute_group_item",
            title="Remote fixture time",
            description="Opaque timestamp-looking text",
            index=0,
            min_occurrence=0,
            max_occurrence=1,
            attribute_group_id=attribute_group_id,
            attribute_id=attribute_id,
        )
        state = self.tables["state"]
        state_id = self.connection.execute(sa.select(state.c.id).order_by(state.c.id).limit(1)).scalar_one()
        for kind, type_id in (("report", report_type_id), ("excluded-report", excluded_type_id)):
            report_id = self.insert(
                "report_item",
                uuid=identifier(label, kind),
                title=f"remote-test-{label}-{kind}",
                title_prefix="Remote fixture",
                created=COLLECTED,
                last_updated=datetime.now(UTC),
                report_item_type_id=type_id,
                state_id=state_id,
            )
            self.insert(
                "report_item_attribute",
                value=ATTRIBUTE_VALUE,
                binary_size=0,
                attribute_group_item_id=group_item_id,
                attribute_group_item_title="Remote fixture time",
                report_item_id=report_id,
                version=1,
                current=True,
                created=COLLECTED,
                last_updated=COLLECTED,
            )
        self.news(label, "news-1", source_id)
        self.news(label, "excluded-news", excluded_source_id)
        access_id = self.insert(
            "remote_access",
            name=f"remote-test-{label}-access",
            description="Fixture grant",
            enabled=True,
            connected=False,
            api_key=command["key"],
            event_id=identifier(label, "event"),
            legacy_timezone=command["peer_timezone"],
            last_synced_news_items=INITIAL_CURSOR,
            last_synced_report_items=INITIAL_CURSOR,
        )
        self.insert("remote_access_osint_source", remote_access_id=access_id, osint_source_id=source_id)
        self.insert("remote_access_report_item_type", remote_access_id=access_id, report_item_type_id=report_type_id)
        self.insert(
            "remote_node",
            name=f"remote-test-{label}-peer",
            description="Fixture consumer",
            enabled=True,
            remote_url=command["peer_url"],
            events_url=command["peer_url"].rstrip("/") + "/sse",
            api_key=command["peer_key"],
            sync_news_items=True,
            sync_report_items=True,
            osint_source_group_id=group_id,
            legacy_timezone=command["peer_timezone"],
        )
        return self.fixture_ids(label)

    def snapshot(self, label: str) -> dict[str, Any]:
        """Return persisted identities, timestamps, contents, and synchronization cursors."""
        news = []
        data, attrs = self.tables["news_item_data"], self.tables["news_item_attribute"]
        association = self.tables["news_item_data_news_item_attribute"]
        for row in self.connection.execute(sa.select(data).where(data.c.hash.like("remote-test-%")).order_by(data.c.hash)).mappings():
            item = {name: row[name] for name in ("hash", "title", "published", "remote_source")}
            item["collected"] = utc_string(row["collected"])
            item["attributes"] = [
                {name: attr[name] for name in ("key", "value", "remote_user")}
                for attr in self.connection.execute(
                    sa.select(attrs)
                    .join(association, attrs.c.id == association.c.news_item_attribute_id)
                    .where(association.c.news_item_data_id == row["id"]),
                ).mappings()
            ]
            news.append(item)
        table, attrs = self.tables["report_item"], self.tables["report_item_attribute"]
        reports = [
            {
                **{name: row[name] for name in ("uuid", "title", "remote_user")},
                "attributes": [
                    {"title": attr["attribute_group_item_title"], "value": attr["value"]}
                    for attr in self.connection.execute(sa.select(attrs).where(attrs.c.report_item_id == row["id"])).mappings()
                ],
            }
            for row in self.connection.execute(sa.select(table).where(table.c.title.like("remote-test-%")).order_by(table.c.uuid)).mappings()
        ]
        access = self.find("remote_access", name=f"remote-test-{label}-access")
        node = self.find("remote_node", name=f"remote-test-{label}-peer")
        return {
            "news": news,
            "reports": reports,
            "access": {
                **{name: access[name] for name in ("id", "enabled", "connected", "event_id")},
                **{name: utc_string(access[name]) for name in ("last_synced_news_items", "last_synced_report_items")},
            },
            "node": {name: node[name] for name in ("id", "name", "enabled", "event_id")},
        }

    def hold_ack(self, enabled: bool) -> None:
        """Temporarily reject real HTTP cursor acknowledgments in this test database."""
        self.connection.exec_driver_sql("DROP TRIGGER IF EXISTS remote_test_hold_ack ON remote_access")
        self.connection.exec_driver_sql("DROP FUNCTION IF EXISTS remote_test_hold_ack()")
        if enabled:
            self.connection.exec_driver_sql("""
                CREATE FUNCTION remote_test_hold_ack() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'Remote test deliberately rejected acknowledgment'; END $$
            """)
            self.connection.exec_driver_sql("""
                CREATE TRIGGER remote_test_hold_ack BEFORE UPDATE ON remote_access
                FOR EACH ROW WHEN (
                    OLD.last_synced_news_items IS DISTINCT FROM NEW.last_synced_news_items OR
                    OLD.last_synced_report_items IS DISTINCT FROM NEW.last_synced_report_items
                ) EXECUTE FUNCTION remote_test_hold_ack()
            """)


def emit(event_id: str) -> None:
    """Publish the production event names through the node's real SSE forwarder."""
    from sse.sse import SSE  # noqa: PLC0415 - only emitting actions load the application's logging stack

    publisher = SSE()
    for event in ("remote_access_news_items_updated", "remote_access_report_items_updated"):
        publisher.publish([event_id], event=event, channel="remote")


def main() -> None:
    """Execute one command against the disposable node database."""
    command = json.load(sys.stdin)
    label = command.get("label", "a")
    if label not in ("a", "b"):
        message = "Fixture label must be a or b"
        raise ValueError(message)
    engine = sa.create_engine(Config.SQLALCHEMY_DATABASE_URI)
    should_emit = command["action"] in ("emit", "update", "replay")
    try:
        with contextlib.redirect_stdout(sys.stderr), engine.begin() as connection:
            database = Database(connection)
            action = command["action"]
            if action == "seed":
                result = database.seed(command)
            elif action == "snapshot":
                result = database.snapshot(label)
            else:
                ids = database.fixture_ids(label)
                if action == "update":
                    database.news(label, "news-2", ids["source_id"])
                    report = database.find("report_item", uuid=ids["report_uuid"])
                    database.update("report_item", report["id"], title=f"remote-test-{label}-report-updated", last_updated=datetime.now(UTC))
                    attrs = database.tables["report_item_attribute"]
                    connection.execute(
                        attrs.update().where(attrs.c.report_item_id == report["id"]).values(value="Updated opaque 15.07.2026 - 11:30"),
                    )
                elif action == "replay":
                    database.update(
                        "remote_access",
                        ids["access_id"],
                        last_synced_news_items=INITIAL_CURSOR,
                        last_synced_report_items=INITIAL_CURSOR,
                    )
                elif action == "access":
                    database.update("remote_access", ids["access_id"], enabled=command["enabled"])
                elif action == "node":
                    database.update("remote_node", ids["node_id"], enabled=command["enabled"])
                elif action == "hold_ack":
                    database.hold_ack(command["enabled"])
                elif action != "emit":
                    message = f"Unknown helper action: {action}"
                    raise ValueError(message)
                result = database.snapshot(label)
        # Publish only after commit, so the HTTP readers can see the fixture changes.
        if should_emit:
            with contextlib.redirect_stdout(sys.stderr):
                emit(identifier(label, "event"))
        print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
