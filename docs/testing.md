# Testing

Two commands install dependencies and run the default suites.

```bash
python3 scripts/dev_setup.py      # install (add --all for Playwright browsers + ansible)
python3 scripts/run_tests.py      # run every suite except e2e
```

## The suites

| Suite | What it covers | Where it lives |
| --- | --- | --- |
| `pytest` | Python unit tests | `src/core/tests`, `src/shared/tests`, and one suite per service (see `PYTEST_SUITES`) |
| `vitest` | GUI unit/component tests | `src/gui/tests/unit` |
| `ansible` | Playbook syntax check + `ansible-lint` | `ansible/playbooks`, `ansible/roles` |
| `e2e` | Playwright end-to-end | `src/gui/tests/e2e` |

`e2e` is **not** in the default set: it builds and boots a Docker stack and takes minutes.
Ask for it explicitly.

```bash
python3 scripts/run_tests.py --suite pytest            # one suite (repeatable)
python3 scripts/run_tests.py --suite e2e               # needs Docker
python3 scripts/run_tests.py --all                     # everything
python3 scripts/run_tests.py --suite pytest -- -k saml # extra args go to the tool
```

A suite whose tooling is not installed **skips** rather than fails, so a partial checkout
can still commit. CI adds `--require`, which turns each skip into a failure.

## Remote synchronization compatibility

The separate **Remote Compatibility Tests** workflow
(`.github/workflows/remote-tests.yml`) runs on pull requests, pushes to `main`, and manual
dispatch. Its contract job runs the remote API, client, model, timezone migration, and
shared protocol tests against a disposable PostgreSQL service. Its integration
jobs build real core services from the current checkout and the unmodified v1-only
release `26.10.1`, pinned to commit
`53892ffeb2a0862bf2d995d2022d1d74e6357192`.

| Lane | Nodes and timezones | Protocol and direction |
| --- | --- | --- |
| `mixed-utc` | Current UTC + legacy UTC | v1 in both directions |
| `mixed-bratislava` | Current UTC + legacy Europe/Bratislava | v1 in both directions, with explicit peer timezone settings |
| `current` | Two current UTC nodes | v2 in both directions |

Each lane has two cores, independent PostgreSQL databases and Redis services, and real
SSE forwarding. It does not start the GUI or collector, presenter, publisher, or bot
services. The tests check database-backed news and report imports, acknowledgments,
incremental updates, replay, sharing filters, authentication, and timestamp contracts.
Report payload and persistence are covered; full report rendering is outside this suite.

Run the same lanes locally from the repository root:

```bash
python3 scripts/dev_setup.py --skip-gui
python3 scripts/run_remote_tests.py --lane mixed-utc
python3 scripts/run_remote_tests.py --lane mixed-bratislava
python3 scripts/run_remote_tests.py --lane current
# Or run all three lanes (the default):
python3 scripts/run_remote_tests.py
```

The runner requires Git, a working Docker engine with Compose v2, and the root `.venv`
with pytest and requests. If the pinned legacy commit is absent from a shallow checkout,
fetch it with `git fetch origin tag 26.10.1`. The runner archives that exact commit into
a temporary directory; it does not patch the historical application. A read-only timezone
data volume supplies the historical image with the IANA database needed for non-UTC
deployments. The current build inputs are copied into a temporary context with readable
permissions, preserving source bytes and leaving the checkout unchanged. Missing tooling
or a failed historical build is a failure, never a skip. The runner uses a dedicated Compose
project and disposable credentials and volumes, waits for readiness and synchronization
with deadlines, and removes its own stack after the run. Host-facing ports are allocated
dynamically and bind only to loopback. JUnit XML, run metadata, database snapshots, and
container diagnostics are written under `local/remote-tests/<lane>/`;
CI uploads these artifacts with a 14-day retention period.

Console output shows image build and container readiness status, the tested behaviors,
and pytest results.
Dependency installation and Docker build details (including legacy `uv build` and
`uv export` output) stay in `setup.log` (CI), `build.log`, `startup.log`, and
`cleanup.log` in the artifacts directory, including when setup fails.
Use `--artifacts PATH` to choose another output directory and `--python PATH` to select
another interpreter containing pytest and requests. These integration tests are intentionally separate from
`scripts/run_tests.py`'s unit suites and are stored under `tests/integration/remote`,
with their own pytest configuration so the core unit tests' stub config cannot affect
running nodes. Replay tests temporarily reject acknowledgment writes in the disposable
provider database, then retry the imported batch through the real SSE listener.

For a quick contract-only check after installing the Python dependencies, run the
following command. Set `TARANIS_TEST_POSTGRES_URL` to a disposable PostgreSQL database
URL (`postgresql+psycopg://...`) to include the migration database cases; otherwise only
those cases are skipped locally. CI always supplies this database.

```bash
.venv/bin/python -m pytest -v \
  src/core/tests/test_remote_api_versions.py \
  src/core/tests/test_remote_client_compat.py \
  src/core/tests/test_remote_model_compat.py \
  src/core/tests/test_remote_timezone_migration.py \
  src/shared/tests/test_remote_protocol.py
```

## Installation

`scripts/dev_setup.py` builds **one** `.venv` at the repository root holding the dev
tooling, pytest, and every backend service's runtime dependencies, plus
`src/gui/node_modules`.

One environment rather than one per service is deliberate: an editor's Python extension
issues a single pytest invocation per workspace folder, so per-service virtualenvs would
limit the Testing view to whichever one it was pointed at.

```bash
python3 scripts/dev_setup.py --check      # report what is missing, install nothing
python3 scripts/dev_setup.py --skip-gui   # Python only
python3 scripts/dev_setup.py --all        # + Playwright browsers + ansible tooling
```

Two caveats worth knowing:

- **Never run a bare `uv sync`** against the root `.venv` afterwards. `uv sync` makes the
  environment match the declared groups exactly, so it removes the service dependencies
  `dev_setup.py` added. Re-running `dev_setup.py` puts them back.
- A lone `uv sync --group test` (or `--group ansible`) **prunes `.venv/bin/uv`**, and no
  other uv exists on a typical machine to run the command that would restore it. Always
  pass `--group dev` alongside; `dev_setup.py` already does.

## Editor setup (VS Code)

`.vscode/` is intentionally not committed, so nothing here is forced on you and your local
tweaks never show up as repository changes. Test discovery instead comes from committed
configuration, and you enable it once.

Install these extensions:

- **Python** (`ms-python.python`) — pytest discovery
- **Vitest** (`vitest.explorer`) — Vitest discovery
- **Playwright Test for VSCode** (`ms-playwright.playwright`) — e2e discovery

Then, in your workspace settings:

```jsonc
{
    // The one root environment dev_setup.py builds.
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    // No path arguments: pytest reads `testpaths` from the root pyproject.toml, which
    // lists every project's suite. Naming one path limits the Testing view to it; naming
    // two makes pytest fall back to their common ancestor as rootdir, where no config
    // applies and every core import fails at collection.
    "python.testing.pytestArgs": []
}
```

Vitest and Playwright need no settings — both extensions discover
`src/gui/vitest.config.js` and `src/gui/playwright.config.js` on their own.

## Where versions come from

Each tool version is declared **once**:

| Tool | Single source |
| --- | --- |
| pytest | root `pyproject.toml` → `[dependency-groups] test` |
| ruff, djlint | root `pyproject.toml` → `[dependency-groups] dev` |
| uv | root `pyproject.toml` → `[tool.uv] required-version` |
| ansible-core, ansible-lint | root `pyproject.toml` → `[dependency-groups] ansible` |
| vitest, Playwright | `src/gui/package.json` |
| Python (CI) | `.github/python-version` |
| Node (CI) | `src/gui/.nvmrc` |
| Release version | `VERSION.md` |

Nothing restates them. The workflows omit `version:` on `astral-sh/setup-uv` so it reads
`required-version` itself, and use `python-version-file` / `node-version-file` rather than
literals. Dependabot bumps each source in one place.

`scripts/check_tool_versions.py` guards the derived pins that cannot be avoided (ruff and
djlint also appear as `rev:` in `.pre-commit-config.yaml`), and
`scripts/bump_version.py --check` guards the release version across every pyproject,
`package.json` and the `TARANIS_NG_TAG` in the docker env files.

## Pre-commit

```bash
pre-commit run --all-files
```

Each test hook is gated by path, so a commit only pays for what it can affect: Python
changes run pytest, `src/gui` changes run lint-staged and Vitest, `ansible/` changes run
the syntax check and lint. All three go through `scripts/run_tests.py`, the same entry
point CI uses.

> `pre-commit run --all-files` also runs `ruff --fix` across the whole tree, which
> reformats a few dozen files of pre-existing import-sorting debt. That is expected; CI
> lints only the files a pull request touches.

## Known gaps

- **`src/presenters/tests` runs with a stubbed config.** The service reads its Docker
  secret (`/run/secrets/api_key`) at import time, so `tests/conftest.py` injects a stub
  `config` module before any application import — the same pattern `src/core/tests`
  uses. `tests/__init__.py` is deliberately absent (matching core) so pytest imports the
  test modules top-level instead of walking up to the service-root `__init__.py`.
- **`src/bots` has no tests yet.** Add a `tests/` directory, then list the project in
  `PYTEST_SUITES` in `scripts/run_tests.py` and in `testpaths` in the root
  `pyproject.toml`.
- **`src/collectors/tests` covers the email and CSAF collectors, and the scheduling they
  share.** It stubs `config` and `TARANIS_NG_CORE_URL` the way presenters does, since
  `remote/core_api.py` reads both at import time. The CSAF tests answer every request from
  a fake fetcher and sign their documents with a key generated for the run, so they never
  reach the network. The RSS, web, Slack and Twitter collectors all reach the network in
  `collect()` and have no coverage.
- **`src/publishers/tests` has to bind its own package before pytest does.** It stubs
  `config` like presenters, and works around a service-root/inner-package name clash on
  top of that: `src/publishers/__init__.py` makes the service root a package called
  `publishers`, so pytest imports it, its `from .app import create_app` reaches
  `managers/publishers_manager.py`'s `from publishers.email_publisher import ...` while
  that same name is still half-initialized, and collection dies on `ModuleNotFoundError:
  No module named 'publishers.email_publisher'` — even for an empty test file, and
  `--import-mode=importlib` does not help. `tests/conftest.py` therefore imports
  `publishers` itself first, binding it to the inner package the way the running service
  does (its `PYTHONPATH` is `/app`); pytest then finds it in `sys.modules` and never
  executes the service-root `__init__`. Presenters has the same clash and survives it
  only by luck of `sys.path` ordering, so do not read that suite as proof the layout is
  fine.
- **`managers/ssh_host_keys.py` still has no coverage.** Its host-key verification is a
  security control, and the publishers suite covers key loading and the publishers
  themselves but not the pinning policy.
