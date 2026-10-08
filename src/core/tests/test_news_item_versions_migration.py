"""Static regression tests for the news item versions migration.

``e7b2c4a91d53`` adds the version columns to news_item_data and creates the history table.
Like the other migration tests here, these need neither an application nor a database: they
protect the properties most easily lost while rebasing onto a newer Alembic head, and the
agreement between the migration and the model that `create_all()` builds from.
"""

import ast
from pathlib import Path

import sqlalchemy as sa
from model import tag_cloud as tag_cloud_module
from model.news_item import NewsItem, NewsItemAggregate, NewsItemAggregateSearchIndex, NewsItemData, NewsItemDataVersion
from model.tag_cloud import TagCloud

CORE_ROOT = Path(__file__).parents[1]
MIGRATION = CORE_ROOT / "migrations" / "versions" / "e7b2c4a91d53_news_item_versions.py"


def _module() -> ast.Module:
    return ast.parse(MIGRATION.read_text(encoding="utf-8"), filename=str(MIGRATION))


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


def _calls(function: ast.FunctionDef) -> set[str]:
    names = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_the_migration_extends_the_attribute_extraction_head() -> None:
    module = _module()
    assert _assignment(module, "revision") == "e7b2c4a91d53"
    assert _assignment(module, "down_revision") == "d4f1c8a70b62"


def test_the_history_table_survives_a_premature_create_all() -> None:
    """A core started before the migration has already created the table, empty."""
    upgrade = _function(_module(), "upgrade")
    assert "_drop_empty_premature_table" in _calls(upgrade)
    assert "create_table" in _calls(upgrade)


def test_the_columns_are_only_added_when_missing() -> None:
    upgrade = _function(_module(), "upgrade")
    assert "get_columns" in _calls(upgrade)
    assert "get_indexes" in _calls(upgrade)


def test_history_is_deleted_with_its_item_in_the_migration_and_the_model() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'ondelete="CASCADE"' in source
    assert [key.ondelete for key in NewsItemDataVersion.__table__.foreign_keys] == ["CASCADE"]


def test_the_model_declares_the_indexes_the_migration_creates() -> None:
    module = _module()
    assert _assignment(module, "VERSION_TABLE") == NewsItemDataVersion.__table__.name
    assert _assignment(module, "VERSION_KEY_INDEX") in {index.name for index in NewsItemData.__table__.indexes}
    source = MIGRATION.read_text(encoding="utf-8")
    for index in NewsItemDataVersion.__table__.indexes:
        assert index.name in source, f"{index.name} is declared on the model but not created by the migration"


def test_the_version_key_index_is_partial() -> None:
    (index,) = [index for index in NewsItemData.__table__.indexes if index.name == "ix_news_item_data_version_key"]
    assert "version_key IS NOT NULL" in str(index.dialect_options["postgresql"]["where"])


def _source(function: ast.FunctionDef) -> str:
    return ast.get_source_segment(MIGRATION.read_text(encoding="utf-8"), function)


# --- lookup indexes, tag cloud key and retention setting ---------------------------------


def test_the_upgrade_adds_the_indexes_the_tag_cloud_key_and_the_setting() -> None:
    assert {"_create_lookup_indexes", "_tag_cloud_one_row_per_word", "_add_retention_setting"} <= _calls(_function(_module(), "upgrade"))


def test_the_models_declare_the_lookup_indexes_the_migration_creates() -> None:
    tables = {model.__table__.name: model.__table__ for model in (NewsItemData, NewsItem, NewsItemAggregate, NewsItemAggregateSearchIndex)}
    for name, table, column in _assignment(_module(), "LOOKUP_INDEXES"):
        (index,) = [index for index in tables[table].indexes if index.name == name]
        assert [indexed.name for indexed in index.columns] == [column]


def test_a_column_already_indexed_is_left_alone() -> None:
    assert "get_indexes" in _calls(_function(_module(), "_create_lookup_indexes"))


def test_tag_cloud_duplicates_are_merged_before_the_key_is_added() -> None:
    function = _function(_module(), "_tag_cloud_one_row_per_word")
    source = _source(function)
    assert "get_unique_constraints" in _calls(function)
    assert source.index("sum(word_quantity)") < source.index("DELETE FROM tag_cloud USING") < source.index("create_unique_constraint")


def test_the_model_declares_the_tag_cloud_key_the_migration_adds() -> None:
    module = _module()
    (key,) = [constraint for constraint in TagCloud.__table__.constraints if isinstance(constraint, sa.UniqueConstraint)]
    assert key.name == _assignment(module, "TAG_CLOUD_KEY")
    assert [column.name for column in key.columns] == ["collected", "word"]
    for column in _assignment(module, "TAG_CLOUD_COLUMNS"):
        assert TagCloud.__table__.c[column].nullable is False


def test_the_retention_setting_is_seeded_as_seven_days_and_removed_on_downgrade() -> None:
    module = _module()
    assert _assignment(module, "RETENTION_SETTING") == tag_cloud_module.RETENTION_SETTING
    source = _source(_function(module, "_add_retention_setting"))
    assert '"type": "I"' in source
    assert f'"value": "{tag_cloud_module.DEFAULT_RETENTION_DAYS}"' in source
    assert f'"default_val": "{tag_cloud_module.DEFAULT_RETENTION_DAYS}"' in source
    assert "DELETE FROM settings" in _source(_function(module, "downgrade"))


def test_history_entries_repeating_a_revision_are_dropped() -> None:
    module = _module()
    assert "_drop_repeated_revisions" in _calls(_function(module, "upgrade"))
    source = _source(_function(module, "_drop_repeated_revisions"))
    # Copies of the revision the item still holds, and all but the last copy of any other.
    assert "copy.version = item.version" in source
    assert "later.version = copy.version AND later.id > copy.id" in source
