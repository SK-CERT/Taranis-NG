# Release version bumping

`bump_version.py` bumps the release version everywhere at once. `VERSION.md`
is the canonical source; the derived locations are:

- `pyproject.toml` (root), `src/shared/pyproject.toml` — `[project] version`
- `src/{bots,collectors,core,presenters,publishers}/pyproject.toml` —
  `[project] version` **and** the `taranis-ng-shared==X` dependency pin
- `src/gui/package.json` + `package-lock.json`, `src/gui-v3/package.json` +
  `package-lock.json` — root-package `version` fields

```bash
# Cut a new release version: rewrites VERSION.md + all pins above, then
# re-runs `uv lock` in the root workspace and all 5 services.
python3 scripts/bump_version.py 26.08.1

# Same, but skip the relock (CI check-locks will fail until locks are refreshed)
python3 scripts/bump_version.py 26.08.1 --no-lock

# Verify every pin matches VERSION.md (exit 0 = OK, exit 1 = drift found)
python3 scripts/bump_version.py --check
```

The `--check` mode runs on every commit through the `check-version-lockstep`
pre-commit hook, so a partial manual bump is blocked before it lands. The
gui-v3 build metadata (`src/gui-v3/scripts/update-version.cjs`) reads
`VERSION.md` at build time (falling back to `package.json`), so it needs no
separate pin.

# Dev tool version lockstep

`check_tool_versions.py` enforces that the `ruff` and `djlint` versions pinned
across the repository stay in sync. It is wired in as a local pre-commit hook
(`check-tool-versions-lockstep`) so drift is caught before push.

## Single source of truth

The canonical versions live in the `[dependency-groups] dev` section of the
**root** `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "djlint==1.40.4",
    "ruff==0.15.21",
]
```

The following locations must agree with it:

| Location | Key | Match rule |
|----------|-----|------------|
| `pyproject.toml` | `[tool.ruff] required-version` | exact equality (e.g. `"0.15.21"`) |
| `.pre-commit-config.yaml` | `rev:` of `astral-sh/ruff-pre-commit` | leading `v` stripped, then equal |
| `.pre-commit-config.yaml` | `rev:` of `djlint/djLint` | leading `v` stripped, then equal |

CI (`.github/workflows/linting.yaml`) consumes the dev group transitively via
`uv run --group dev <tool>`, so there is no separate CI pin to drift.

## Usage

```bash
# Check lockstep (exit 0 = OK, exit 1 = drift found)
python3 scripts/check_tool_versions.py

# Auto-realign pyproject.toml [tool.ruff] required-version and the two
# pre-commit rev: values to match the dev group
python3 scripts/check_tool_versions.py --fix
```

The same check also runs automatically on every commit through the
`check-tool-versions-lockstep` pre-commit hook.

## Update flow

| Event | What gets bumped | How lockstep is restored |
|-------|------------------|-------------------------|
| Dependabot `uv` PR merges | `[dependency-groups] dev` in `pyproject.toml` | run `--fix` (or the pre-commit hook will flag the drift until the pre-commit `rev:`s match) |
| Dependabot `pre-commit` PR merges | `rev:` in `.pre-commit-config.yaml` | same — the guard ensures `[tool.ruff] required-version` matches |
| Manual edit to any single pin | that one file | pre-commit hook blocks the commit until the other locations agree |

### Typical bump workflow

1. Dependabot opens a PR bumping `ruff` in `[dependency-groups] dev` (e.g. `0.15.21` → `0.15.22`).
2. Pull the branch locally and run:
   ```bash
   python3 scripts/check_tool_versions.py --fix
   ```
   This rewrites `[tool.ruff] required-version` and the `astral-sh/ruff-pre-commit` `rev:` to `0.15.22` / `v0.15.22`.
3. Verify and commit. Run pre-commit to confirm everything is green:
   ```bash
   pre-commit run --all-files
   ```
4. If Dependabot's `pre-commit` PR for the same bump arrives separately, close it as a duplicate (or let it rebase; the guard will already be satisfied).

## Design notes

- The script uses only the Python standard library (`tomllib`, `re`, `argparse`),
  so it can run under the system interpreter with no dependencies installed.
- The canonical pin is always `[dependency-groups] dev`. The other locations are
  considered *derived*; `--fix` only ever rewrites them to match the dev group,
  never the other way around.
- Because CI resolves tools via `uv run --group dev`, a correctly bumped dev
  group is sufficient for CI to pick up the new version — no CI edit needed.
