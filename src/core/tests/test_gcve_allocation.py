"""GCVE identifiers: allocated with a CVD Report from its organization's GNA, never given again, guarding what is published.

The models are built in memory (no database); the session is stubbed. Every model module is
imported first so the mappers can be configured.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model import organization_gna  # noqa: E402 - after every mapper is registered
from model.gcve_assignment import PUBLISHED, REJECTED, RESERVED, GcveAssignment  # noqa: E402
from model.organization_gna import CvdNotConfiguredError, GnaSettingsError, OrganizationGna  # noqa: E402
from model.product import CvdProductError, GcvePublicationError, GcveRecordsHeldError, Product  # noqa: E402
from model.product_preset import ProductPreset, ProductPresetLockedError  # noqa: E402
from model.report_item import ReportItem  # noqa: E402
from model.report_item_type import ReportItemType, ReportTypeDisabledError, ReportTypeLockedError  # noqa: E402
from model.setting import Setting  # noqa: E402
from model.state import StateDefinition  # noqa: E402

from shared import gcve  # noqa: E402

USER = SimpleNamespace(id=3, name="Example Analyst")
NEW_REPORT = {
    "id": None,
    "uuid": None,
    "state_id": None,
    "report_item_type_id": 9,
    "title": "Login bypass",
    "title_prefix": "",
    "attributes": [],
}


def test_identifiers_are_padded_to_four_digits_and_grow_beyond() -> None:
    assert gcve.gcve_id(65535, 2026, 1) == "GCVE-65535-2026-0001"
    assert gcve.gcve_id(65535, 2026, 9999) == "GCVE-65535-2026-9999"
    assert gcve.gcve_id(65535, 2026, 10000) == "GCVE-65535-2026-10000"
    assert gcve.GCVE_ID_PATTERN.match("GCVE-1-2026-10000")
    assert not gcve.GCVE_ID_PATTERN.match("GCVE-1-2026-1")


class _Session:
    """Records what the allocation runs and adds."""

    def __init__(self, number: int) -> None:
        self.number = number
        self.statements: list[tuple[str, dict]] = []
        self.added: list[object] = []

    def execute(self, statement: object, parameters: dict) -> SimpleNamespace:
        self.statements.append((str(statement), parameters))
        return SimpleNamespace(scalar_one=lambda: self.number)

    def add(self, item: object) -> None:
        self.added.append(item)


@pytest.mark.parametrize(("number", "expected"), [(1, "GCVE-65535-2026-0001"), (10000, "GCVE-65535-2026-10000")])
def test_the_next_number_of_the_year_is_taken_in_one_upsert(monkeypatch: pytest.MonkeyPatch, number: int, expected: str) -> None:
    session = _Session(number)
    monkeypatch.setattr(db, "session", session)
    report = ReportItem(None, None, "Login bypass", "", 9, None, [], [], [])

    assignment = GcveAssignment.allocate(report, 65535, datetime(2026, 11, 8, tzinfo=UTC))

    ((statement, parameters),) = session.statements
    assert "ON CONFLICT (gna_id, year) DO UPDATE SET last_number = gcve_counter.last_number + 1" in statement
    assert "RETURNING last_number" in statement
    assert parameters == {"gna_id": 65535, "year": 2026}
    assert (assignment.gcve_id, assignment.state, assignment.report_item) == (expected, RESERVED, report)
    assert session.added == [assignment]


def _organization(organization_id: int, gna_id: int | None = 65535, cna: bool = False) -> dict:
    return {
        "id": organization_id,
        "name": f"CERT {organization_id}",
        "gna_id": gna_id,
        "short_name": "TEST-GNA" if gna_id else None,
        "gna_configured": gna_id is not None,
        "cna_configured": cna,
    }


@pytest.fixture
def created(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Reports created without a database, with the report type and the author's organizations the test sets."""
    state = SimpleNamespace(stored=[], allocated=[], report_type=None, organizations=[_organization(1)])
    monkeypatch.setattr(organization_gna, "cvd_organizations", lambda _user: state.organizations)

    def gna_of(_cls: type, organization_id: int) -> SimpleNamespace | None:
        found = next((target for target in state.organizations if target["id"] == organization_id), None)
        return SimpleNamespace(gna_id=found["gna_id"]) if found and found["gna_id"] else None

    monkeypatch.setattr(OrganizationGna, "for_organization", classmethod(gna_of))
    monkeypatch.setattr(ReportItemType, "allowed_with_acl", classmethod(lambda _cls, *_args, **_kwargs: True))
    monkeypatch.setattr(ReportItemType, "find", classmethod(lambda _cls, _id: state.report_type))
    monkeypatch.setattr(StateDefinition, "get_initial_state", classmethod(lambda _cls, *_args: None))
    monkeypatch.setattr(Setting, "get_setting", classmethod(lambda _cls, *_args: "cs"))
    monkeypatch.setattr(ReportItem, "update_cpes", lambda _self: None)
    monkeypatch.setattr(db.session, "add", state.stored.append)
    monkeypatch.setattr(db.session, "commit", lambda: None)

    def allocate(_cls: type, report: ReportItem, gna_id: int) -> None:
        state.allocated.append((report, gna_id))

    monkeypatch.setattr(GcveAssignment, "allocate", classmethod(allocate))
    return state


def _type(**fields: object) -> SimpleNamespace:
    return SimpleNamespace(**{"title": "CVD Report", "enabled": True, "system_key": gcve.CVD_TYPE_KEY, **fields})


def test_a_cvd_report_gets_its_identifier_as_it_is_created_and_is_english(created: SimpleNamespace) -> None:
    created.report_type = _type()

    report, status = ReportItem.add_report_item(NEW_REPORT, USER)

    assert status == HTTPStatus.OK
    assert created.allocated == [(report, 65535)]
    assert report.language == "en"
    # Its author's organization publishes it.
    assert report.organization_id == 1


def test_a_member_of_several_organizations_picks_one_of_them(created: SimpleNamespace) -> None:
    created.report_type = _type()
    created.organizations = [_organization(1), _organization(2, gna_id=4242)]

    with pytest.raises(ValueError, match="Pick the organization"):
        ReportItem.add_report_item(NEW_REPORT, USER)
    with pytest.raises(ValueError, match="one of your organizations"):
        ReportItem.add_report_item({**NEW_REPORT, "organization_id": 7}, USER)
    assert created.stored == []

    report, _status = ReportItem.add_report_item({**NEW_REPORT, "organization_id": "2"}, USER)

    assert report.organization_id == 2
    assert created.allocated == [(report, 4242)]


def test_other_reports_get_no_identifier(created: SimpleNamespace) -> None:
    created.report_type = _type(title="Vulnerability Report", system_key=None)

    report, _status = ReportItem.add_report_item({**NEW_REPORT, "organization_id": 1}, USER)

    assert created.allocated == []
    assert report.language == "cs"
    assert report.organization_id is None


def test_no_cvd_report_before_it_can_be_published_anywhere(created: SimpleNamespace) -> None:
    created.report_type = _type()
    created.organizations = []

    with pytest.raises(CvdNotConfiguredError, match=r"none of your organizations has a GNA number or a CVE Services account"):
        ReportItem.add_report_item(NEW_REPORT, USER)
    assert created.stored == []


def test_with_only_the_cna_account_a_cvd_report_waits_for_its_gcve_identifier(created: SimpleNamespace) -> None:
    created.report_type = _type()
    created.organizations = [_organization(1, gna_id=None, cna=True)]

    report, status = ReportItem.add_report_item(NEW_REPORT, USER)

    assert status == HTTPStatus.OK
    assert created.allocated == []
    assert report.language == "en"


def test_no_report_of_a_switched_off_type(created: SimpleNamespace) -> None:
    created.report_type = _type(enabled=False)

    with pytest.raises(ReportTypeDisabledError, match="switched off"):
        ReportItem.add_report_item(NEW_REPORT, USER)
    assert created.allocated == []


def _with_assignment(state: str) -> SimpleNamespace:
    assignment = SimpleNamespace(gcve_id="GCVE-65535-2026-0007", state=state, report_item="report")
    assignment.published = state == PUBLISHED
    assignment.reject = lambda: (setattr(assignment, "state", REJECTED), setattr(assignment, "report_item", None))
    return assignment


def test_a_published_record_is_never_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    report = SimpleNamespace(gcve_assignment=_with_assignment(PUBLISHED))
    monkeypatch.setattr(db.session, "get", lambda _cls, _id: report)
    deleted = []
    monkeypatch.setattr(db.session, "delete", deleted.append)

    message, status = ReportItem.delete_report_item(7)

    assert status == HTTPStatus.CONFLICT
    assert "deprecation" in message
    assert deleted == []


def test_an_unpublished_identifier_is_kept_rejected_when_its_report_goes(monkeypatch: pytest.MonkeyPatch) -> None:
    assignment = _with_assignment(RESERVED)
    report = SimpleNamespace(gcve_assignment=assignment)
    monkeypatch.setattr(db.session, "get", lambda _cls, _id: report)
    deleted = []
    monkeypatch.setattr(db.session, "delete", deleted.append)
    monkeypatch.setattr(db.session, "commit", lambda: None)

    assert ReportItem.delete_report_item(7) == ("success", HTTPStatus.OK)
    assert (assignment.state, assignment.report_item) == (REJECTED, None)
    assert deleted == [report]


def test_deleting_a_missing_report_is_a_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db.session, "get", lambda _cls, _id: None)

    assert ReportItem.delete_report_item(7) == ("Report item not found", HTTPStatus.NOT_FOUND)


# -- the shipped type and preset are locked --------------------------------------------------


def test_a_shipped_report_type_only_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    shipped = ReportItemType(None, "CVD Report", "Shipped", [])
    shipped.system_key = gcve.CVD_TYPE_KEY
    monkeypatch.setattr(db.session, "get", lambda _cls, _id: shipped)
    monkeypatch.setattr(db.session, "commit", lambda: None)

    ReportItemType.update(4, {"title": "Renamed", "description": "Changed", "attribute_groups": [], "enabled": False})

    assert (shipped.title, shipped.description, shipped.enabled) == ("CVD Report", "Shipped", False)
    with pytest.raises(ReportTypeLockedError, match="only be switched on or off"):
        ReportItemType.delete_report_item_type(4)


def test_a_shipped_product_preset_only_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    shipped = ProductPreset("GCVE Advisory", "Shipped", public_web_enabled=True)
    shipped.system_key = gcve.GCVE_PRESET_KEY
    monkeypatch.setattr(ProductPreset, "find", classmethod(lambda _cls, _id: shipped))
    monkeypatch.setattr(db.session, "commit", lambda: None)

    ProductPreset.update(3, {"name": "Renamed", "public_web_enabled": False, "enabled": False}, "admin")

    assert (shipped.name, shipped.public_web_enabled, shipped.enabled) == ("GCVE Advisory", True, False)
    with pytest.raises(ProductPresetLockedError):
        ProductPreset.delete(3)


def test_the_gcve_preset_is_shown_only_on_webs_that_publish_gcve_records(monkeypatch: pytest.MonkeyPatch) -> None:
    webs = [SimpleNamespace(id=1, name="Main", gcve_enabled=False), SimpleNamespace(id=2, name="GNA", gcve_enabled=True)]
    monkeypatch.setattr("model.product_preset.PublicWeb", SimpleNamespace(query=SimpleNamespace(all=lambda: webs)))
    preset = ProductPreset("GCVE Advisory", public_web_enabled=True)
    preset.system_key = gcve.GCVE_PRESET_KEY

    assert preset.public_web_ids == [2]
    assert [preset.shown_on_web(web_id) for web_id in (1, 2, None)] == [False, True, True]
    assert preset.web_choices == [{"id": 2, "name": "GNA"}]


# -- publishing ------------------------------------------------------------------------------


@pytest.fixture
def gcve_preset(monkeypatch: pytest.MonkeyPatch) -> ProductPreset:
    preset = ProductPreset("GCVE Advisory", public_web_enabled=True)
    preset.system_key = gcve.GCVE_PRESET_KEY
    monkeypatch.setattr(ProductPreset, "find", classmethod(lambda _cls, _id: preset))
    monkeypatch.setattr(Product, "_published_state_id", staticmethod(lambda: 5))
    monkeypatch.setattr(Setting, "get_setting", classmethod(lambda _cls, *_args: ""))
    return preset


@pytest.fixture
def organization_gnas(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The organizations' GNAs by organization id, as the test sets them."""
    gnas: dict[int, SimpleNamespace] = {1: SimpleNamespace(gna_id=65535, short_name="TEST-GNA")}
    monkeypatch.setattr(OrganizationGna, "for_organization", classmethod(lambda _cls, organization_id: gnas.get(organization_id)))
    return gnas


def _published_report(**fields: object) -> SimpleNamespace:
    assignment = SimpleNamespace(gna_id=65535, published=False, publish=lambda: None)
    return SimpleNamespace(
        **{
            "gcve_id": "GCVE-65535-2026-0001",
            "title": "Login bypass",
            "is_cvd": True,
            "organization_id": 1,
            "gna_short_name": "TEST-GNA",
            "gcve_assignment": assignment,
            **fields,
        },
    )


@pytest.mark.usefixtures("organization_gnas")
def test_publishing_a_gcve_advisory_names_what_is_wrong(monkeypatch: pytest.MonkeyPatch, gcve_preset: ProductPreset) -> None:  # noqa: ARG001
    report = _published_report()
    monkeypatch.setattr("model.product.gcve_publication.problems", lambda _item, _name: ["References: required"])

    with pytest.raises(GcvePublicationError, match=r"GCVE-65535-2026-0001: References: required"):
        Product.publish_gcve_records(5, 3, [report])


@pytest.mark.usefixtures("organization_gnas")
def test_no_gcve_record_before_the_directory_names_its_gna(monkeypatch: pytest.MonkeyPatch, gcve_preset: ProductPreset) -> None:  # noqa: ARG001
    monkeypatch.setattr("model.product.gcve_publication.problems", lambda _item, _name: [])

    with pytest.raises(GcvePublicationError, match=r"GCVE-65535-2026-0001: the short name of GNA 65535 is not known yet"):
        Product.publish_gcve_records(5, 3, [_published_report(gna_short_name=None)])


@pytest.mark.usefixtures("organization_gnas")
def test_publishing_a_gcve_advisory_publishes_its_records(monkeypatch: pytest.MonkeyPatch, gcve_preset: ProductPreset) -> None:  # noqa: ARG001
    published = []
    assignment = SimpleNamespace(gna_id=65535, published=False)

    def publish() -> None:
        published.append(1)
        assignment.published = True

    assignment.publish = publish
    changed = []
    cve_assignment = SimpleNamespace(published=True, changed=lambda: changed.append(1))
    report = _published_report(title="x", gcve_assignment=assignment, cve_assignment=cve_assignment)
    monkeypatch.setattr("model.product.gcve_publication.problems", lambda _item, _name: [])

    Product.publish_gcve_records(5, 3, [report])
    Product.publish_gcve_records(4, 3, [report])  # not the published state: nothing happens
    Product.publish_gcve_records(5, 3, [report])  # saved again while published

    assert published == [1, 1]
    # Its published CVE record names the GCVE record from the first publication on: out of date once.
    assert changed == [1]


def test_a_report_written_without_the_gna_number_gets_its_gcve_identifier_when_published(
    monkeypatch: pytest.MonkeyPatch,
    gcve_preset: ProductPreset,  # noqa: ARG001
    organization_gnas: dict,
) -> None:
    allocated = []

    def allocate(_cls: type, report: SimpleNamespace, gna_id: int) -> None:
        allocated.append(gna_id)
        report.gcve_assignment = SimpleNamespace(gna_id=gna_id, published=False, publish=lambda: None)

    monkeypatch.setattr(GcveAssignment, "allocate", classmethod(allocate))
    monkeypatch.setattr("model.product.gcve_publication.problems", lambda _item, _name: [])
    report = _published_report(gcve_id=None, title="x", organization_id=2, gcve_assignment=None)

    with pytest.raises(GcvePublicationError, match="no GCVE identifier, and its organization has no GNA number"):
        Product.publish_gcve_records(5, 3, [report])
    assert allocated == []

    # Its organization's GNA number, not another's.
    organization_gnas[2] = SimpleNamespace(gna_id=4242, short_name="OTHER")
    Product.publish_gcve_records(5, 3, [report])
    assert allocated == [4242]


def test_a_published_record_stays_in_the_feed(monkeypatch: pytest.MonkeyPatch, gcve_preset: ProductPreset) -> None:
    held = SimpleNamespace(id=11, gcve_id="GCVE-65535-2026-0001", gcve_assignment=SimpleNamespace(published=True))
    product = SimpleNamespace(id=21, state_id=5, product_preset=gcve_preset, report_items=[held])
    monkeypatch.setattr(Product, "_held_elsewhere", classmethod(lambda _cls, _product_id: set()))

    with pytest.raises(GcveRecordsHeldError, match="GCVE-65535-2026-0001 is published"):
        Product.check_gcve_records_kept(product, 4, 3, [held])  # unpublished
    with pytest.raises(GcveRecordsHeldError):
        Product.check_gcve_records_kept(product, 5, 3, [])  # its report taken out
    with pytest.raises(GcveRecordsHeldError):
        Product.check_gcve_records_kept(product, None, None, [])  # deleted
    Product.check_gcve_records_kept(product, 5, 3, [held])  # edited, still holding it

    monkeypatch.setattr(Product, "_held_elsewhere", classmethod(lambda _cls, _product_id: {11}))
    Product.check_gcve_records_kept(product, None, None, [])  # another advisory keeps it


# -- an organization's GNA -------------------------------------------------------------------


@pytest.fixture
def gnas(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Organizations' GNAs saved without a database: by organization, with the numbers identifiers were allocated with."""
    state = SimpleNamespace(rows={}, allocated=set(), added=[], deleted=[])
    monkeypatch.setattr(OrganizationGna, "for_organization", classmethod(lambda _cls, organization_id: state.rows.get(organization_id)))
    monkeypatch.setattr(
        OrganizationGna,
        "find_by_gna",
        classmethod(lambda _cls, gna_id: next((row for row in state.rows.values() if row.gna_id == gna_id), None)),
    )
    monkeypatch.setattr(GcveAssignment, "any_exists", classmethod(lambda _cls, gna_id: gna_id in state.allocated))

    def add(row: OrganizationGna) -> None:
        state.added.append(row)
        state.rows[row.organization_id] = row

    def delete(row: OrganizationGna) -> None:
        state.deleted.append(row)
        state.rows.pop(row.organization_id)

    monkeypatch.setattr(db.session, "add", add)
    monkeypatch.setattr(db.session, "delete", delete)
    return state


def test_an_organizations_gna_number_is_checked(gnas: SimpleNamespace) -> None:
    for number in (0, 65536):
        with pytest.raises(GnaSettingsError, match="from 1 to 65535"):
            OrganizationGna.save(1, number, None, None, "admin")
    with pytest.raises(GnaSettingsError, match="JSON object"):
        OrganizationGna.save(1, 65535, None, [1], "admin")

    gna = OrganizationGna.save(1, 65535, " ", {"governance": {}}, "admin")

    assert (gna.organization_id, gna.gna_id, gna.records_license, gna.conformance) == (1, 65535, "CC-BY-4.0", {"governance": {}})
    assert gnas.added == [gna]


@pytest.mark.usefixtures("gnas")
def test_two_organizations_never_share_a_gna_number() -> None:
    OrganizationGna.save(1, 65535, None, None, "admin")

    with pytest.raises(GnaSettingsError, match="is the one of the organization") as refused:
        OrganizationGna.save(2, 65535, None, None, "admin")
    assert refused.value.conflict


def test_the_gna_number_is_fixed_once_identifiers_were_allocated_with_it(gnas: SimpleNamespace) -> None:
    gna = OrganizationGna.save(1, 65535, None, None, "admin")
    gna.short_name = "TEST-GNA"
    # Another number, while none was allocated: what the directory said is forgotten.
    gna = OrganizationGna.save(1, 4242, None, None, "admin")
    assert (gna.gna_id, gna.short_name) == (4242, None)

    gnas.allocated.add(4242)
    with pytest.raises(GnaSettingsError, match="cannot change any more") as refused:
        OrganizationGna.save(1, 65535, None, None, "admin")
    assert refused.value.conflict
    with pytest.raises(GnaSettingsError, match="cannot change any more"):
        OrganizationGna.save(1, None, None, None, "admin")
    # The licence and the conformance details still change.
    assert OrganizationGna.save(1, 4242, "CC0-1.0", None, "admin").records_license == "CC0-1.0"

    gnas.allocated.clear()
    assert OrganizationGna.save(1, None, None, None, "admin") is None
    assert gnas.deleted == [gna]


def test_a_cvd_report_moves_to_another_organization_only_while_it_holds_no_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("model.report_item.cvd_organizations", lambda _user: [_organization(1), _organization(2, gna_id=None, cna=True)])
    free = SimpleNamespace(has_publication_ids=False)
    held = SimpleNamespace(has_publication_ids=True)

    assert ReportItem._organization_change_refused(free, 2, USER) is None
    assert "one of your organizations" in ReportItem._organization_change_refused(free, 3, USER)
    assert "cannot change" in ReportItem._organization_change_refused(held, 2, USER)


def test_an_organization_publishing_cvd_reports_is_not_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    state = SimpleNamespace(reports=False, gna=None, webs=[])
    query = SimpleNamespace(
        filter=lambda *_args: SimpleNamespace(limit=lambda _n: SimpleNamespace(first=lambda: 1 if state.reports else None)),
    )
    monkeypatch.setattr(db.session, "query", lambda *_args: query)
    monkeypatch.setattr(OrganizationGna, "for_organization", classmethod(lambda _cls, _organization_id: state.gna))
    monkeypatch.setattr("model.public_web.PublicWeb", SimpleNamespace(query=SimpleNamespace(all=lambda: state.webs)))

    assert organization_gna.organization_delete_refused(1) is None
    state.webs = [SimpleNamespace(name="Advisories", hostname="a.example.org", gcve_organization_id=1)]
    assert organization_gna.organization_delete_refused(1) == "The public web Advisories publishes its GCVE records"
    state.gna = SimpleNamespace(gna_id=65535, frozen=True)
    assert "allocated with its GNA number 65535" in organization_gna.organization_delete_refused(1)
    state.reports = True
    assert organization_gna.organization_delete_refused(1) == "It owns CVD Reports"


@pytest.mark.parametrize("system_key", [gcve.GCVE_PRESET_KEY, gcve.CVE_PRESET_KEY])
def test_a_gcve_or_cve_product_holds_cvd_reports_only_and_is_english(monkeypatch: pytest.MonkeyPatch, system_key: str) -> None:
    preset = ProductPreset("Shipped", public_web_enabled=False)
    preset.system_key = system_key
    monkeypatch.setattr(ProductPreset, "find", classmethod(lambda _cls, _id: preset))
    organization = SimpleNamespace(name="CERT")
    cvd = SimpleNamespace(id=1, title="Login bypass", is_cvd=True, organization=organization)
    other = SimpleNamespace(id=2, title="Weekly digest", is_cvd=False)
    elsewhere = SimpleNamespace(id=3, title="XSS", is_cvd=True, organization=SimpleNamespace(name="Partner CERT"))

    product = SimpleNamespace(product_preset_id=3, report_items=[cvd, other], language="cs", submitted_translations=None)
    with pytest.raises(CvdProductError, match="holds CVD Reports only; not one: 'Weekly digest'"):
        Product._apply_cvd_product_rules(product)

    # One organization publishes its records.
    product.report_items = [cvd, elsewhere]
    with pytest.raises(CvdProductError, match=r"of one organization; these belong to several \(CERT: 'Login bypass'; Partner CERT: 'XSS'\)"):
        Product._apply_cvd_product_rules(product)

    product.report_items = [cvd]
    Product._apply_cvd_product_rules(product)
    # English, and not translated: its translations are emptied with it.
    assert (product.language, product.submitted_translations) == ("en", {})


def test_any_other_product_keeps_its_language_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ProductPreset, "find", classmethod(lambda _cls, _id: ProductPreset("Weekly", public_web_enabled=False)))
    product = SimpleNamespace(
        product_preset_id=3,
        report_items=[SimpleNamespace(id=2, title="x", is_cvd=False)],
        language="cs",
        submitted_translations=None,
    )

    Product._apply_cvd_product_rules(product)

    assert (product.language, product.submitted_translations) == ("cs", None)
