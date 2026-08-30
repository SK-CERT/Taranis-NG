"""The default public-web node is seeded by bootstrap, and only when it should be.

This seeding used to live in ``docker/prestart_core.sh``: a backgrounded subshell
that grepped ``Total:`` out of ``manage.py public-web --list`` and created the node
blind. It has moved into :mod:`bootstrap_docker`, beside the four mandatory
satellites, and these tests pin the three properties that move bought:

* the compose profile still gates it - a stack without the feed gets no node;
* an existing node is matched on ``api_url``, so an operator who renamed it in
  Configuration -> Public Web keeps their name and gets no duplicate;
* a node that never answers is reported and skipped, never raised - ``gui`` and
  ``gui-v3`` wait on this script completing, so an optional feed must not be able
  to take the whole stack down.
"""

from __future__ import annotations

import types

import bootstrap_docker
import pytest


class _FakeSession:
    """Records what bootstrap would have written, without a database."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, row: object) -> None:
        """Stage a row."""
        self.added.append(row)

    def commit(self) -> None:
        """Count a commit."""
        self.commits += 1

    def rollback(self) -> None:
        """Count a rollback."""
        self.rollbacks += 1


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> _FakeSession:
    """Swap the real db session for a recorder and skip the retry sleeps."""
    fake = _FakeSession()
    monkeypatch.setattr(bootstrap_docker.db_manager, "db", types.SimpleNamespace(session=fake))
    monkeypatch.setattr(bootstrap_docker.time, "sleep", lambda _seconds: None)
    return fake


def _existing(name: str, api_url: str = bootstrap_docker.DEFAULT_PUBLIC_WEB_URL, webs: list | None = None) -> types.SimpleNamespace:
    """Build a stand-in for a persisted PublicWebNode."""
    return types.SimpleNamespace(id=7, name=name, api_url=api_url, webs=webs if webs is not None else [])


def _stub_lookup(monkeypatch: pytest.MonkeyPatch, node: object | None) -> None:
    """Make the api_url lookup answer with ``node``."""
    monkeypatch.setattr(bootstrap_docker, "_node_by_url", lambda _model, _url: node)


def _stub_verify(monkeypatch: pytest.MonkeyPatch, problem: str | None) -> None:
    """Make the node liveness probe report ``problem`` (None means it answered)."""
    monkeypatch.setattr(bootstrap_docker.public_web_manager, "verify_node", lambda _url, _key: problem)


@pytest.mark.parametrize(
    ("profiles", "expected"),
    [
        ("public-web", True),
        ("public-web,other", True),
        (" public-web , other ", True),
        ("", False),
        ("other", False),
        # A prefix match must not count: "public-web-dev" is a different profile.
        ("public-web-dev", False),
    ],
)
def test_profile_gates_seeding(monkeypatch: pytest.MonkeyPatch, profiles: str, expected: bool) -> None:
    """Only the exact "public-web" profile switches the seeding on."""
    monkeypatch.setenv("COMPOSE_PROFILES", profiles)
    assert bootstrap_docker._public_web_enabled() is expected


def test_missing_env_leaves_feed_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deployment that never sets COMPOSE_PROFILES gets no public-web node."""
    monkeypatch.delenv("COMPOSE_PROFILES", raising=False)
    assert bootstrap_docker._public_web_enabled() is False


def test_creates_node_and_web(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    """A stack with no node yet gets one, fronted by core, with a single web."""
    _stub_lookup(monkeypatch, None)
    _stub_verify(monkeypatch, None)
    monkeypatch.setattr(bootstrap_docker, "_available_name", lambda _model, name: name)

    created: list[object] = []

    def _create(name, description, api_key, api_url, fronted_by_core=False):  # noqa: ANN001, ANN202
        node = types.SimpleNamespace(
            id=1,
            name=name,
            description=description,
            api_key=api_key,
            api_url=api_url,
            fronted_by_core=fronted_by_core,
            webs=[],
        )
        created.append(node)
        return node

    monkeypatch.setattr(bootstrap_docker, "PublicWebNode", _create)

    bootstrap_docker._ensure_public_web("the-key")

    assert len(created) == 1
    node = created[0]
    assert node.name == bootstrap_docker.DEFAULT_PUBLIC_WEB_NAME
    assert node.api_url == bootstrap_docker.DEFAULT_PUBLIC_WEB_URL
    assert node.api_key == "the-key"
    # The node beside core: core's own Traefik publishes its webs. An ansible-
    # registered remote node fronts its own and must never be marked.
    assert node.fronted_by_core is True

    webs = [row for row in session.added if isinstance(row, bootstrap_docker.PublicWeb)]
    assert len(webs) == 1
    assert webs[0].name == bootstrap_docker.DEFAULT_PUBLIC_WEB_WEB_NAME
    # No hostname: a node can serve several webs on several hostnames, so that is
    # set in Configuration -> Public Web, not here.
    assert webs[0].hostname == ""


def test_existing_node_keeps_its_name_and_web(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    """A renamed node is matched on api_url: no rename, no second node, no second web."""
    node = _existing("Our Public Feed", webs=[object()])
    _stub_lookup(monkeypatch, node)
    _stub_verify(monkeypatch, None)

    bootstrap_docker._ensure_public_web("the-key")

    assert node.name == "Our Public Feed"
    assert session.added == []
    assert session.commits == 0


def test_backfills_missing_api_url(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    """A node stored before api_url existed gets the core->node channel back."""
    node = _existing("Default Public Web", api_url="", webs=[object()])
    # Matched by name-independent lookup even with an empty api_url (the caller's
    # query is stubbed); the point here is the backfill.
    _stub_lookup(monkeypatch, node)
    _stub_verify(monkeypatch, None)

    bootstrap_docker._ensure_public_web("the-key")

    assert node.api_url == bootstrap_docker.DEFAULT_PUBLIC_WEB_URL
    assert session.commits == 1


def test_unreachable_node_warns_but_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
    session: _FakeSession,
    capsys: pytest.CaptureFixture,
) -> None:
    """gui/gui-v3 gate on this script exiting 0, so an absent feed must not raise."""
    _stub_lookup(monkeypatch, None)
    _stub_verify(monkeypatch, "No public-web node answered at 'http://public-web'")
    monkeypatch.setattr(bootstrap_docker, "MAX_ATTEMPTS", 3)

    bootstrap_docker._ensure_public_web("the-key")

    assert session.added == []
    assert "WARNING" in capsys.readouterr().out


def test_recovers_when_the_node_shows_up_late(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:  # noqa: ARG001
    """The retry loop is what lets a slow public-web container still be seeded.

    The ``session`` fixture is required for its sleep stub, not for its recording.
    """
    answers = ["not yet", "not yet", None]
    monkeypatch.setattr(bootstrap_docker.public_web_manager, "verify_node", lambda _url, _key: answers.pop(0))
    _stub_lookup(monkeypatch, _existing("Default Public Web", webs=[object()]))

    bootstrap_docker._ensure_public_web("the-key")

    assert answers == []
