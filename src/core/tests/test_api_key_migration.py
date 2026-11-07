"""The API key migration matches the models, keeps existing keys working and can run again.

``5a9e3c7d1b42`` hashes the stored keys in place, adds the scope, allowlist and usage columns,
the scope table, the policy columns and the permissions. A core started with the new models
creates ``api_key_permission`` itself (``db.create_all()``), so the migration checks before
creating. Like the other migration tests, these need no database.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

from api import config as config_api
from model.apikey import ApiKey, ApiKeyPermission, hash_key
from model.security_settings import SecuritySettings

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
VERSIONS = CORE_ROOT / "migrations" / "versions"
MIGRATION = VERSIONS / "5a9e3c7d1b42_api_key_management.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("api_key_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function_source(name: str) -> str:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    return ast.unparse(next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name))


def test_the_migration_extends_the_products_head() -> None:
    module = _load()
    assert module.revision == "5a9e3c7d1b42"
    assert module.down_revision == "72f1a157e289"
    revises = re.compile(r'^down_revision = "72f1a157e289"$', re.MULTILINE)
    children = [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_existing_keys_are_hashed_like_the_model_hashes_a_presented_key() -> None:
    """Postgres' sha256 over the key's UTF-8 bytes, hex encoded, is hashlib's digest."""
    body = _function_source("_hash_keys")
    assert "encode(sha256(convert_to(key, 'UTF8')), 'hex')" in body
    assert "left(key, 8)" in body
    assert body.index("UPDATE") < body.index("drop_column(TABLE, 'key')")
    assert hash_key("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_the_migration_creates_what_the_models_declare() -> None:
    module = _load()
    source = MIGRATION.read_text(encoding="utf-8")
    assert ApiKey.__tablename__ == module.TABLE
    assert ApiKeyPermission.__tablename__ == module.PERMISSION_TABLE
    assert SecuritySettings.__tablename__ == module.SETTINGS_TABLE
    for column in (*ApiKey.__table__.columns, *ApiKeyPermission.__table__.columns):
        assert f'"{column.name}"' in source, column.name
    for name, _column in module.SETTINGS_COLUMNS:
        assert name in SecuritySettings.__table__.columns
    assert {constraint.name for constraint in ApiKey.__table__.constraints} >= {module.NAME_UNIQUE}
    for foreign_key in ApiKeyPermission.__table__.foreign_keys:
        assert foreign_key.ondelete == "CASCADE"
    assert source.count('ondelete="CASCADE"') == 2


def test_keys_expired_before_the_upgrade_are_not_reported() -> None:
    body = _function_source("_upgrade_api_key")
    assert "SET expiry_notified_at = expires_at WHERE expires_at <= now() AND expiry_notified_at IS NULL" in body


def test_tables_and_columns_made_by_create_all_are_reused() -> None:
    assert "if PERMISSION_TABLE in _tables()" in _function_source("_create_permission_table")
    assert "if name not in columns" in _function_source("_add_policy_columns")
    assert "if name not in columns" in _function_source("_upgrade_api_key")


def test_admin_gets_the_new_permissions_and_startup_registers_them_too() -> None:
    module = _load()
    ids = {permission_id for permission_id, _name, _description in module.PERMISSIONS}
    assert ids == {"CONFIG_API_KEY_ACCESS", "CONFIG_API_KEY_CREATE", "CONFIG_API_KEY_UPDATE", "CONFIG_API_KEY_DELETE", "MY_API_KEYS_MANAGE"}
    source = MIGRATION.read_text(encoding="utf-8")
    assert "role.name = 'Admin'" in source
    assert "ON CONFLICT (id) DO NOTHING" in source
    startup = Path(config_api.__file__).read_text(encoding="utf-8")
    for permission_id, name, description in module.PERMISSIONS:
        assert f'Permission.add("{permission_id}", "{name}", "{description}")' in startup


def test_the_downgrade_says_it_deletes_the_keys() -> None:
    assert "DELETE FROM {TABLE}" in _function_source("downgrade")
    assert "cannot recover a key from its hash" in (_load().__doc__ or "")
