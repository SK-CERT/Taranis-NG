#!/usr/bin/env python3
"""Build disposable real nodes and run the remote compatibility integration suite.

Usage: python3 scripts/run_remote_tests.py [--lane mixed-utc|mixed-bratislava|current|all]
Requires Docker Compose v2, the pinned legacy Git object, and the root test venv
created by ``python3 scripts/dev_setup.py --skip-gui``. Never skips prerequisites.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker" / "docker-compose.remote-tests.yml"
LEGACY_COMMIT = "53892ffeb2a0862bf2d995d2022d1d74e6357192"
LANES = ("mixed-utc", "mixed-bratislava", "current")


def run(command: list[str], *, env: dict[str, str], timeout: int = 120, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run without a shell, retaining failures and enforcing a deadline."""
    return subprocess.run(command, cwd=ROOT, env=env, check=True, text=True, capture_output=capture, timeout=timeout)


def legacy_checkout(destination: Path, env: dict[str, str]) -> None:
    """Materialize the exact historical tree without modifying the current checkout."""
    try:
        run(["git", "cat-file", "-e", f"{LEGACY_COMMIT}^{{commit}}"], env=env, capture=True)
    except subprocess.CalledProcessError as error:
        message = f"Legacy commit {LEGACY_COMMIT} is missing; run git fetch origin tag 26.10.1 first"
        raise RuntimeError(message) from error
    archive = destination.parent / "legacy.tar"
    run(["git", "archive", "--format=tar", f"--output={archive}", LEGACY_COMMIT], env=env)
    destination.mkdir()
    with tarfile.open(archive) as tree:
        tree.extractall(destination, filter="data")


def stage_current_context(destination: Path) -> None:
    """Copy the current core inputs with portable modes, preserving source bytes.

    Local workspaces may contain owner-only directories which become unreadable
    by the production image's unprivileged user. Normalize only this disposable
    copy; exclude credentials, databases, and unrelated service build inputs.
    """
    ignored = shutil.ignore_patterns(
        ".venv",
        "__pycache__",
        "dist",
        "build",
        "*.egg-info",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        "secrets",
        "tls",
        ".env*",
    )
    destination.mkdir()
    for relative in ("docker", "src/core", "src/shared"):
        shutil.copytree(ROOT / relative, destination / relative, ignore=ignored, symlinks=True)
    shutil.copy2(ROOT / ".dockerignore", destination / ".dockerignore")
    for path in (destination, *destination.rglob("*")):
        if path.is_symlink():
            continue
        path.chmod(0o755 if path.is_dir() else (path.stat().st_mode & 0o777) | 0o444)


def wait_http(url: str, deadline: float) -> None:
    """Wait for the host-facing health endpoint as well as container health."""
    last_error = "not ready"
    while time.monotonic() < deadline:
        try:
            # URL is constructed from Docker's loopback-only published HTTP port.
            with urllib.request.urlopen(f"{url}/api/v1/isalive", timeout=3) as response:  # noqa: S310
                if response.status == HTTPStatus.OK:
                    return
        except (OSError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(0.5)
    message = f"Core readiness deadline exceeded for {url}: {last_error}"
    raise TimeoutError(message)


def require_executable(executable: str) -> None:
    """Reject a missing prerequisite before creating a test stack."""
    if shutil.which(executable) is None:
        message = f"Required executable is missing: {executable}"
        raise RuntimeError(message)


def run_lane(lane: str, python: Path, artifacts_root: Path) -> int:
    """Start, exercise, diagnose, and always remove one independently named stack."""
    artifacts = artifacts_root / lane
    artifacts.mkdir(parents=True, exist_ok=True)
    # A successful local retry must not retain diagnostics from an earlier run.
    for pattern in ("runner-error.txt", "junit.xml", "containers.log", "containers.json", "run.json", "a-*.json", "b-*.json"):
        for previous in artifacts.glob(pattern):
            if previous.is_file():
                previous.unlink()
    project = f"taranis-remote-{lane}-{secrets.token_hex(4)}"
    env = os.environ.copy()
    # Explicit paths avoid the deployment .env and make helper subprocesses use
    # the same isolated stack and interpolation environment as this runner.
    env.update(
        {
            "REMOTE_TEST_ROOT": str(ROOT),
            "REMOTE_TEST_A_CONTEXT": str(ROOT),
            "REMOTE_TEST_PROJECT": project,
            "REMOTE_TEST_COMPOSE": str(COMPOSE),
            "REMOTE_TEST_ARTIFACTS": str(artifacts),
            "REMOTE_TEST_LANE": lane,
            "REMOTE_TEST_B_TIMEZONE": "Europe/Bratislava" if lane == "mixed-bratislava" else "UTC",
        },
    )
    print(f"Remote compatibility: {lane} (project {project})", flush=True)
    result = 1
    with tempfile.TemporaryDirectory(prefix="taranis-remote-") as temporary:
        workspace = Path(temporary)
        env_file = workspace / "empty.env"
        env_file.write_text("")
        env["COMPOSE_ENV_FILES"] = str(env_file)
        env["REMOTE_TEST_ENV_FILE"] = str(env_file)
        compose = ["docker", "compose", "--env-file", str(env_file), "-f", str(COMPOSE), "-p", project]
        secret_dir = workspace / "secrets"
        secret_dir.mkdir()
        env["REMOTE_TEST_SECRETS_DIR"] = str(secret_dir)
        for name in ("postgres_password", "jwt_secret_key", "api_key", "secrets_encryption_key"):
            secret = secret_dir / name
            secret.write_text(secrets.token_hex(32))
            # Docker bind-backed secrets must be readable by the app's uid 10001;
            # their parent temporary directory stays mode 0700 on the host.
            secret.chmod(0o644)
        try:
            current = workspace / "current"
            stage_current_context(current)
            env["REMOTE_TEST_A_CONTEXT"] = str(current)
            if lane == "current":
                env["REMOTE_TEST_B_CONTEXT"] = str(current)
            else:
                checkout = workspace / "legacy"
                legacy_checkout(checkout, env)
                env["REMOTE_TEST_B_CONTEXT"] = str(checkout)
            (artifacts / "run.json").write_text(
                json.dumps(
                    {
                        "lane": lane,
                        "project": project,
                        "legacy_commit": LEGACY_COMMIT if lane != "current" else None,
                        "b_timezone": env["REMOTE_TEST_B_TIMEZONE"],
                    },
                    indent=2,
                )
                + "\n",
            )
            run([*compose, "config", "--quiet"], env=env)
            run([*compose, "build"], env=env, timeout=2400)
            run([*compose, "up", "--detach", "--wait", "--wait-timeout", "420"], env=env, timeout=480)
            deadline = time.monotonic() + 60
            for node in ("a", "b"):
                binding = run([*compose, "port", f"core-{node}", "80"], env=env, capture=True).stdout.strip()
                url = f"http://{binding}"
                env[f"REMOTE_TEST_{node.upper()}_URL"] = url
                wait_http(url, deadline)
            completed = subprocess.run(
                [
                    str(python),
                    "-m",
                    "pytest",
                    "-c",
                    str(ROOT / "tests/integration/remote/pytest.ini"),
                    str(ROOT / "tests/integration/remote"),
                    "-v",
                    "--tb=short",
                    f"--junitxml={artifacts / 'junit.xml'}",
                ],
                cwd=ROOT,
                env=env,
                check=False,
                timeout=1200,
            )
            result = completed.returncode
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"Remote compatibility {lane} failed: {error}", file=sys.stderr)
            (artifacts / "runner-error.txt").write_text(str(error) + "\n")
        finally:
            # Preserve useful diagnostics even for a build/startup failure, before
            # deleting only this runner-owned project's resources.
            for filename, arguments in (("containers.json", ["ps", "--all", "--format", "json"]), ("containers.log", ["logs", "--no-color"])):
                try:
                    with (artifacts / filename).open("w") as output:
                        subprocess.run(
                            [*compose, *arguments],
                            cwd=ROOT,
                            env=env,
                            check=False,
                            stdout=output,
                            stderr=subprocess.STDOUT,
                            timeout=60,
                        )
                except (OSError, subprocess.SubprocessError) as error:
                    print(f"Could not collect {filename}: {error}", file=sys.stderr)
            try:
                run([*compose, "down", "--volumes", "--remove-orphans", "--timeout", "5"], env=env)
            except (OSError, subprocess.SubprocessError) as error:
                print(f"Cleanup failed for {project}: {error}", file=sys.stderr)
                result = 1
    return result


def main() -> int:
    """Validate prerequisites and run every requested lane, even after a failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", choices=(*LANES, "all"), default="all")
    parser.add_argument("--python", type=Path, default=ROOT / ".venv/bin/python", help="Python containing pytest and requests")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "local/remote-tests")
    args = parser.parse_args()
    env = os.environ.copy()
    try:
        for executable in ("docker", "git"):
            require_executable(executable)
        # Preserve the venv's executable path: resolving its symlink invokes the
        # global interpreter and loses the environment's installed packages.
        python = args.python.expanduser().absolute()
        run([str(python), "-c", "import pytest, requests"], env=env)
        run(["docker", "compose", "version"], env=env)
        run(["docker", "info", "--format", "{{.ServerVersion}}"], env=env)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Remote test prerequisite failed: {error}\nRun python3 scripts/dev_setup.py --skip-gui and start Docker.", file=sys.stderr)
        return 1
    lanes = LANES if args.lane == "all" else (args.lane,)
    results = [run_lane(lane, python, args.artifacts.resolve()) for lane in lanes]
    return int(any(results))


if __name__ == "__main__":
    sys.exit(main())
