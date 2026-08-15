"""Repair the distribution bundle skipped by migration 1c4eed243364.

This is a narrowly scoped compatibility repair. It deliberately refuses to
merge a partially present bundle, because title-based reconciliation could
overwrite administrator-owned configuration.
"""

from importlib import util
from pathlib import Path
from types import ModuleType

from sqlalchemy import bindparam, orm, text
from sqlalchemy.engine import Connection, Engine

PRODUCT_PATHS = {
    "Weekly Bulletin": "/app/templates/weekly.html",
    "OSINT Weekly Report": "/app/templates/template_osint.html",
    "Disinformation": "/app/templates/template_disinfo.html",
    "Offensive Content": "/app/templates/template_content.html",
}

REPORT_TYPES = {
    "OSINT Report - Summary",
    "OSINT Report - Ransomware",
    "OSINT Report - Sectors",
    "OSINT Report - Threats",
    "OSINT Report - Cyber Event",
    "Disinformation from public source",
    "Offensive content",
    "News by Sector",
}

ATTRIBUTES = {
    "NIS Sector",
    "Attachment",
    "Disinfo type",
    "Boolean",
    "Threat level",
    "Trend",
    "Source Reliability",
    "Information Credibility",
}

NAME_QUERIES = {
    ("product_type", "title"): text("SELECT title FROM product_type WHERE title IN :expected"),
    ("report_item_type", "title"): text("SELECT title FROM report_item_type WHERE title IN :expected"),
    ("attribute", "name"): text("SELECT name FROM attribute WHERE name IN :expected"),
}
EXPECTED_GROUP_COUNT = 24
EXPECTED_GROUP_ITEM_COUNT = 93


def _matching_names(connection: Connection, table: str, column: str, expected: set[str]) -> set[str]:
    """Return expected names already present in one known table and column."""
    statement = NAME_QUERIES[(table, column)].bindparams(bindparam("expected", expanding=True))
    return set(connection.execute(statement, {"expected": tuple(expected)}).scalars())


def _load_legacy_migration() -> ModuleType:
    """Load the migration containing the distribution bundle definition."""
    migration_path = Path(__file__).with_name("versions") / "1c4eed243364_new_reports.py"
    spec = util.spec_from_file_location("distribution_bundle_1c4eed243364", migration_path)
    if spec is None or spec.loader is None:
        message = f"Could not load distribution migration: {migration_path}"
        raise RuntimeError(message)

    migration = util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _validate_bundle(connection: Connection) -> None:
    """Validate the objects and links created by the compatibility repair."""
    product_rows = connection.execute(
        text(
            """
            SELECT pt.title, presenter.type, parameter.key, parameter_value.value
              FROM product_type AS pt
              JOIN presenter ON presenter.id = pt.presenter_id
              JOIN product_type_parameter_value AS link ON link.product_type_id = pt.id
              JOIN parameter_value ON parameter_value.id = link.parameter_value_id
              JOIN parameter ON parameter.id = parameter_value.parameter_id
             WHERE pt.title IN :titles
            """,
        ).bindparams(bindparam("titles", expanding=True)),
        {"titles": tuple(PRODUCT_PATHS)},
    ).all()

    actual_products = {
        title: path
        for title, presenter_type, parameter_key, path in product_rows
        if presenter_type == "HTML_PRESENTER" and parameter_key == "HTML_TEMPLATE_PATH"
    }
    actual_reports = _matching_names(connection, "report_item_type", "title", REPORT_TYPES)
    actual_attributes = _matching_names(connection, "attribute", "name", ATTRIBUTES)

    group_count = connection.execute(
        text(
            """
            SELECT count(*)
              FROM attribute_group AS ag
              JOIN report_item_type AS rit ON rit.id = ag.report_item_type_id
             WHERE rit.title IN :titles
            """,
        ).bindparams(bindparam("titles", expanding=True)),
        {"titles": tuple(REPORT_TYPES)},
    ).scalar_one()
    item_count = connection.execute(
        text(
            """
            SELECT count(*)
              FROM attribute_group_item AS agi
              JOIN attribute_group AS ag ON ag.id = agi.attribute_group_id
              JOIN report_item_type AS rit ON rit.id = ag.report_item_type_id
             WHERE rit.title IN :titles
            """,
        ).bindparams(bindparam("titles", expanding=True)),
        {"titles": tuple(REPORT_TYPES)},
    ).scalar_one()

    if (
        actual_products != PRODUCT_PATHS
        or actual_reports != REPORT_TYPES
        or actual_attributes != ATTRIBUTES
        or group_count != EXPECTED_GROUP_COUNT
        or item_count != EXPECTED_GROUP_ITEM_COUNT
    ):
        message = "Distribution bundle validation failed; all repair changes were rolled back"
        raise RuntimeError(message)


def _presenter_binding(connection: Connection, presenter_node_url: str | None) -> tuple[str, int]:
    """Select one HTML presenter and its template parameter deterministically."""
    statement = """
        SELECT presenter.id, parameter.id
          FROM presenter
          JOIN presenters_node ON presenters_node.id = presenter.node_id
          JOIN presenter_parameter ON presenter_parameter.presenter_id = presenter.id
          JOIN parameter ON parameter.id = presenter_parameter.parameter_id
         WHERE presenter.type = 'HTML_PRESENTER'
           AND parameter.key = 'HTML_TEMPLATE_PATH'
    """
    parameters = {}
    if presenter_node_url is not None:
        statement += " AND rtrim(presenters_node.api_url, '/') = rtrim(:node_url, '/')"
        parameters["node_url"] = presenter_node_url
    statement += " ORDER BY presenters_node.api_url, presenter.id, parameter.id"

    bindings = connection.execute(text(statement), parameters).all()
    if not bindings or (presenter_node_url is None and len(bindings) != 1):
        target = presenter_node_url or "the configured presenter nodes"
        message = f"Could not select one HTML presenter/template binding for {target}; found {len(bindings)}"
        raise RuntimeError(message)
    return bindings[0][0], bindings[0][1]


def repair_distribution_bundle(
    engine: Engine,
    presenter_node_url: str | None = None,
    *,
    preserve_partial: bool = False,
) -> None:
    """Install the wholly absent legacy bundle, or report that it is complete."""
    with engine.begin() as connection:
        present_products = _matching_names(connection, "product_type", "title", set(PRODUCT_PATHS))
        present_reports = _matching_names(connection, "report_item_type", "title", REPORT_TYPES)
        present_attributes = _matching_names(connection, "attribute", "name", ATTRIBUTES)

        if present_products == set(PRODUCT_PATHS) and present_reports == REPORT_TYPES and present_attributes == ATTRIBUTES:
            print("Distribution bundle is already complete; no changes made.", flush=True)  # noqa: T201
            return

        if present_products or present_reports or present_attributes:
            if preserve_partial:
                print("Existing partial or customized distribution configuration preserved; no changes made.", flush=True)  # noqa: T201
                return
            message = "The distribution bundle is partially present. The automatic repair will not merge or overwrite configuration."
            raise RuntimeError(message)

        presenter_id, parameter_html_id = _presenter_binding(connection, presenter_node_url)
        migration = _load_legacy_migration()
        with orm.Session(bind=connection) as session:
            migration.install_distribution_bundle(session, presenter_id, parameter_html_id)
        _validate_bundle(connection)

    print("Distribution bundle repaired and validated.", flush=True)  # noqa: T201
