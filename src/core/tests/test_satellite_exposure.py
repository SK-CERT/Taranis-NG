"""Which core paths are reachable on which port.

The browser and the satellites share ``/api/`` but not a single prefix below it, and
that is the whole basis of the split: the GUI keeps ``:443`` while collectors, bots and
public-web move to a port a firewall can restrict to the worker hosts.

Carving prefixes out of the public router is the edit in all of this most likely to
break something quietly - a mistake there does not fail loudly, it 404s part of the GUI.
So the rules are asserted here as behaviour ("which entrypoint serves this path"),
rather than as strings.
"""

import re
from pathlib import Path

import pytest
import yaml

COMPOSE = Path(__file__).parents[3] / "docker" / "docker-compose.yml"

# Paths the browser calls. None of these may leave :443.
BROWSER_PATHS = (
    "/api/v1/config/public-web-nodes",
    "/api/v1/config/collectors-nodes",
    "/api/v1/config/bots-nodes",
    "/api/v1/assess/news-items",
    "/api/v1/auth/login",
    "/api/v1/isalive",
)

# Paths only a satellite calls. None of these may stay on :443.
SATELLITE_PATHS = (
    "/api/v1/collectors/news-items",
    "/api/v1/bots/news-item-data",
    "/api/v1/public-web/products",
)


@pytest.fixture(scope="module")
def core_labels() -> dict:
    """The Traefik labels declared on the core service."""
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]["core"]["labels"]


def _rules(labels: dict) -> dict[str, str]:
    """Map router name -> rule expression."""
    return {key.split(".routers.")[1].removesuffix(".rule"): value for key, value in labels.items() if key.endswith(".rule")}


def _serves(rule: str, path: str) -> bool:
    """Whether a rule matches a path.

    Only the subset used here: PathPrefix terms, negated PathPrefix terms, and ``||``
    between the positives. Host() is ignored - every one of these rules carries the
    same host, so it cannot distinguish them.
    """
    positives = re.findall(r"(?<!!)PathPrefix\(`([^`]+)`\)", rule)
    negatives = re.findall(r"!PathPrefix\(`([^`]+)`\)", rule)
    if any(path.startswith(prefix) for prefix in negatives):
        return False
    return any(path.startswith(prefix) for prefix in positives)


def _entrypoints_for(labels: dict, path: str) -> set[str]:
    """Every entrypoint whose router would serve this path."""
    serving = set()
    for router, rule in _rules(labels).items():
        if _serves(rule, path):
            serving.add(labels[f"traefik.http.routers.{router}.entrypoints"])
    return serving


@pytest.mark.parametrize("path", BROWSER_PATHS)
def test_the_browser_api_stays_on_the_public_entrypoint(path: str, core_labels: dict) -> None:
    """Carving out the satellite prefixes must not take the GUI with it."""
    assert "websecure" in _entrypoints_for(core_labels, path), (
        f"{path} is no longer served on :443 - the GUI calls it, so an exclusion has gone too far."
    )


@pytest.mark.parametrize("path", SATELLITE_PATHS)
def test_satellite_paths_leave_the_public_entrypoint(path: str, core_labels: dict) -> None:
    """The point of the split: these must not stay reachable from the world."""
    assert "websecure" not in _entrypoints_for(core_labels, path), (
        f"{path} is still served on :443, so restricting the satellite port protects nothing."
    )


@pytest.mark.parametrize("path", SATELLITE_PATHS)
def test_satellite_paths_are_served_on_the_satellite_entrypoint(path: str, core_labels: dict) -> None:
    """Having moved them, they still have to be reachable by a worker."""
    assert "satellite" in _entrypoints_for(core_labels, path)


def test_sse_is_served_on_both(core_labels: dict) -> None:
    """The one dual-use path: the browser needs it, and so does a remote bots node."""
    assert _entrypoints_for(core_labels, "/sse") == {"websecure", "satellite"}


def test_the_scoped_provider_route_is_published(core_labels: dict) -> None:
    """A remote node's Traefik has to be able to poll it."""
    assert "satellite" in _entrypoints_for(core_labels, "/traefik/dynamic/node")


def test_the_unscoped_provider_route_is_not_published(core_labels: dict) -> None:
    """It carries every node's webs and the private keys inlined beside them.

    It is safe only because nothing routes it: the local Traefik reaches it over the
    compose network. A router matching it - including one matching it by prefix on the
    way to the scoped route - would publish all of that.
    """
    assert _entrypoints_for(core_labels, "/traefik/dynamic") == set()


def _satellite_mappings() -> list[str]:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return [p for p in compose["services"]["traefik"]["ports"] if "8443" in p]


def test_the_satellite_port_is_not_exposed_by_default() -> None:
    """A single-host install never uses it, so it must not open a port to the world."""
    published = _satellite_mappings()
    assert published, "the satellite entrypoint is no longer published at all"
    assert all("-127.0.0.1}" in p or "-::1}" in p for p in published), (
        "every satellite mapping must default to a loopback bind; a distributed deployment opts in explicitly"
    )


def test_the_satellite_port_is_published_on_both_address_families() -> None:
    """Naming a host address pins a mapping to that family.

    Publishing only "0.0.0.0:8443:8443" leaves the port unreachable for a worker that
    resolves core's AAAA record - and unreachable as a timeout rather than a refusal,
    because with nothing published on v6 the packets fall through to filter/INPUT and a
    default-deny host firewall drops them. The other ports name no address at all and
    are dual-stack for free; these two have to ask for it.
    """
    published = _satellite_mappings()
    assert any(p.startswith("${TARANIS_NG_SATELLITE_BIND:-") for p in published), "no IPv4 satellite mapping"
    assert any(p.startswith("[${TARANIS_NG_SATELLITE_BIND6:-") for p in published), (
        "no IPv6 satellite mapping - a worker resolving an AAAA record cannot reach the port"
    )
