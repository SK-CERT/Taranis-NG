"""Static regression tests for the authentication-provider migrations.

These checks intentionally need neither a configured application nor a database.
They protect the migration properties that are easiest to accidentally lose while
rebasing the feature onto a newer Alembic head.
"""

import ast
from pathlib import Path

CORE_ROOT = Path(__file__).parents[1]
MIGRATIONS = CORE_ROOT / "migrations" / "versions"
SCHEMA_MIGRATION = MIGRATIONS / "e3f9d1a7c8b5_auth_providers.py"
DATA_MIGRATION = MIGRATIONS / "4c8e1f7a2b90_seed_auth_provider_defaults.py"
AUTH_PROVIDER_MODEL = CORE_ROOT / "model" / "auth_provider.py"


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment(module: ast.Module, name: str) -> object:
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    message = f"{name} is not assigned"
    raise AssertionError(message)


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    message = f"{name} is not defined"
    raise AssertionError(message)


def test_auth_migrations_extend_the_current_head_in_two_steps() -> None:
    schema = _module(SCHEMA_MIGRATION)
    data = _module(DATA_MIGRATION)

    assert _assignment(schema, "revision") == "e3f9d1a7c8b5"
    assert _assignment(schema, "down_revision") == "6f3a8d9c2e11"
    assert _assignment(data, "revision") == "4c8e1f7a2b90"
    assert _assignment(data, "down_revision") == "e3f9d1a7c8b5"

    revisions: set[str] = set()
    referenced_revisions: set[str] = set()
    for path in MIGRATIONS.glob("*.py"):
        migration = _module(path)
        try:
            revisions.add(_assignment(migration, "revision"))
            parent = _assignment(migration, "down_revision")
        except AssertionError:
            continue
        if isinstance(parent, str):
            referenced_revisions.add(parent)
        elif parent:
            referenced_revisions.update(parent)

    assert revisions - referenced_revisions == {"4c8e1f7a2b90"}


def test_schema_upgrade_is_deterministic_and_schema_only() -> None:
    module = _module(SCHEMA_MIGRATION)
    upgrade = _function(module, "upgrade")
    imported_modules = {alias.name for node in module.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    called_attributes = {node.func.attr for node in ast.walk(upgrade) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    source = ast.get_source_segment(SCHEMA_MIGRATION.read_text(encoding="utf-8"), upgrade) or ""

    assert not imported_modules.intersection({"os", "pathlib", "re"})
    assert not called_attributes.intersection({"bulk_insert", "execute", "get_bind"})
    assert "TARANIS_NG_" not in source
    assert "LDAP_" not in source


def test_migrations_use_frozen_local_objects_not_application_models() -> None:
    for path in (SCHEMA_MIGRATION, DATA_MIGRATION):
        module = _module(path)
        application_imports = [
            node
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module and (node.module == "model" or node.module.startswith("model."))
        ]

        assert application_imports == []
        assert not any(isinstance(node, ast.ClassDef) for node in module.body)

    data_source = DATA_MIGRATION.read_text(encoding="utf-8")
    assert "sa.table(" in data_source
    assert "db.Model" not in data_source


def test_data_revision_owns_permissions_local_provider_and_generation_one_settings() -> None:
    module = _module(DATA_MIGRATION)
    permissions = _assignment(module, "PERMISSIONS")
    local_provider = _assignment(module, "LOCAL_PROVIDER")
    security_settings = _assignment(module, "SECURITY_SETTINGS")

    assert {permission["id"] for permission in permissions} == {
        "CONFIG_AUTH_PROVIDER_ACCESS",
        "CONFIG_AUTH_PROVIDER_CREATE",
        "CONFIG_AUTH_PROVIDER_UPDATE",
        "CONFIG_AUTH_PROVIDER_DELETE",
    }
    assert len(permissions) == 4
    assert local_provider == {
        "name": "Local accounts",
        "slug": "local",
        "kind": "local",
        "enabled": True,
        "organization_id": None,
        "provisioning_mode": "manual",
        "allowed_domains": "",
        "require_mfa": False,
        "config": {},
        "secret": None,
        "updated_by": None,
    }
    assert security_settings == {
        "id": 1,
        "passkey_enabled": False,
        "passkey_second_factor": True,
        "require_mfa": False,
        "auth_generation": 1,
        "rp_id": None,
        "rp_name": "Taranis NG",
        "origins": None,
        "updated_by": None,
    }


def test_auth_generation_is_revision_frozen_and_downgrade_protected() -> None:
    schema_source = SCHEMA_MIGRATION.read_text(encoding="utf-8")
    data_source = DATA_MIGRATION.read_text(encoding="utf-8")

    assert 'sa.Column("auth_generation", sa.INTEGER(), nullable=False, server_default=sa.text("1"))' in schema_source
    assert 'sa.column("auth_generation", sa.Integer())' in data_source
    assert "security_settings_row != SECURITY_SETTINGS" in data_source
    assert 'sa.delete(security_settings).where(security_settings.c.id == SECURITY_SETTINGS["id"])' in data_source


def test_schema_downgrade_refuses_loss_instead_of_inventing_passwords() -> None:
    module = _module(SCHEMA_MIGRATION)
    downgrade = _function(module, "downgrade")
    source = ast.get_source_segment(SCHEMA_MIGRATION.read_text(encoding="utf-8"), downgrade) or ""

    assert "RuntimeError" in source
    assert "password = ''" not in source
    assert "UPDATE" not in source.upper()
    assert source.index("RuntimeError") < source.index('alter_column("user", "password"')


def test_identity_model_declares_the_database_partial_unique_index() -> None:
    module = _module(AUTH_PROVIDER_MODEL)
    identity = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "UserAuthIdentity")
    source = ast.get_source_segment(AUTH_PROVIDER_MODEL.read_text(encoding="utf-8"), identity) or ""

    assert '"uq_identity_provider_external"' in source
    assert '"auth_provider_id"' in source
    assert '"external_id"' in source
    assert "unique=True" in source
    assert 'postgresql_where=db.text("external_id IS NOT NULL")' in source


def test_new_providers_default_disabled_except_for_the_local_seed() -> None:
    schema_source = SCHEMA_MIGRATION.read_text(encoding="utf-8")
    model_source = AUTH_PROVIDER_MODEL.read_text(encoding="utf-8")

    assert 'sa.Column("enabled", sa.BOOLEAN(), nullable=False, server_default=sa.text("false"))' in schema_source
    assert 'enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="false")' in model_source
    assert "enabled: bool = False" in model_source
    assert _assignment(_module(DATA_MIGRATION), "LOCAL_PROVIDER")["enabled"] is True
