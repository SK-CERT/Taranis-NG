#!/usr/bin/env python3
"""Start backend services for Taranis-NG E2E testing (cross-platform).

This is the command the Playwright ``webServer`` boots (see
``src/gui-v3/playwright.config.js`` and ``src/gui-v3/playwright.ui.config.js``).
It replaces the former ``scripts/test-setup.sh`` so the same setup works on
Windows, macOS and Linux without bash (Git Bash, WSL) on Windows.

Invariants:

  * uses the dedicated E2E compose project (``COMPOSE_PROJECT_NAME=taranis-e2e``)
    so its containers/networks/volumes are namespaced ``taranis-e2e_*`` and a
    ``down -v`` can never touch a production ``taranis-ng_*`` stack.
  * tears down any previous E2E stack AND its postgres volume before starting —
    the seed tests (``00-config-seed.spec.js``) create nodes/types/presets with
    fixed names on ``unique=True`` columns, so leftover data makes the next run
    hit a UniqueViolation (HTTP 500, surfaced in the Vue dialog as the misleading
    "Could not connect to X node.").
  * seeds any missing ``docker/secrets/*.txt`` from its ``.example`` so a fresh
    checkout boots without manual steps.
  * starts ``postgres redis core collectors presenters publishers`` with
    ``--build`` so new backend routes are available in E2E runs.
  * waits for postgres, core container health, the published localhost core API
    port, and collectors/presenters/publishers being reachable BOTH on their
    host port AND resolvable from the core container via Docker DNS — the exact
    path ``add_presenters_node`` / ``add_collectors_node`` / ``add_publishers_node``
    takes. Docker's embedded DNS resolver can lag service start; without that
    second probe the seed tests would fire before DNS resolves and 500.

The E2E env file (``docker/.env.e2e``) is parsed for ``E2E_*`` port defaults so
the readiness probes reference the right ports; the real environment overrides
them (``E2E_CORE_PORT=8091 python3 scripts/test-setup.py``).

Usage::

    python3 scripts/test-setup.py                # start, wait, exit 0 on ready
    python3 scripts/test-setup.py --timeout 240  # longer overall deadline (s)
    E2E_CORE_PORT=8091 python3 scripts/test-setup.py   # override a port

Exit status: 0 if every service is ready within the deadline, 1 otherwise (and
an explanatory message on stderr). The Playwright ``webServer`` retries this by
polling the ``url`` (isalive), so a non-zero exit here just means "try again".
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_DIR = PROJECT_ROOT / "docker"
E2E_ENV_FILE = COMPOSE_DIR / ".env.e2e"

# Default E2E_* host ports (loopback only, picked to avoid the production
# published ports). Overridable via the real environment and docker/.env.e2e.
DEFAULT_PORTS = {
    "E2E_CORE_PORT": "8090",
    "E2E_COLLECTORS_PORT": "5091",
    "E2E_PRESENTERS_PORT": "5092",
    "E2E_PUBLISHERS_PORT": "5093",
}

# Polling budget per service (seconds). Mirrors the bash loop counts
# (postgres/core: 30 tries x 1s = 30s; collectors/presenters/publishers:
# 60 tries x 1s = 60s).
DEFAULT_DEADLINE_S = 120


def log(msg: str) -> None:
    """Print a status line (flush so the Playwright webServer logs stream live)."""
    print(msg, flush=True)


def die(msg: str) -> NoReturn:
    """Print an error and exit non-zero (the webServer treats this as "not ready")."""
    print(f"✗ {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def have_docker_compose() -> str:
    """Return the compose CLI to use, preferring the standalone ``docker compose`` plugin.

    ``docker compose`` (with a space) is the v2 plugin shipping with Docker Desktop
    on all platforms; it matches what ``test-setup.sh`` used. Raise a clear error
    early if neither ``docker`` nor ``docker-compose`` is on PATH.
    """
    if shutil.which("docker") is None:
        die(
            "`docker` is not on PATH. Install Docker Desktop (or the Docker Engine) and retry. Download: https://docs.docker.com/get-docker/",
        )
    # ``docker compose`` is the v2 plugin — universally available with Docker Desktop.
    return "docker compose"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a ``KEY=value`` .env file (no shell expansion: only simple values).

    Mirrors how ``set -a; . .env.e2e`` exposes the vars in bash. Ignores blank
    lines and ``#`` comments, and strips a single pair of surrounding quotes so
    ``FOO="bar"`` → ``FOO=bar``. Does NOT honour ``export``/interpolation — the
    E2E env file uses neither, by inspection of docker/.env.e2e.
    """
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        env[key] = value
    return env


def resolve_ports(env_file_vars: dict[str, str]) -> dict[str, str]:
    """Resolve E2E_* ports with the same precedence as the bash script.

    real environment > env file > DEFAULT_PORTS. Export them so subprocesses
    (compose, curl-from-core) inherit them.
    """
    ports: dict[str, str] = {}
    for key, default in DEFAULT_PORTS.items():
        value = os.environ.get(key) or env_file_vars.get(key) or default
        ports[key] = value
        os.environ[key] = value
    return ports


def compose_cmd(*args: str, env_file: Path | None = None, project: str = "taranis-e2e") -> list[str]:
    """Build a ``docker compose`` invocation with the E2E project + env file wired in.

    Order matches test-setup.sh: ``--env-file`` first, then ``-f`` overlays, then
    ``-p`` project. ``down``/``up`` get the matching ``docker-compose.e2e.yml``
    overlay except for the bare project-status ``exec`` commands (which only need
    the base file in practice, but include both for parity with the up/down flow).
    """
    cmd = ["docker", "compose"]
    if env_file and env_file.is_file():
        cmd += ["--env-file", str(env_file)]
    cmd += ["-f", "docker-compose.yml", "-f", "docker-compose.e2e.yml", "-p", project, *args]
    return cmd


def run_quiet(cmd: list[str], cwd: Path) -> bool:
    """Run a command, suppressing output; return True on success (exit 0).

    Used for the ``down -v`` teardown and secret-seeding copies where noise
    would drown out the readiness progress messages.
    """
    try:
        subprocess.run(cmd, cwd=str(cwd), check=False, capture_output=True)
    except FileNotFoundError:
        return False
    return True


def read_url(url: str, timeout_s: float = 2.0) -> bool:
    """Return True if a URL responds with a 2xx within ``timeout_s`` seconds.

    Uses urllib from the stdlib so there's no ``requests``/``httpx`` dependency.
    A connection error, refused, or non-2xx all return False.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


def wait_for(label: str, check: Callable[[], bool], deadline_epoch: float, interval_s: float = 1.0) -> None:
    """Poll ``check()`` until it returns True or the deadline elapses.

    ``check`` is a zero-arg callable returning bool. ``label`` is printed with
    a ✓ on success or ✗ + exit on timeout. The deadline is global (not per-
    service) so a slow core container doesn't blow the whole budget for the
    later services — matches the bash script's per-loop ``i in {1..30}``.
    """
    while time.time() < deadline_epoch:
        if check():
            log(f"✓ {label}")
            return
        time.sleep(interval_s)
    die(f"{label} not ready within the deadline")


def main() -> None:
    deadline_epoch = time.time() + _overall_deadline()
    env_file_vars = parse_env_file(E2E_ENV_FILE)
    ports = resolve_ports(env_file_vars)

    have_docker_compose()  # fail fast if docker isn't installed

    log(
        f"Starting Taranis-NG backend services for E2E tests (project=taranis-e2e, core=127.0.0.1:{ports['E2E_CORE_PORT']})...",
    )

    # --- Tear down any previous E2E stack AND its postgres volume ------------
    # The named postgres volume is namespaced taranis-e2e_postgres_data, so
    # ``down -v`` only ever wipes the E2E stack's own volumes and cannot touch
    # a production ``taranis-ng_*`` stack. ``|| true`` → ignore errors if the
    # stack doesn't exist yet (first run).
    run_quiet(
        compose_cmd("down", "-v", "--remove-orphans", env_file=E2E_ENV_FILE),
        cwd=COMPOSE_DIR,
    )

    # --- Seed missing secrets from their .example ----------------------------
    # ``docker/secrets/*.txt`` is gitignored; developers copy the .example
    # files. Seed any missing one so a fresh checkout — or one predating a newly
    # added secret — boots the stack without manual steps.
    for example in sorted((COMPOSE_DIR / "secrets").glob("*.txt.example")):
        secret = example.with_suffix("")  # strip .example → the real secret path
        if not secret.exists():
            log(f"Seeding missing secret {secret.name} from its example")
            shutil.copy2(example, secret)

    # --- Start core, postgres, redis with localhost port exposure -----------
    # ``--build`` rebuilds the core image from the current workspace so new
    # backend routes are available in E2E runs. Captures output on failure
    # only, so a clean up doesn't spam the log.
    log("Starting containers (postgres redis core collectors presenters publishers)...")
    cmd = compose_cmd(
        "up",
        "-d",
        "--build",
        "postgres",
        "redis",
        "core",
        "collectors",
        "presenters",
        "publishers",
        env_file=E2E_ENV_FILE,
    )
    result = subprocess.run(cmd, cwd=str(COMPOSE_DIR), check=False, capture_output=True, text=True)
    if result.returncode != 0:
        die(f"docker compose up failed:\n{result.stdout}\n{result.stderr}")

    log("Waiting for services to be ready...")

    # --- Wait for postgres ---------------------------------------------------
    def postgres_ready() -> bool:
        # pg_isready is the canonical readiness check; -U matches the compose
        # service's POSTGRES_USER. Runs inside the postgres container.
        ps = subprocess.run(
            compose_cmd("exec", "-T", "postgres", "pg_isready", "-U", "taranis-ng"),
            cwd=str(COMPOSE_DIR),
            check=False,
            capture_output=True,
        )
        return ps.returncode == 0

    wait_for("PostgreSQL is ready", postgres_ready, deadline_epoch)

    # --- Wait for core container health -------------------------------------
    # The core service defines a healthcheck; ``ps --format json`` is unreliable
    # across compose versions for "healthy" (some emit "running":true, others
    # "State":"running" strings), so match on the long-form human status text
    # which ALWAYS includes "healthy" once the container is healthy.
    def core_healthy() -> bool:
        ps = subprocess.run(
            compose_cmd("ps", "core"),
            cwd=str(COMPOSE_DIR),
            check=False,
            capture_output=True,
            text=True,
        )
        return ps.returncode == 0 and "healthy" in ps.stdout

    wait_for("Core container is healthy", core_healthy, deadline_epoch)

    # --- Verify the published localhost port is reachable --------------------
    # Playwright's webServer probes THIS url after the script exits, so it must
    # be 200 before we return 0.
    core_url = f"http://127.0.0.1:{ports['E2E_CORE_PORT']}/api/v1/isalive"

    def core_api_up() -> bool:
        return read_url(core_url)

    wait_for(f"Core API is reachable on localhost:{ports['E2E_CORE_PORT']}", core_api_up, deadline_epoch)

    # --- Wait for collectors / presenters / publishers ----------------------
    # Each service must be reachable on its host port AND resolvable from the
    # core container via Docker DNS — the exact path the seed tests' node-add
    # calls take. Docker's embedded DNS resolver can lag service start by a few
    # seconds; without the in-core check the seed tests would fire before DNS
    # resolves and 500 with the misleading "Could not connect to X node."
    service_ports = {
        "collectors": ports["E2E_COLLECTORS_PORT"],
        "presenters": ports["E2E_PRESENTERS_PORT"],
        "publishers": ports["E2E_PUBLISHERS_PORT"],
    }
    for service, port in service_ports.items():
        host_url = f"http://127.0.0.1:{port}/api/v1/isalive"

        def both_up(host_url: str = host_url, service: str = service) -> bool:
            # 1) the service's own HTTP serves on its host port-forward
            if not read_url(host_url):
                return False
            # 2) the core container can resolve it via Docker DNS
            exec_cmd = compose_cmd(
                "exec",
                "-T",
                "core",
                "curl",
                "-sf",
                f"http://{service}/api/v1/isalive",
            )
            ps = subprocess.run(exec_cmd, cwd=str(COMPOSE_DIR), check=False, capture_output=True)
            return ps.returncode == 0

        wait_for(
            f"{service} is ready (isalive on :{port} AND core resolves http://{service})",
            both_up,
            deadline_epoch,
        )

    log("✓ All services ready")


def _overall_deadline() -> float:
    """Read ``--timeout`` (seconds) from argv, defaulting to DEFAULT_DEADLINE_S."""
    args = sys.argv[1:]
    deadline = float(DEFAULT_DEADLINE_S)
    for i, arg in enumerate(args):
        if arg == "--timeout" and i + 1 < len(args):
            try:
                deadline = float(args[i + 1])
            except ValueError:
                die(f"--timeout expects a number of seconds, got {args[i + 1]!r}")
    return deadline


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("Interrupted")
