"""Regression tests for the link references migration.

``a3c9f1d27b64`` turns positional citations ("[2]") into stable key tokens ("[#k3f9a2]") and
gives products their own links. Like the other migration tests here, these need neither an
application nor a database: the conversion functions are pure and are loaded straight from the
migration file, and the rest is checked on its source.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from managers.link_references import LINK_KEY_RE, LINK_TOKEN_RE
from model.product import Product
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
MIGRATION = CORE_ROOT / "migrations" / "versions" / "a3c9f1d27b64_link_references.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("link_references_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function(name: str) -> ast.FunctionDef:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"), filename=str(MIGRATION))
    for node in tree.body:
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


def test_the_migration_extends_the_news_item_versions_head() -> None:
    module = _load()
    assert module.revision == "a3c9f1d27b64"
    assert module.down_revision == "e7b2c4a91d53"


def _source(name: str) -> str:
    return ast.get_source_segment(MIGRATION.read_text(encoding="utf-8"), _function(name))


def test_the_product_links_column_survives_a_premature_create_all() -> None:
    """A core started before the migration has already created the column with the table."""
    assert "information_schema.columns" in _source("_add_product_links")
    assert "get_columns" in _calls(_function("downgrade"))


def test_the_migration_column_matches_the_model() -> None:
    column = Product.__table__.c["links"]
    assert column.nullable is False
    assert "'[]'" in str(column.server_default.arg)
    assert "server_default=sa.text(\"'[]'\")" in _source("_add_product_links")


def test_product_links_are_jsonb_so_products_can_be_selected_distinct() -> None:
    """Postgres has no equality for json, and product queries use SELECT DISTINCT."""
    assert isinstance(Product.__table__.c["links"].type, JSONB)
    source = _source("_add_product_links")
    assert "JSONB()" in source
    # A column an earlier draft of the revision created as json is converted.
    assert "TYPE jsonb USING links::jsonb" in source


def test_generated_keys_and_tokens_are_what_core_understands() -> None:
    module = _load()
    taken: set[str] = set()
    key = module.new_key(taken)
    assert key in taken
    assert LINK_KEY_RE.fullmatch(key)
    assert module.KEY_RE.pattern == LINK_KEY_RE.pattern
    assert LINK_TOKEN_RE.search(f"text [#{key}]")


def test_positional_citations_become_tokens_of_the_report_links() -> None:
    module = _load()
    keys = ["aaaaaa", "bbbbbb"]

    assert module.tokens_from_positions("See [2], then [1] and [2].", keys) == "See [#bbbbbb], then [#aaaaaa] and [#bbbbbb]."
    # Out of range, zero and non-citations are left as they are.
    assert module.tokens_from_positions("Item [3], [0], [x], [12a]", keys) == "Item [3], [0], [x], [12a]"
    assert module.tokens_from_positions("No links [1]", []) == "No links [1]"
    assert module.tokens_from_positions(None, keys) is None


def test_the_downgrade_turns_tokens_back_into_positions() -> None:
    module = _load()
    keys = ["aaaaaa", "bbbbbb"]
    text = "See [2], then [1]."

    converted = module.tokens_from_positions(text, keys)
    assert module.positions_from_tokens(converted, keys) == text
    assert module.positions_from_tokens("Product link [#prod01]", keys) == "Product link [#prod01]"


def test_product_descriptions_use_the_old_product_wide_numbering() -> None:
    """Vulnerability reports only, in product order, each link value listed once."""
    module = _load()
    reports = [
        ("Vulnerability Report", [("vul1aa", "https://a.example"), ("vul1bb", "https://b.example")]),
        ("OSINT Report", [("osin01", "https://o.example")]),
        ("Vulnerability Report - Intro", [("intr01", "https://b.example"), ("intr02", "https://c.example")]),
        (None, [("none01", "https://n.example")]),
    ]

    keys = module.legacy_product_keys(reports)

    assert keys == ["vul1aa", "vul1bb", "intr02"]
    assert module.tokens_from_positions("Sources [1], [3] and [4].", keys) == "Sources [#vul1aa], [#intr02] and [4]."


def test_the_upgrade_converts_reports_before_product_descriptions() -> None:
    upgrade = _function("upgrade")
    source = ast.get_source_segment(MIGRATION.read_text(encoding="utf-8"), upgrade)
    assert {"autocommit_block", "_add_product_links", "_switch_links_items", "_key_report_links"} <= _calls(upgrade)
    assert source.index("_key_report_links") < source.index("_rewrite_report_text") < source.index("_rewrite_product_descriptions")
