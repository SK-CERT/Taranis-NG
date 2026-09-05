"""A satellite must dial the port its traffic was moved to.

``test_satellite_exposure`` pins core's half of the split - that ``/api/v1/collectors``
and friends leave ``:443`` and appear on the satellite entrypoint. That is only half a
contract. Carving those prefixes out of the public router silently invalidates every
client still pointed at the port-less public URL: no router matches, and core answers a
404 that looks nothing like a routing problem.

That is exactly what shipped. The ansible worker role handed each container
``TARANIS_NG_CORE_URL: "{{ core_url }}"`` - correct before the split, and afterwards a
url on which collectors and bots no longer exist. ansible-lint cannot see it; the value
is well-formed, just aimed at the wrong port.

So these tests assert the two ends agree on a number, by rendering the role's own
templates and comparing against the compose file core is deployed from.
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

REPO = Path(__file__).parents[3]
COMPOSE = REPO / "docker" / "docker-compose.yml"
ROLE = REPO / "ansible" / "roles" / "taranis-ng-worker"

CORE_HOST = "core.example.com"
CORE_URL = f"https://{CORE_HOST}"

# The types that call core back. presenters and publishers never do, so they have no
# stake in this - but they are rendered too, because the env block is shared and a
# regression there would show up on whichever type happens to be listed first.
WORKER_TYPES = ["collectors", "bots", "presenters", "publishers", "public-web"]


def _core_satellite_port() -> int:
    """The host port a satellite connects to on the core host.

    Deliberately the *published* port rather than the container-side entrypoint
    address: a satellite reaches core from outside the compose network, so the left
    side of the port mapping is the one it has to dial.
    """
    # Read from the raw text, not the parsed document: the mappings ship commented out
    # (a single-host install never dials the port, and binding [::1] fails where IPv6
    # loopback is off), and a distributed deployment uncomments them. The number still
    # has to agree with the one ansible hands the workers - an opt-in aimed at a port
    # nothing serves fails as timeouts, which is the whole subject of this module.
    text = COMPOSE.read_text(encoding="utf-8")
    mappings = [m.group("mapping") for m in re.finditer(r'^\s*#?\s*-\s*"(?P<mapping>[^"]*:8443)"\s*$', text, re.MULTILINE)]
    assert mappings, "the satellite entrypoint is neither published nor offered to uncomment"
    # One mapping per address family - naming a host address pins a mapping to that
    # family - so there is more than one, and they must all name the same port.
    # e.g. "${TARANIS_NG_SATELLITE_BIND:-127.0.0.1}:${TARANIS_NG_SATELLITE_PORT:-8443}:8443"
    ports = set()
    for mapping in mappings:
        default = re.search(r"TARANIS_NG_SATELLITE_PORT:-(\d+)", mapping)
        assert default, f"satellite mapping no longer carries a port default: {mapping}"
        ports.add(int(default.group(1)))
    assert len(ports) == 1, f"satellite mappings disagree on the port: {mappings}"
    return ports.pop()


#: Vars whose Jinja is resolved before rendering. Kept to the url chain on purpose -
#: many other defaults interpolate ansible-only filters (``dirname``, ``to_uuid``) that
#: plain Jinja cannot evaluate, and the templates are happy to receive those unresolved.
URL_CHAIN = ("core_satellite_url", "core_sse_url")


def _role_vars() -> dict:
    """Role defaults, with the url chain resolved the way ansible resolves it lazily.

    ``core_satellite_url`` is defined in terms of ``core_url`` and
    ``core_satellite_port``, and ``core_sse_url`` in terms of ``core_satellite_url``.
    Following the chain rather than hardcoding its result is the point: if someone
    rewrites it to bypass the satellite port, these tests go with them.
    """
    # autoescape stays off deliberately: these templates render YAML, and HTML-escaping
    # would corrupt the very values these tests parse back out. Same below.
    env = Environment()  # noqa: S701
    values = {**yaml.safe_load((ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")), "core_url": CORE_URL}
    for key in URL_CHAIN:
        assert key in values, f"{key} is no longer a role default; the satellite url chain has been restructured"
        for _ in range(len(values)):  # one pass per link of the chain
            if "{{" not in values[key]:
                break
            values[key] = env.from_string(values[key]).render(**values)
        else:
            unresolved = f"{key} did not resolve: {values[key]}"
            raise AssertionError(unresolved)
    return values


def _render(template: str, worker_types: list[str], tls_mode: str) -> str:
    """Render a role template as the play would for a host running ``worker_types``.

    The overrides go last: several of these names are role defaults too, and it is the
    play-supplied value that reaches the template at runtime.
    """
    context = {
        **_role_vars(),
        "inventory_hostname": "w1.example.com",
        "worker_base_hostname": "example.com",
        "worker_types": worker_types,
        "worker_tls_mode": tls_mode,
        "worker_effective_api_keys": dict.fromkeys(worker_types, "k"),
        "worker_selinux_mount_suffix": "",
        "worker_acme_dns_env": {},
        "worker_tz": "UTC",
        "taranis_log_level": "INFO",
        "modules_log_level": "INFO",
    }
    env = Environment(loader=FileSystemLoader(str(ROLE / "templates")), keep_trailing_newline=True)  # noqa: S701
    return env.get_template(template).render(**context)


@pytest.fixture(scope="module")
def worker_env() -> dict[str, dict]:
    """The environment block each worker container is deployed with."""
    services = yaml.safe_load(_render("docker-compose.worker.yml.j2", WORKER_TYPES, "selfsigned"))["services"]
    return {name: services[name]["environment"] for name in WORKER_TYPES}


@pytest.mark.parametrize("worker_type", WORKER_TYPES)
def test_workers_are_pointed_at_the_satellite_port(worker_type: str, worker_env: dict) -> None:
    """The bug this file exists for.

    A port-less url here means every collector and bot 404s against a core that has
    moved those prefixes, and the failure surfaces as an application error rather than
    as the routing change that caused it.
    """
    url = urlsplit(worker_env[worker_type]["TARANIS_NG_CORE_URL"])
    assert url.port == _core_satellite_port(), (
        f"{worker_type} is told to reach core at {url.geturl()}, but the prefixes it calls are only served on port {_core_satellite_port()}."
    )
    assert url.hostname == CORE_HOST, "the satellite url must keep core's hostname; only the port is added"


def test_the_bots_event_stream_uses_the_satellite_port(worker_env: dict) -> None:
    """/sse is served on both entrypoints, so this is a consistency choice, not a fix.

    A remote bots node reaching it on the restricted port keeps every satellite-generated
    connection on one port - which is what makes the firewall rule describable.
    """
    assert urlsplit(worker_env["bots"]["TARANIS_NG_CORE_SSE"]).port == _core_satellite_port()


@pytest.mark.parametrize("tls_mode", ["selfsigned", "provided", "acme"])
def test_the_scoped_provider_is_polled_on_the_satellite_port(tls_mode: str) -> None:
    """Under acme the static file carries the provider; otherwise the compose flags do.

    Both paths exist because a static config file silently beats command-line flags, so
    the role writes the provider into whichever one is authoritative for the mode. Both
    have to name the satellite port.
    """
    template = "traefik.yml.j2" if tls_mode == "acme" else "docker-compose.worker.yml.j2"
    rendered = _render(template, ["public-web"], tls_mode)

    endpoints = re.findall(r"endpoint[=:]\s*\"?(\S+?)/traefik/dynamic/node", rendered)
    assert endpoints, f"the scoped provider endpoint is missing from {template} under {tls_mode}"
    for endpoint in endpoints:
        assert urlsplit(endpoint).port == _core_satellite_port(), (
            f"{template} polls the provider at {endpoint}, which is not the satellite port"
        )
