"""Exercise unmodified remote providers and consumers over HTTP, SSE and PostgreSQL."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests

COLLECTED = datetime(2026, 7, 15, 10, 0, 12, 123456, tzinfo=UTC)
OPAQUE_PUBLICATION = "15.07.2026 - 11:30"


@dataclass
class Node:
    """A host-side handle; application imports only run inside its own container."""

    label: str
    url: str
    timezone: str
    legacy: bool
    compose: list[str]
    artifacts: Path
    ids: dict | None = None

    @property
    def key(self) -> str:
        """Return this provider's disposable API key."""
        return f"remote-test-{self.label}"

    def helper(self, action: str, **arguments: object) -> dict:
        """Run database setup or inspection using the node's own dependencies."""
        completed = subprocess.run(
            [*self.compose, "exec", "-T", f"core-{self.label}", "python", "/remote-tests/node_helper.py"],
            input=json.dumps({"action": action, "label": self.label, **arguments}),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert completed.returncode == 0, f"{self.label} helper {action}: {completed.stderr}\n{completed.stdout}"
        result = json.loads(completed.stdout)
        (self.artifacts / f"{self.label}-{action}.json").write_text(json.dumps(result, indent=2) + "\n")
        return result

    def request(self, method: str, path: str, *, authenticated: bool = True, **kwargs: object) -> requests.Response:
        """Call a published endpoint with bounded request time."""
        headers = {"Authorization": f"ApiKey {self.key}"} if authenticated else {}
        headers.update(kwargs.pop("headers", {}))
        return requests.request(method, f"{self.url}{path}", headers=headers, timeout=10, **kwargs)

    def logs(self) -> str:
        """Read node traffic so the negotiated protocol can be verified."""
        return subprocess.run(
            [*self.compose, "logs", "--no-color", "--no-log-prefix", f"core-{self.label}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        ).stdout

    def admin(self, method: str, path: str, **kwargs: object) -> requests.Response:
        """Call a configuration endpoint using the disposable database's administrator."""
        login = self.request("POST", "/api/v1/auth/login", authenticated=False, json={"username": "admin", "password": "admin"})
        assert login.status_code == 200, login.text
        return self.request(method, path, headers={"Authorization": f"Bearer {login.json()['access_token']}"}, **kwargs)


@pytest.fixture(scope="module")
def nodes() -> dict[str, Node]:
    """Seed two databases; fail clearly when invoked outside the isolated runner."""
    required = (
        "REMOTE_TEST_PROJECT",
        "REMOTE_TEST_COMPOSE",
        "REMOTE_TEST_ARTIFACTS",
        "REMOTE_TEST_LANE",
        "REMOTE_TEST_A_URL",
        "REMOTE_TEST_B_URL",
        "REMOTE_TEST_B_TIMEZONE",
        "REMOTE_TEST_ENV_FILE",
    )
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"Use python3 scripts/run_remote_tests.py; missing {missing}"
    compose = [
        "docker",
        "compose",
        "--env-file",
        os.environ["REMOTE_TEST_ENV_FILE"],
        "-f",
        os.environ["REMOTE_TEST_COMPOSE"],
        "-p",
        os.environ["REMOTE_TEST_PROJECT"],
    ]
    artifacts = Path(os.environ["REMOTE_TEST_ARTIFACTS"])
    pair = {
        "a": Node("a", os.environ["REMOTE_TEST_A_URL"], "UTC", legacy=False, compose=compose, artifacts=artifacts),
        "b": Node(
            "b",
            os.environ["REMOTE_TEST_B_URL"],
            os.environ["REMOTE_TEST_B_TIMEZONE"],
            os.environ["REMOTE_TEST_LANE"] != "current",
            compose,
            artifacts,
        ),
    }
    for label, node in pair.items():
        peer = pair["b" if label == "a" else "a"]
        node.ids = node.helper("seed", peer_url=f"http://core-{peer.label}", peer_timezone=peer.timezone, key=node.key, peer_key=peer.key)
    return pair


def parse_cursor(value: str, timezone: str) -> datetime:
    """Normalize an offset-bearing or legacy boundary timestamp for assertions."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(UTC)


def assert_wire_contract(provider: Node, consumer: Node) -> None:
    """Check both route generations before the manager starts importing."""
    versions = [1] if provider.legacy else [1, 2]
    for tested_version in versions:
        prefix = f"/api/v{tested_version}/remote"
        for operation in ("connect", "disconnect", "sync-news-items", "sync-report-items"):
            for headers in ({}, {"Authorization": "ApiKey incorrect"}):
                denied = provider.request("GET", f"{prefix}/{operation}", authenticated=False, headers=headers)
                assert denied.status_code == 401, denied.text
        for operation in ("sync-news-items", "sync-report-items"):
            denied = provider.request("PUT", f"{prefix}/{operation}", authenticated=False, json={})
            assert denied.status_code == 401, denied.text
        provider.helper("access", enabled=False)
        try:
            assert provider.request("GET", f"{prefix}/connect").status_code == 401
        finally:
            provider.helper("access", enabled=True)
        connected = provider.request("GET", f"{prefix}/connect")
        assert connected.status_code == 200, connected.text
        assert set(connected.json()) == {
            "event_id",
            "last_synced_news_items",
            "last_synced_report_items",
            "news_items_provided",
            "report_items_provided",
        }
        assert connected.json()["event_id"] == provider.ids["event_id"]
        assert connected.json()["news_items_provided"] is True
        assert connected.json()["report_items_provided"] is True
        for field in ("last_synced_news_items", "last_synced_report_items"):
            cursor = connected.json()[field]
            if tested_version == 2:
                assert cursor.endswith("Z")
            elif not provider.legacy:
                datetime.strptime(cursor, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=ZoneInfo(consumer.timezone))

        news_response = provider.request("GET", f"{prefix}/sync-news-items")
        report_response = provider.request("GET", f"{prefix}/sync-report-items")
        assert news_response.status_code == 200, news_response.text
        assert report_response.status_code == 200, report_response.text
        news, reports = news_response.json(), report_response.json()
        assert {item["hash"] for item in news["news_items"]} == {provider.ids["news_hash"]}
        assert {item["uuid"] for item in reports["report_items"]} == {provider.ids["report_uuid"]}
        item = news["news_items"][0]
        assert item["published"] == OPAQUE_PUBLICATION
        if tested_version == 1:
            # New providers format for the old receiving node; old providers use their own TZ.
            boundary = provider.timezone if provider.legacy else consumer.timezone
            assert item["collected"] == COLLECTED.astimezone(ZoneInfo(boundary)).strftime("%d.%m.%Y - %H:%M")
        else:
            assert item["collected"].endswith("Z")
            assert parse_cursor(item["collected"], "UTC") == COLLECTED
        assert provider.request("GET", f"{prefix}/disconnect").status_code == 200
    if provider.legacy:
        assert provider.request("GET", "/api/v2/remote/connect").status_code in (404, 405)


def wait_for_sync(
    provider: Node,
    consumer: Node,
    *,
    updated: bool,
    acknowledged: bool,
    previous_cursors: dict | None = None,
) -> tuple[dict, dict]:
    """Repeat real notifications until both database postconditions hold, with a deadline."""
    deadline = time.monotonic() + 90
    last = {}
    while time.monotonic() < deadline:
        provider.helper("emit")
        received = consumer.helper("snapshot")
        supplied = provider.helper("snapshot")
        expected = {provider.ids["news_hash"]}
        if updated:
            expected.add(provider.ids["updated_news_hash"])
        news = [item for item in received["news"] if item["hash"] in expected]
        reports = [item for item in received["reports"] if item["uuid"] == provider.ids["report_uuid"]]
        imported = len(news) == len(expected) and len(reports) == 1
        if imported and updated:
            imported = reports[0]["title"].endswith("updated")
        cursors = supplied["access"]
        cursor_values = [parse_cursor(cursors[field], "UTC") for field in ("last_synced_news_items", "last_synced_report_items")]
        advanced = all(value.year > 2020 for value in cursor_values)
        held = all(value == datetime(2020, 1, 1, microsecond=123456, tzinfo=UTC) for value in cursor_values)
        if previous_cursors:
            advanced = all(
                parse_cursor(cursors[field], "UTC") > parse_cursor(previous_cursors[field], "UTC")
                for field in ("last_synced_news_items", "last_synced_report_items")
            )
        last = {"received": received, "supplied": supplied}
        if imported and (advanced if acknowledged else held):
            return received, supplied
        time.sleep(0.5)
    pytest.fail(f"Synchronization deadline exceeded: {json.dumps(last, indent=2)}")


@pytest.mark.parametrize("consumer_label", ["a", "b"])
def test_real_nodes_synchronize_news_and_reports_in_both_directions(nodes: dict[str, Node], consumer_label: str) -> None:
    consumer = nodes[consumer_label]
    provider = nodes["b" if consumer_label == "a" else "a"]
    version = 1 if consumer.legacy or provider.legacy else 2
    assert_wire_contract(provider, consumer)
    before = provider.logs()
    # Force a real persistence failure on acknowledgment, after successful import.
    provider.helper("hold_ack", enabled=True)
    try:
        connection = consumer.admin("GET", f"/api/v1/config/remote-nodes/{consumer.ids['node_id']}/connect")
        assert connection.status_code == 200, connection.text
        received, supplied = wait_for_sync(provider, consumer, updated=False, acknowledged=False)
        assert supplied["access"]["connected"] is True
        assert received["node"]["event_id"] == supplied["access"]["event_id"]
    finally:
        provider.helper("hold_ack", enabled=False)

    # The provider still offers the imported batch; retry through the same SSE listener.
    received, supplied = wait_for_sync(provider, consumer, updated=False, acknowledged=True)
    imported = [item for item in received["news"] if item["hash"] == provider.ids["news_hash"]]
    reports = [item for item in received["reports"] if item["uuid"] == provider.ids["report_uuid"]]
    assert len(imported) == len(reports) == 1
    assert imported[0]["published"] == OPAQUE_PUBLICATION
    assert [(item["key"], item["value"]) for item in imported[0]["attributes"]] == [("remote-test-text", OPAQUE_PUBLICATION)]
    expected_collected = COLLECTED.replace(second=0, microsecond=0) if version == 1 else COLLECTED
    assert parse_cursor(imported[0]["collected"], "UTC") == expected_collected
    original_report = next(item for item in supplied["reports"] if item["uuid"] == provider.ids["report_uuid"])
    assert reports[0]["attributes"] == original_report["attributes"]
    assert not any(item["hash"] == provider.ids["excluded_news_hash"] for item in received["news"])
    assert not any(item["uuid"] == provider.ids["excluded_report_uuid"] for item in received["reports"])

    for kind in ("news", "report"):
        batch = provider.request("GET", f"/api/v{version}/remote/sync-{kind}-items")
        assert batch.status_code == 200, batch.text
        assert batch.json()[f"{kind}_items"] == []

    provider.helper("update")
    updated, _ = wait_for_sync(provider, consumer, updated=True, acknowledged=True, previous_cursors=supplied["access"])
    assert sum(item["hash"] == provider.ids["updated_news_hash"] for item in updated["news"]) == 1
    updated_reports = [item for item in updated["reports"] if item["uuid"] == provider.ids["report_uuid"]]
    assert len(updated_reports) == 1
    assert updated_reports[0]["attributes"] != reports[0]["attributes"]

    # Disable the consumer through its supported config API, which invokes manager disconnect.
    disabled = consumer.admin(
        "PUT",
        f"/api/v1/config/remote-nodes/{consumer.ids['node_id']}",
        json={
            "id": consumer.ids["node_id"],
            "name": f"remote-test-{consumer.label}-peer",
            "description": "Compatibility test",
            "enabled": False,
            "remote_url": f"http://core-{provider.label}",
            "events_url": f"http://core-{provider.label}/sse",
            "api_key": provider.key,
            "sync_news_items": True,
            "sync_report_items": True,
            "osint_source_group_id": consumer.ids["group_id"],
            "legacy_timezone": provider.timezone,
        },
    )
    assert disabled.status_code == 200, disabled.text
    assert consumer.helper("snapshot")["node"]["event_id"] is None
    assert provider.helper("snapshot")["access"]["connected"] is False

    traffic = provider.logs()[len(before) :]
    for path in ("connect", "sync-news-items", "sync-report-items", "disconnect"):
        assert f"/api/v{version}/remote/{path}" in traffic
    assert re.search(rf"PUT /api/v{version}/remote/sync-news-items", traffic), traffic
    assert re.search(rf"PUT /api/v{version}/remote/sync-report-items", traffic), traffic
    if version == 1 and not consumer.legacy:
        assert traffic.index("/api/v2/remote/connect") < traffic.index("/api/v1/remote/connect")
        assert "/api/v2/remote/sync-" not in traffic
    if version == 2:
        assert "/api/v1/remote/" not in traffic
