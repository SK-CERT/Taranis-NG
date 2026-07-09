#!/usr/bin/env bash
# Set up a local Python development environment for Taranis-NG.
#
# Creates (or reuses) a .venv at the project root and installs the shared
# package plus the dependencies of every backend service so that IDEs,
# type-checkers (ty/ruff/pyright), and local runs can resolve all imports.
#
# Usage:
#   ./scripts/setup-python-dev.sh          # create .venv and install everything
#   ./scripts/setup-python-dev.sh --recreate  # delete .venv and start fresh
#
# Requirements:
#   - Python 3.12+ ( python3 --version )
#   - uv  ( pip install uv  or  curl -LsSf https://astral.sh/uv/install.sh | sh )

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# Colors --------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}ℹ${NC}  $*"; }
ok()    { echo -e "${GREEN}✓${NC}  $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✗${NC}  $*" >&2; }

# Preflight checks ----------------------------------------------------------
info "Checking prerequisites…"

if ! command -v python3 &>/dev/null; then
    error "python3 is not installed. Install Python 3.12+ and try again."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python: $PY_VERSION ($(command -v python3))"

if ! command -v uv &>/dev/null; then
    warn "uv is not found in PATH. Attempting to install it…"
    # Prefer pipx (handles externally-managed Python cleanly via PEP 668).
    if command -v pipx &>/dev/null; then
        info "Installing uv via pipx…"
        pipx install uv
        export PATH="$HOME/.local/bin:$PATH"
    else
        error "pipx is not installed. Install it first: apt install pipx && pipx ensurepath"
        error "Then re-run this script."
        exit 1
    fi
    if ! command -v uv &>/dev/null; then
        error "uv installation failed. Install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
fi
ok "uv: $(uv --version)"

# --recreate: delete existing venv -----------------------------------------
if [[ "${1:-}" == "--recreate" ]]; then
    if [[ -d "$VENV_DIR" ]]; then
        warn "Deleting existing $VENV_DIR …"
        rm -rf "$VENV_DIR"
        ok "Removed .venv"
    fi
fi

# Create venv ---------------------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtualenv at $VENV_DIR …"
    uv venv "$VENV_DIR" --python python3
    ok ".venv created"
else
    info "Reusing existing $VENV_DIR"
fi

# Activate helper -----------------------------------------------------------
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

UV_PIP=(uv pip install --python "$VENV_DIR/bin/python")

# Upgrade pip ---------------------------------------------------------------
info "Upgrading pip…"
"${UV_PIP[@]}" --upgrade pip setuptools wheel
ok "pip/setuptools/wheel up to date"

# Install shared package (editable) -----------------------------------------
info "Installing shared package (editable)…"
"${UV_PIP[@]}" --editable "$PROJECT_ROOT/src/shared"
ok "shared installed"

# Install every backend service's dependencies ------------------------------
# We install dependencies only (not the packages themselves) because some services
# (e.g. core) use a flat-layout that setuptools auto-discovery can't handle.
# For dev environments we only need the deps resolvable — the source is on
# PYTHONPATH via .vscode/settings.json extraPaths.
SERVICES=(core bots collectors presenters publishers public_web)

for svc in "${SERVICES[@]}"; do
    info "Installing dependencies for: $svc"
    # Extract dependencies from pyproject.toml and install them directly via uv pip install.
    "${UV_PIP[@]}" --requirement <(
        python3 -c "
import tomllib, sys
with open('$PROJECT_ROOT/src/$svc/pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
for dep in data.get('project', {}).get('dependencies', []):
    print(dep)
"
    )
    ok "$svc dependencies installed"
done

# Install dev tooling (ty type checker + ruff linter) declared in the root
# [dependency-groups] dev = [...]. Pinned to match .pre-commit-config.yaml so
# local `ty check <files>` / `ruff check` runs match CI & pre-commit behavior.
info "Installing dev tooling (ty, ruff)…"
"${UV_PIP[@]}" --group dev
ok "dev tooling installed: $(ty --version 2>/dev/null || echo 'ty'), $(ruff --version 2>/dev/null || echo 'ruff')"

# Verification ---------------------------------------------------------------
info "Verifying key imports…"

VERIFY_SCRIPT=$(cat <<'PYEOF'
import importlib

packages = [
    ("flask", "Flask"),
    ("flask_restful", "flask-RESTful"),
    ("flask_jwt_extended", "flask-jwt-extended"),
    ("flask_sqlalchemy", "flask-sqlalchemy"),
    ("sqlalchemy", "SQLAlchemy"),
    ("alembic", "alembic"),
    ("gevent", "gevent"),
    ("gunicorn", "gunicorn"),
    ("marshmallow", "marshmallow"),
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("dotenv", "python-dotenv"),
    ("keycloak", "python-keycloak"),
    ("Cryptodome", "pycryptodomex"),
    ("langchain", "langchain"),
    ("langchain_openai", "langchain-openai"),
    ("bleach", "bleach"),
    ("cachelib", "cachelib"),
    ("cvss", "cvss"),
    ("feedgen", "feedgen"),
    ("envelope", "envelope"),
    ("schedule", "schedule"),
    ("sseclient", "sseclient-py"),
    ("dateutil", "python-dateutil"),
    ("selenium", "selenium"),
    ("socks", "PySocks"),
    ("shared.common", "taranis-ng-shared"),
]

failed = []
for module, pip_name in packages:
    try:
        importlib.import_module(module)
    except ImportError:
        failed.append(pip_name)

if failed:
    print(f"  ⚠ Missing: {', '.join(failed)}")
    exit(1)
else:
    print("  All key imports resolved.")
PYEOF
)

if python3 -c "$VERIFY_SCRIPT"; then
    ok "Environment ready!"
else
    warn "Some imports failed — see messages above."
fi

# Summary -------------------------------------------------------------------
echo ""
echo -e "${BOLD}Python dev environment is ready.${NC}"
echo ""
echo "  Venv:      $VENV_DIR"
echo "  Python:    $("$VENV_DIR/bin/python" --version)"
echo "  Packages:  $("$VENV_DIR/bin/pip" list --format=freeze 2>/dev/null | wc -l) installed"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Reload VS Code:  Ctrl+Shift+P → 'Developer: Reload Window'"
echo "  2. The interpreter at $VENV_DIR/bin/python should be auto-detected."
echo "     If not: Ctrl+Shift+P → 'Python: Select Interpreter' → choose .venv"
echo ""
