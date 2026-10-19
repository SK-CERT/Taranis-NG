"""The notifications migration matches the models and can run on a database that has its tables.

``1f928d40433c`` creates the channel and outbox tables and the notification permissions. A core
started with the new models creates the tables itself (``db.create_all()``), so the migration
checks before creating; and what it creates must be what the models declare, or such a database
ends up different from a migrated one. Like the other migration tests, these need no database.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

from api import config as config_api
from model.notification import NotificationChannel, NotificationEvent, NotificationOutbox

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
VERSIONS = CORE_ROOT / "migrations" / "versions"
MIGRATION = VERSIONS / "1f928d40433c_notifications.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("notifications_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_extends_the_passkey_aaguid_head() -> None:
    module = _load()
    assert module.revision == "1f928d40433c"
    assert module.down_revision == "2c2e10005e77"
    revises = re.compile(r'^down_revision = "2c2e10005e77"$', re.MULTILINE)
    children = [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_tables_made_by_create_all_are_reused() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    create_tables = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_create_tables")
    body = ast.unparse(create_tables)
    assert "if CHANNEL_TABLE not in tables" in body
    assert "if OUTBOX_TABLE not in tables" in body
    assert "if EVENT_TABLE not in tables" in body
    assert "if OUTBOX_INDEX not in indexes" in body


def test_the_migration_creates_what_the_models_declare() -> None:
    module = _load()
    assert NotificationChannel.__tablename__ == module.CHANNEL_TABLE
    assert NotificationOutbox.__tablename__ == module.OUTBOX_TABLE
    assert NotificationEvent.__tablename__ == module.EVENT_TABLE
    assert module.OUTBOX_INDEX in {index.name for index in NotificationOutbox.__table__.indexes}
    source = MIGRATION.read_text(encoding="utf-8")
    for column in NotificationOutbox.__table__.columns:
        assert f'"{column.name}"' in source, column.name
    for model in (NotificationChannel, NotificationEvent):
        for column in model.__table__.columns:
            assert f'"{column.name}"' in source, column.name
    user_fk = next(iter(NotificationOutbox.__table__.c.user_id.foreign_keys))
    assert user_fk.ondelete == "SET NULL"
    assert 'ondelete="SET NULL"' in source


def test_admin_gets_the_new_permissions_and_startup_registers_them_too() -> None:
    module = _load()
    ids = {permission_id for permission_id, _name, _description in module.PERMISSIONS}
    assert ids == {"CONFIG_NOTIFICATIONS_ACCESS", "CONFIG_NOTIFICATIONS_UPDATE"}
    source = MIGRATION.read_text(encoding="utf-8")
    assert "role.name = 'Admin'" in source
    assert "ON CONFLICT (id) DO NOTHING" in source
    startup = Path(config_api.__file__).read_text(encoding="utf-8")
    for permission_id in ids:
        assert f'Permission.add("{permission_id}"' in startup
