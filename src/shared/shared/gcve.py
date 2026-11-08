"""GCVE and CVE publishing: the shipped CVD Report type, its two presets and their vocabularies.

Taranis can act as a GCVE Numbering Authority (GNA, https://gcve.eu): every report item of the
shipped "CVD Report" type gets an identifier ``GCVE-<GNA>-<year>-<number>`` when it is created
(GCVE-BCP-04), and a published "GCVE Advisory" product puts its CVD Reports, as CVE Record Format
records with the GCVE extension (GCVE-BCP-05), on the public webs that publish GCVE records
(GCVE-BCP-03). A published "CVE Record" product submits the same reports to MITRE's CVE Services,
the organisation acting as a CVE Numbering Authority (CNA). The type and the presets are seeded by
migrations and locked: they can only be switched on or off.

This module is what core, public-web and the migration agree on: the stable keys the type and
the preset are found by, the fields of the type (their titles are the keys report templates use),
and the vocabularies the CVE Record Format and the GCVE BCPs prescribe.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# -- the shipped type and preset ---------------------------------------------------------

# ``report_item_type.system_key`` / ``product_preset.system_key`` of the shipped ones.
CVD_TYPE_KEY = "cvd"
GCVE_PRESET_KEY = "gcve"

CVD_TYPE_TITLE = "CVD Report"
CVD_TYPE_DESCRIPTION = "Coordinated Vulnerability Disclosure, published as a GCVE or a CVE record"
GCVE_PRESET_NAME = "GCVE Advisory"
GCVE_PRESET_DESCRIPTION = "CVD Reports published as GCVE records on the public webs that publish GCVE records"

# A CVD Report is written in English: the CVE Record Format requires an English description.
CVD_LANGUAGE = "en"

# -- CVE publication (this organisation as a CVE Numbering Authority) ----------------------

# The shipped "CVE Record" preset: publishing one submits its CVD Reports to MITRE's CVE Services
# as CVE records, with CVE IDs reserved by the organisation's CNA account.
CVE_PRESET_KEY = "cve"
CVE_PRESET_NAME = "CVE Record"
CVE_PRESET_DESCRIPTION = "CVD Reports published as CVE records through CVE Services (this organisation as a CNA)"

# Where CVE Services answers, by environment; the test one is for trying a CNA account out.
CVE_ENVIRONMENTS = ("production", "test")
CVE_SERVICES_URLS = {
    "production": "https://cveawg.mitre.org/api",
    "test": "https://cveawg-test.mitre.org/api",
}

# Where published CVE records are read (to fill a CVD Report from one): the data provider of this
# type, seeded with MITRE's public CVE Services API; MITRE's when there is none.
CVE_SERVICES_API_TYPE = "CVE_SERVICES"
CVE_SERVICES_PUBLIC_URL = "https://cveawg.mitre.org/api/"
CVE_RECORD_WEB_URL = "https://www.cve.org/CVERecord?id="

CVE_ID_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,19}$")

# -- the GNA (an organization's, see core's model.organization_gna) ------------------------

# GNA numbers are positive; 0 is the CVE Program's, 65535 the one GCVE reserves for testing.
GNA_ID_MIN = 1
GNA_ID_MAX = 65535

# The licence a GNA's records are published under, until its organization names another.
DEFAULT_RECORDS_LICENSE = "CC-BY-4.0"

# The GNA directory gcve.eu publishes: every GNA's number, short and full name, and where it
# publishes. A GNA's short name is taken from it, never typed in. The setting says where it is
# downloaded from; ``<url>.sigsha512`` is its signature.
DIRECTORY_URL_SETTING = "GCVE_GNA_DIRECTORY_URL"
DEFAULT_DIRECTORY_URL = "https://gcve.eu/dist/gcve.json"


class RegistrationUrl(NamedTuple):
    """An address a web publishing a GNA's records serves.

    ``field`` is the GNA directory field gcve.eu registers it as (None: not registered there).
    """

    key: str
    field: str | None
    url: str


def registration_urls(hostname: str, gna_id: int, *, security_txt: bool = False) -> list[RegistrationUrl]:
    """What a web publishing GNA ``gna_id``'s records serves, and what gcve.eu registers of it.

    Args:
        hostname: The web's hostname.
        gna_id: The GNA number.
        security_txt: Whether the web serves a security.txt (it has a security contact).

    Returns:
        list[RegistrationUrl]: The website, the pull API and the dump directory as the directory
            names them, then the endpoints (GCVE-BCP-03, GCVE-BCP-06).
    """
    base = f"https://{hostname.strip().rstrip('/')}"
    urls = [
        RegistrationUrl("website", "gcve_url", f"{base}/"),
        RegistrationUrl("pull_api", "gcve_pull_api", f"{base}/"),
        RegistrationUrl("dumps", "gcve_dump", f"{base}/dumps/"),
        RegistrationUrl("publication", None, f"{base}/api/gcve/publication"),
        RegistrationUrl("dump", None, f"{base}/dumps/gna-{gna_id}.ndjson"),
        RegistrationUrl("conformance", None, f"{base}/api/gcve/conformance"),
    ]
    if security_txt:
        urls.append(RegistrationUrl("security_txt", None, f"{base}/.well-known/security.txt"))
    return urls


# -- identifiers (GCVE-BCP-04) -------------------------------------------------------------

GCVE_ID_PATTERN = re.compile(r"^GCVE-(?P<gna>[0-9]+)-(?P<year>[0-9]{4})-(?P<number>[0-9]{4,})$")


def gcve_id(gna_id: int, year: int, number: int) -> str:
    """The identifier of the ``number``-th allocation of ``year``, padded to at least 4 digits.

    Args:
        gna_id: The GNA number.
        year: The year of allocation.
        number: Its sequence number within the year, from 1.

    Returns:
        str: ``GCVE-<GNA>-<year>-<number>``, e.g. ``GCVE-65535-2026-0001``.
    """
    return f"GCVE-{gna_id}-{year}-{number:04d}"


# -- record format (GCVE-BCP-05 on CVE Record Format 5.2.0) --------------------------------

DATA_TYPE = "CVE_RECORD"
DATA_VERSION = "5.2.0"

# Every record type GCVE-BCP-05 defines.
RECORD_TYPES = (
    "advisory",
    "update",
    "analysis",
    "metadata",
    "reference",
    "comment",
    "statement",
    "remediation",
    "deprecation",
    "detection",
    "translation",
    "bundle",
)
DEFAULT_RECORD_TYPE = "advisory"
# The only record type a CVE record is published for: a CVE record describes a vulnerability.
CVE_RECORD_TYPE = "advisory"
# Records are English only, and a translation record needs a language of its own.
OFFERED_RECORD_TYPES = tuple(record_type for record_type in RECORD_TYPES if record_type != "translation")
# GCVE-BCP-05 (1.8): every record type but these two MUST include a relationships table.
RECORD_TYPES_WITH_OPTIONAL_RELATIONSHIPS = ("advisory", "bundle")
RECORD_TYPES_NEEDING_RELATIONSHIPS = tuple(
    record_type for record_type in RECORD_TYPES if record_type not in RECORD_TYPES_WITH_OPTIONAL_RELATIONSHIPS
)

RELATIONSHIP_TYPES = (
    "possibly_related",
    "related",
    "not equal",
    "equal",
    "superset",
    "subset",
    "overlap",
    "opposes",
    "not_applicable",
)

CREDIT_TYPES = (
    "finder",
    "reporter",
    "analyst",
    "coordinator",
    "remediation developer",
    "remediation reviewer",
    "remediation verifier",
    "tool",
    "sponsor",
    "other",
)

REFERENCE_TAGS = (
    "broken-link",
    "customer-entitlement",
    "exploit",
    "government-resource",
    "issue-tracking",
    "mailing-list",
    "mitigation",
    "not-applicable",
    "patch",
    "permissions-required",
    "media-coverage",
    "product",
    "related",
    "release-notes",
    "signature",
    "technical-description",
    "third-party-advisory",
    "vendor-advisory",
    "vdb-entry",
)

CNA_TAGS = ("unsupported-when-assigned", "exclusively-hosted-service", "disputed")

DISCOVERY_VALUES = ("INTERNAL", "EXTERNAL", "USER", "UNKNOWN")

VERSION_STATUSES = ("affected", "unaffected", "unknown")

# The CVE sub-schema a JSON field is checked against (the attribute's ``validator_parameter``).
JSON_METRIC_OTHER = "metric_other"
JSON_TAXONOMY_MAPPING = "taxonomy_mapping"
JSON_SCHEMAS = (JSON_METRIC_OTHER, JSON_TAXONOMY_MAPPING)

# The longest text value the CVE Record Format takes, and the longest title.
TEXT_MAX_LENGTH = 4096
TITLE_MAX_LENGTH = 256

# -- the CVD Report type --------------------------------------------------------------------


class CvdAttribute(NamedTuple):
    """An attribute (``attribute`` table) the CVD Report type uses."""

    name: str
    type: str
    description: str
    # The constants a choice attribute offers, or a structured one draws its vocabulary from.
    constants: tuple[str, ...] = ()
    default_value: str | None = None
    # For JSON attributes: the CVE sub-schema its values are checked against.
    validator_parameter: str | None = None


class CvdField(NamedTuple):
    """A field of the CVD Report type (``attribute_group_item``)."""

    title: str
    # The attribute it uses: a name from ``CVD_ATTRIBUTES``, or one of ``GENERIC_ATTRIBUTE_TYPES``
    # for the first attribute of that type, the one every report type shares (where the
    # imported CVE and CWE dictionaries live, too).
    attribute: str
    min_occurrence: int
    max_occurrence: int
    description: str

    @property
    def key(self) -> str:
        """The key report templates read it by (``item.attrs.<key>``)."""
        return self.title.lower().replace(" ", "_")


class CvdGroup(NamedTuple):
    """A group of fields of the CVD Report type (``attribute_group``)."""

    title: str
    fields: tuple[CvdField, ...]


# How many values an unlimited field takes, as in the other shipped report types.
MANY = 1000

# Fields of these types use the generic attribute of the type (Text, Rich Text, Date, CVSS, CVE,
# CWE); only fields with a vocabulary or a structure of their own have a CVD attribute.
GENERIC_ATTRIBUTE_TYPES = ("STRING", "RICH_TEXT", "DATE", "CVSS", "CVE", "CWE")

CVD_ATTRIBUTES = (
    CvdAttribute("CVD Record type", "RADIO", "GCVE record type (GCVE-BCP-05)", OFFERED_RECORD_TYPES, DEFAULT_RECORD_TYPE),
    CvdAttribute("CVD Discovery", "RADIO", "How the vulnerability was discovered", DISCOVERY_VALUES),
    CvdAttribute("CVD Tags", "MULTI_CHOICE", "CVE record tags", CNA_TAGS),
    CvdAttribute("CVD Affected product", "AFFECTED", "Affected product with its versions", VERSION_STATUSES),
    CvdAttribute("CVD Credit", "CREDIT", "Credit for work on the vulnerability", CREDIT_TYPES),
    CvdAttribute("CVD Timeline event", "TIMELINE", "Dated event of the disclosure"),
    CvdAttribute("CVD Relationship", "RELATIONSHIP", "Relationship to another record (GCVE-BCP-05)", RELATIONSHIP_TYPES),
    CvdAttribute("CVD Reference", "REFERENCE", "Reference with its name and tags", REFERENCE_TAGS),
    CvdAttribute("CVD Other metric", "JSON", "Other impact metric (CVE metrics.other)", validator_parameter=JSON_METRIC_OTHER),
    CvdAttribute("CVD Taxonomy mapping", "JSON", "Taxonomy mapping (CVE taxonomyMappings)", validator_parameter=JSON_TAXONOMY_MAPPING),
)

CVD_GROUPS = (
    CvdGroup(
        "Record",
        (
            CvdField("Record type", "CVD Record type", 1, 1, "The GCVE record type; deprecation withdraws the record"),
            CvdField("CVE", "CVE", 0, 1, "The CVE of the same vulnerability, if it has one"),
            CvdField("Related records", "CVD Relationship", 0, MANY, "Other records this one relates to"),
            CvdField("Tags", "CVD Tags", 0, 1, "CVE record tags"),
        ),
    ),
    CvdGroup(
        "Vulnerability",
        (
            CvdField("Description", "RICH_TEXT", 1, 1, "What the vulnerability is"),
            CvdField("Affected products", "CVD Affected product", 1, MANY, "Products and versions affected"),
            CvdField("CVSS", "CVSS", 0, MANY, "CVSS vectors (2.0, 3.0, 3.1 or 4.0)"),
            CvdField("Other metrics", "CVD Other metric", 0, MANY, "Metrics in another format, e.g. SSVC"),
            CvdField("CWE", "CWE", 0, MANY, "Weaknesses (problem types)"),
            CvdField("Problem types", "STRING", 0, MANY, "Problem types without a CWE"),
            CvdField("Impacts", "RICH_TEXT", 0, MANY, "Impacts; a leading CAPEC-<n> names the CAPEC pattern"),
            CvdField("Taxonomy mappings", "CVD Taxonomy mapping", 0, MANY, "Mappings to other taxonomies"),
            CvdField("Date public", "DATE", 0, 1, "When the vulnerability was disclosed publicly"),
        ),
    ),
    CvdGroup(
        "Remediation",
        (
            CvdField("Solutions", "RICH_TEXT", 0, MANY, "Fixes"),
            CvdField("Workarounds", "RICH_TEXT", 0, MANY, "Temporary mitigations"),
            CvdField("Configurations", "RICH_TEXT", 0, MANY, "Configurations required for exposure"),
            CvdField("Exploits", "RICH_TEXT", 0, MANY, "Known exploits and exploitation"),
        ),
    ),
    CvdGroup(
        "Source",
        (
            CvdField("Discovery", "CVD Discovery", 0, 1, "How the vulnerability was discovered"),
            CvdField("Defects", "STRING", 0, MANY, "Defect (bug tracker) identifiers"),
            CvdField("Advisories", "STRING", 0, MANY, "Advisory identifiers"),
        ),
    ),
    CvdGroup(
        "Disclosure",
        (
            CvdField("Timeline", "CVD Timeline event", 0, MANY, "Events of the disclosure"),
            CvdField("Credits", "CVD Credit", 0, MANY, "People, organisations and tools credited"),
        ),
    ),
    CvdGroup(
        "Resources",
        (CvdField("References", "CVD Reference", 1, MANY, "References; texts cite them as [n]"),),
    ),
)


def cvd_fields() -> dict[str, CvdField]:
    """Every field of the CVD Report type, by key."""
    return {field.key: field for group in CVD_GROUPS for field in group.fields}
