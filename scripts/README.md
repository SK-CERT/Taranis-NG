# Repository maintenance scripts

Run these commands from the repository root.

## Release version lockstep

`VERSION.md` is the canonical release version. `bump_version.py` synchronizes:

- root, shared, and service `pyproject.toml` project versions;
- each service's `taranis-ng-shared` dependency pin;
- Vue 2 and Vue 3 `package.json` and `package-lock.json` versions; and
- root and service `uv.lock` files.

Release versions use `YY.MM.PATCH`.

```bash
# Update all version pins and refresh uv locks
python3 scripts/bump_version.py 26.08.1

# Update pins without refreshing uv locks
python3 scripts/bump_version.py 26.08.1 --no-lock

# Verify all derived pins against VERSION.md
python3 scripts/bump_version.py --check
```

The `--no-lock` form requires a later `uv lock` in the root project and every
backend service before lockfile checks can pass. Vue 3 build metadata reads
`VERSION.md` through `src/gui-v3/scripts/update-version.cjs`.

The `check-version-lockstep` pre-commit hook runs the verification command.

## Development-tool lockstep

The canonical Ruff and djLint versions are the exact pins under
`[dependency-groups].dev` in the root `pyproject.toml`.
`check_tool_versions.py` verifies that:

- `[tool.ruff].required-version` matches the Ruff dependency pin; and
- the Ruff and djLint revisions in `.pre-commit-config.yaml` match their
  dependency pins after removing a leading `v`.

```bash
# Report drift
python3 scripts/check_tool_versions.py

# Rewrite derived Ruff/djLint pins from pyproject.toml
python3 scripts/check_tool_versions.py --fix
```

The script uses only the Python standard library. Its pre-commit hook runs on
every commit, and CI consumes the root development dependency group when it
executes these tools.

## Ansible playbook syntax check

`check_ansible_syntax.py` validates every playbook under `ansible/playbooks/`
with `ansible-playbook --syntax-check`. It also installs the required Ansible
collections (from `ansible/requirements.yml`) into a project-local cache at
`.cache/ansible-collections` (gitignored) so module references like
`community.docker.docker_image` resolve correctly.

```bash
# Check all playbooks
python3 scripts/check_ansible_syntax.py

# Stream ansible-playbook output (useful when debugging)
python3 scripts/check_ansible_syntax.py --verbose

# Force a clean collection re-install (after bumping requirements.yml)
rm -rf .cache/ansible-collections
python3 scripts/check_ansible_syntax.py
```

The script needs `ansible-core` on PATH:

```bash
pip install ansible-core
```

The `ansible-syntax-check` pre-commit hook runs only when files under
`ansible/` change (so unrelated commits stay fast). The Linting CI workflow
runs the same check on every PR (with a path-based skip so PRs that don't
touch `ansible/` don't spend CI minutes installing `ansible-core`).
