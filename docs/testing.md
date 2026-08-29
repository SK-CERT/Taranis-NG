# Testing

Two commands cover everything.

```bash
python3 scripts/dev_setup.py      # install (add --all for Playwright browsers + ansible)
python3 scripts/run_tests.py      # run every suite except e2e
```

## The suites

| Suite | What it covers | Where it lives |
| --- | --- | --- |
| `pytest` | Python unit tests | `src/core/tests`, `src/shared/tests` |
| `vitest` | GUI unit/component tests | `src/gui-v3/tests/unit` |
| `ansible` | Playbook syntax check + `ansible-lint` | `ansible/playbooks`, `ansible/roles` |
| `e2e` | Playwright end-to-end | `src/gui-v3/tests/e2e` |

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

## Installation

`scripts/dev_setup.py` builds **one** `.venv` at the repository root holding the dev
tooling, pytest, and every backend service's runtime dependencies, plus
`src/gui-v3/node_modules`.

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
`src/gui-v3/vitest.config.js` and `src/gui-v3/playwright.config.js` on their own.

> If the Vitest extension ever attaches to the legacy Vue 2 GUI at `src/gui`, point it at
> the right config with `"vitest.rootConfig": "src/gui-v3/vitest.config.js"`. That
> directory carries a `node_modules` containing Vitest but no config of its own, which has
> caused exactly this confusion before.

## Where versions come from

Each tool version is declared **once**:

| Tool | Single source |
| --- | --- |
| pytest | root `pyproject.toml` → `[dependency-groups] test` |
| ruff, djlint | root `pyproject.toml` → `[dependency-groups] dev` |
| uv | root `pyproject.toml` → `[tool.uv] required-version` |
| ansible-core, ansible-lint | root `pyproject.toml` → `[dependency-groups] ansible` |
| vitest, Playwright | `src/gui-v3/package.json` |
| Python (CI) | `.github/python-version` |
| Node (CI) | `src/gui-v3/.nvmrc` |
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
changes run pytest, `src/gui-v3` changes run lint-staged and Vitest, `ansible/` changes run
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
- **`src/bots`, `src/collectors`, `src/publishers` have no tests yet.** Add a `tests/`
  directory, then list the project in `PYTEST_SUITES` in `scripts/run_tests.py` and in
  `testpaths` in the root `pyproject.toml`.
