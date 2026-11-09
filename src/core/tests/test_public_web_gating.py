"""Public-web work only happens where a public-web node exists.

Nothing is registered under Configuration -> Public web on a stock install, yet
every product create/update/delete used to look the published state up and then
load every node, and the scheduler pinged for nodes once a minute against an
empty table. All of that was thrown away deep inside :func:`notify_nodes`, which
filtered down to an empty target list and returned.

These tests pin the short-circuit at the TOP of each entry point — before any
query — and, just as importantly, pin the opposite direction: a deployment that
does have a node must keep getting every ping and every cache-reset push.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING, Self

import pytest
from api import publish
from managers import public_web_manager
from model.public_web_node import PublicWebNode
from model.state import StateDefinition, StateEnum

if TYPE_CHECKING:
    from collections.abc import Callable

PUBLISHED_STATE_ID = 7
OTHER_STATE_ID = 3


class _FakeQuery:
    """A query that only knows how to narrow itself and answer ``.first()``."""

    def __init__(self, row: object) -> None:
        self._row = row
        self.criteria: list[object] = []

    def filter(self, *criteria: object) -> _FakeQuery:
        """Record the criteria; the primed answer is what they find."""
        self.criteria.extend(criteria)
        return self

    def first(self) -> object:
        """Return the single row the fixture was primed with."""
        return self._row


class _FakeSession:
    """Records what was asked for, so the predicate's cheapness stays pinned."""

    def __init__(self, row: object) -> None:
        self._row = row
        self.queries: list[tuple] = []
        self.made: list[_FakeQuery] = []

    def query(self, *columns: object) -> _FakeQuery:
        """Record the selected columns and hand back the primed answer."""
        self.queries.append(columns)
        self.made.append(_FakeQuery(self._row))
        return self.made[-1]


class _FakeDb:
    """Stands in for ``managers.db_manager.db`` — session only, no engine."""

    def __init__(self, row: object) -> None:
        self.session = _FakeSession(row)


class _FakeAppContext:
    """The context manager :func:`job` enters; it owns nothing."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class _FakeApp:
    """Just the ``app_context()`` the scheduled job asks for."""

    def app_context(self) -> _FakeAppContext:
        """Return a context manager that does nothing."""
        return _FakeAppContext()


class _NeverIterated:
    """An iterable that fails the test if anything walks it."""

    def __iter__(self) -> None:
        msg = "notify_nodes looked at the nodes instead of returning"
        raise AssertionError(msg)


@pytest.fixture
def nodes_in_db(monkeypatch: pytest.MonkeyPatch) -> Callable[[object], _FakeDb]:
    """Return a setter for what ``SELECT id FROM public_web_node LIMIT 1`` finds."""

    def _set(row: object) -> _FakeDb:
        fake = _FakeDb(row)
        monkeypatch.setattr(public_web_manager, "db", fake)
        return fake

    return _set


@pytest.fixture
def node_traffic(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record everything the health check reaches for, and hand it one node."""
    made: list[str] = []
    node = types.SimpleNamespace(name="web", api_url="http://public-web", api_key="node-key", enabled=True)
    node.update_last_seen = lambda: made.append("update_last_seen")
    off = types.SimpleNamespace(name="off", api_url="http://switched-off", api_key="other-key", enabled=False)
    off.update_last_seen = lambda: made.append("update_last_seen off")

    def fake_get_all(_cls: type) -> list:
        made.append("get_all")
        return [node, off]

    class _FakeApi:
        def __init__(self, api_url: str, api_key: str) -> None:  # noqa: ARG002
            made.append("PublicWebApi" if api_url == node.api_url else f"PublicWebApi {api_url}")

        def isalive(self) -> tuple[dict, HTTPStatus]:
            return {"status": "ok"}, HTTPStatus.OK

    monkeypatch.setattr(PublicWebNode, "get_all", classmethod(fake_get_all))
    monkeypatch.setattr(public_web_manager, "PublicWebApi", _FakeApi)
    return made


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> list:
    """Capture the cache-reset pushes instead of dialling any node."""
    started: list = []

    class _FakeThread:
        def __init__(self, target: object = None, args: tuple = (), daemon: bool = False) -> None:  # noqa: ARG002
            self._targets = args[0] if args else []

        def start(self) -> None:
            started.append(self._targets)

    monkeypatch.setattr(public_web_manager.threading, "Thread", _FakeThread)
    return started


@pytest.fixture
def state_lookups(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every published-state lookup the publish hooks make."""
    made: list[str] = []

    def fake_get_by_name(_cls: type, name: str) -> object:
        made.append(name)
        return types.SimpleNamespace(id=PUBLISHED_STATE_ID)

    monkeypatch.setattr(StateDefinition, "get_by_name", classmethod(fake_get_by_name))
    return made


@pytest.fixture
def notifications(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record whether the publish hooks decided to notify the nodes."""
    made: list[str] = []
    monkeypatch.setattr(publish, "_notify_public_web_nodes", lambda: made.append("notify"))
    return made


def test_public_web_enabled_is_false_with_no_nodes(nodes_in_db: Callable[[object], _FakeDb]) -> None:
    """An empty node table is how a stock install says the feature is not in use."""
    fake = nodes_in_db(None)

    assert public_web_manager.public_web_enabled() is False
    # One column, not whole rows: the point of the predicate is that it is
    # cheaper than the StateDefinition lookup it saves.
    (columns,) = fake.session.queries
    assert len(columns) == 1
    assert columns[0] is PublicWebNode.id
    # Only a node in use counts: with every node switched off there is nothing to talk to.
    (query,) = fake.session.made
    assert [str(criterion) for criterion in query.criteria] == [str(PublicWebNode.enabled.is_(True))]


def test_public_web_enabled_is_true_with_a_node(nodes_in_db: Callable[[object], _FakeDb]) -> None:
    """One node row is enough; nothing here cares how many or whether they are up."""
    nodes_in_db((PUBLISHED_STATE_ID,))

    assert public_web_manager.public_web_enabled() is True


def test_health_check_job_makes_no_calls_when_disabled(nodes_in_db: Callable[[object], _FakeDb], node_traffic: list[str]) -> None:
    """The once-a-minute ping must not load nodes, nor build an API client."""
    nodes_in_db(None)

    public_web_manager.job(_FakeApp())

    assert node_traffic == []


def test_health_check_job_still_pings_when_a_node_exists(nodes_in_db: Callable[[object], _FakeDb], node_traffic: list[str]) -> None:
    """The gate must not switch the feature off for the deployments that use it - nor ping a node switched off."""
    nodes_in_db((1,))

    public_web_manager.job(_FakeApp())

    assert node_traffic == ["get_all", "PublicWebApi", "update_last_seen"]


def test_notify_nodes_returns_immediately_when_disabled(nodes_in_db: Callable[[object], _FakeDb], pushes: list) -> None:
    """Not merely "starts no thread": it returns before it inspects the nodes."""
    nodes_in_db(None)

    public_web_manager.notify_nodes(_NeverIterated())

    assert pushes == []


def _reachable(name: str, *, enabled: bool = True) -> types.SimpleNamespace:
    node = types.SimpleNamespace(name=name, api_url=f"http://{name}", api_key=f"{name}-key", enabled=enabled)
    node.is_reachable = lambda: True
    return node


def test_notify_nodes_still_pushes_when_a_node_exists(nodes_in_db: Callable[[object], _FakeDb], pushes: list) -> None:
    """A reachable node still gets its cache reset, off the request thread; one switched off does not."""
    nodes_in_db((1,))

    public_web_manager.notify_nodes([_reachable("web"), _reachable("off", enabled=False)])

    assert pushes == [[("web", "http://web", "web-key")]]


def test_a_node_switched_on_or_off_gets_its_cache_reset(nodes_in_db: Callable[[object], _FakeDb], pushes: list) -> None:
    """Switched off it must drop what it serves now, not when its cache expires - even as the last node."""
    nodes_in_db(None)

    public_web_manager.reset_node(_reachable("off", enabled=False))

    assert pushes == [[("off", "http://off", "off-key")]]


def test_publish_hooks_do_no_state_lookup_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    state_lookups: list[str],
    notifications: list[str],
) -> None:
    """The wasted query the maintainer flagged: every product write ran this."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: False)

    publish._reset_public_web_cache_if_published_changed(old_state_id=OTHER_STATE_ID, new_state_id=PUBLISHED_STATE_ID)

    assert state_lookups == []
    assert notifications == []


def test_publish_hooks_still_notify_when_a_node_exists(
    monkeypatch: pytest.MonkeyPatch,
    state_lookups: list[str],
    notifications: list[str],
) -> None:
    """Publishing a product on a deployment that has a feed still resets its cache."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: True)

    publish._reset_public_web_cache_if_published_changed(old_state_id=OTHER_STATE_ID, new_state_id=PUBLISHED_STATE_ID)

    assert state_lookups == [StateEnum.PUBLISHED.value]
    assert notifications == ["notify"]


def test_is_published_state_does_no_state_lookup_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    state_lookups: list[str],
) -> None:
    """The delete path asks the same question, so it needs the same gate."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: False)

    assert publish._is_published_state(PUBLISHED_STATE_ID) is False
    assert state_lookups == []


def test_is_published_state_still_answers_when_a_node_exists(
    monkeypatch: pytest.MonkeyPatch,
    state_lookups: list[str],
) -> None:
    """With a node configured the answer must still be the real one."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: True)

    assert publish._is_published_state(PUBLISHED_STATE_ID) is True
    assert publish._is_published_state(OTHER_STATE_ID) is False
    assert state_lookups == [StateEnum.PUBLISHED.value, StateEnum.PUBLISHED.value]


def test_is_published_state_logs_a_database_error_instead_of_hiding_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bare ``except`` reported a broken database as "this product is not published"."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: True)

    def boom(_cls: type, _name: str) -> object:
        msg = "connection reset by peer"
        raise RuntimeError(msg)

    monkeypatch.setattr(StateDefinition, "get_by_name", classmethod(boom))
    logged: list[str] = []
    monkeypatch.setattr(publish, "logger", types.SimpleNamespace(debug=logged.append))

    assert publish._is_published_state(PUBLISHED_STATE_ID) is False
    assert any("connection reset by peer" in line for line in logged)


def test_notify_public_web_nodes_loads_no_nodes_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing to notify means nothing to fetch, not even the node list."""
    monkeypatch.setattr(publish, "_public_web_enabled", lambda: False)
    loaded: list[str] = []
    monkeypatch.setattr(PublicWebNode, "get_all", classmethod(lambda _cls: loaded.append("get_all") or []))

    publish._notify_public_web_nodes()

    assert loaded == []


def test_publish_reads_the_predicate_from_the_manager(nodes_in_db: Callable[[object], _FakeDb]) -> None:
    """One source of truth: the hooks must not grow their own idea of "enabled"."""
    nodes_in_db(None)
    assert publish._public_web_enabled() is False

    nodes_in_db((1,))
    assert publish._public_web_enabled() is True


def test_publish_treats_an_unavailable_predicate_as_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """These hooks are best-effort; a database hiccup must not fail the product write."""

    def boom() -> bool:
        msg = "no database"
        raise RuntimeError(msg)

    monkeypatch.setattr(public_web_manager, "public_web_enabled", boom)

    assert publish._public_web_enabled() is False


# --- the push thread --------------------------------------------------------


def test_push_reset_cache_survives_a_single_node_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    """One unreachable node must not prevent the remaining nodes from being pushed."""
    seen: list[str] = []

    class _FlakyApi:
        def __init__(self, api_url: str, _api_key: str) -> None:
            self._api_url = api_url

        def reset_cache(self) -> tuple[dict, HTTPStatus]:
            seen.append(self._api_url)
            if self._api_url == "http://broken-node":
                msg = "connection refused"
                raise RuntimeError(msg)
            return {}, HTTPStatus.OK

    monkeypatch.setattr(public_web_manager, "PublicWebApi", _FlakyApi)
    logged: list[str] = []
    monkeypatch.setattr(public_web_manager, "logger", types.SimpleNamespace(debug=lambda message: logged.append(str(message))))

    public_web_manager._push_reset_cache(
        [
            ("broken", "http://broken-node", "key-1"),
            ("fine", "http://fine-node", "key-2"),
        ],
    )
    assert seen == ["http://broken-node", "http://fine-node"]
    assert any("broken" in line for line in logged)


def test_push_reset_cache_survives_a_non_standard_status_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """A proxy answering code 599 makes ``HTTPStatus(599)`` raise ValueError.

    That exception used to escape and kill the daemon thread mid-loop, skipping
    the remaining targets; the guard keeps it best-effort as documented.
    """
    asked: list[str] = []

    class _OddProxyApi:
        def __init__(self, api_url: str, _api_key: str) -> None:
            self._api_url = api_url

        def reset_cache(self) -> tuple[dict, HTTPStatus]:
            asked.append(self._api_url)
            if self._api_url == "http://proxy-599":
                return {}, HTTPStatus(599)  # type: ignore[arg-type] - exactly the failure being pinned
            return {}, HTTPStatus.OK

    monkeypatch.setattr(public_web_manager, "PublicWebApi", _OddProxyApi)
    logged: list[str] = []
    monkeypatch.setattr(public_web_manager, "logger", types.SimpleNamespace(debug=lambda message: logged.append(str(message))))

    public_web_manager._push_reset_cache([("odd", "http://proxy-599", "key"), ("fine", "http://fine-node", "key")])

    # the ValueError was contained to the 'odd' node, and the loop went on to
    # contact the healthy one — a dead thread would have skipped it
    assert any("599" in line for line in logged)
    assert asked == ["http://proxy-599", "http://fine-node"]


def test_push_reset_cache_logs_a_rejecting_node(monkeypatch: pytest.MonkeyPatch) -> None:
    """A node that answers but refuses the reset is noted, not raised."""

    class _RejectingApi:
        def __init__(self, *_args: object) -> None:
            pass

        def reset_cache(self) -> tuple[dict, HTTPStatus]:
            return {"error": "denied"}, HTTPStatus.UNAUTHORIZED

    monkeypatch.setattr(public_web_manager, "PublicWebApi", _RejectingApi)
    logged: list[str] = []
    monkeypatch.setattr(public_web_manager, "logger", types.SimpleNamespace(debug=lambda message: logged.append(str(message))))

    public_web_manager._push_reset_cache([("web", "http://public-web", "key")])

    assert any("did not accept" in line for line in logged)
