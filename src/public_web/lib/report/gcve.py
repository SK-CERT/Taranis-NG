"""The GCVE publication of a web: its records filtered, sorted and paged (GCVE-BCP-03).

Core builds the records (CVE Record Format 5.2.0 with the GCVE extension, GCVE-BCP-05) of the
published GCVE Advisories a web shows; the node keeps them and answers the queries GCVE-BCP-03
defines for ``/api/gcve/publication``, serves them all as a dump, and declares the endpoint in
the web's security.txt. It also writes the conformance document GCVE-BCP-06 (a draft) asks a GNA
to publish. Everything here is a pure function of the records and the web's settings.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

DEFAULT_PER_PAGE = 30
MAX_PER_PAGE = 100
DATE_FIELDS = {"published": "datePublished", "updated": "dateUpdated", "reserved": "dateReserved"}
DEFAULT_DATE_SORT = "updated"
SINCE_FORMATS = ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y%m%d")
BCP_06_VERSION = "BCP-06-1.1"
SYNC_PROTOCOL = "GCVE-BCP-03"
# How long a security.txt is valid (RFC 9116 asks for less than a year).
SECURITY_TXT_VALIDITY = timedelta(days=180)

_CWE = re.compile(r"^(?:CWE-)?([0-9]+)$", re.IGNORECASE)


class QueryError(ValueError):
    """A query parameter that cannot be understood; the message says which."""


def record_id(record: dict) -> str:
    """The GCVE identifier of a record (GCVE-BCP-05): the ``vulnId`` of its ``x_gcve`` entry.

    That is the ``advisory`` entry, or the only entry of a record without one (an ``update``, a
    ``deprecation``...). A record built before the identifier left ``cveMetadata`` still has it
    there; empty when the record has none.
    """
    cna = (record.get("containers") or {}).get("cna") or {}
    entries = [entry for entry in cna.get("x_gcve") or [] if isinstance(entry, dict)]
    entry = next((entry for entry in entries if entry.get("recordType") == "advisory"), None)
    if entry is None and len(entries) == 1:
        entry = entries[0]
    if entry is not None and entry.get("vulnId"):
        return str(entry["vulnId"])
    return str((record.get("cveMetadata") or {}).get("vulnId") or "")


def parse_since(value: str | None) -> datetime | None:
    """The moment of ``since``: an ISO date-time ending in Z, ``YYYY-MM-DD`` or ``YYYYMMDD``.

    Raises:
        QueryError: When it is none of these.
    """
    if not value:
        return None
    for pattern in SINCE_FORMATS:
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    msg = "since must be a date (YYYY-MM-DD or YYYYMMDD) or a date-time (YYYY-MM-DDTHH:MM:SSZ)"
    raise QueryError(msg)


def page_size(value: str | None) -> int:
    """``per_page``: 30 by default, at most 100 (GCVE-BCP-03)."""
    try:
        size = int(value) if value not in (None, "") else DEFAULT_PER_PAGE
    except ValueError as error:
        msg = "per_page must be a whole number"
        raise QueryError(msg) from error
    return min(max(size, 1), MAX_PER_PAGE)


def page_number(value: str | None) -> int:
    """``page``: from 1."""
    try:
        number = int(value) if value not in (None, "") else 1
    except ValueError as error:
        msg = "page must be a whole number"
        raise QueryError(msg) from error
    return max(number, 1)


def _moment(record: dict, field: str) -> datetime | None:
    raw = record.get("cveMetadata", {}).get(field)
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _cwe_ids(record: dict) -> set[str]:
    cna = record.get("containers", {}).get("cna", {})
    return {
        f"CWE-{match.group(1)}"
        for problem in cna.get("problemTypes") or []
        for description in problem.get("descriptions") or []
        if (match := _CWE.match(str(description.get("cweId") or "")))
    }


def _products(record: dict) -> list[str]:
    cna = record.get("containers", {}).get("cna", {})
    return [str(affected.get("product") or affected.get("packageName") or "").lower() for affected in cna.get("affected") or []]


def select(
    records: list[dict],
    *,
    gna_id: int | None,
    since: datetime | None = None,
    date_sort: str | None = None,
    sort_order: str | None = None,
    source: str | None = None,
    cwe: str | None = None,
    product: str | None = None,
    assigner: str | None = None,
) -> list[dict]:
    """The records a query of ``/api/gcve/publication`` asks for, in its order.

    Args:
        records: Every record of the web.
        gna_id: The GNA number; its records are the source ``gna-<GNA>``.
        since: Only records published or updated from then on.
        date_sort: ``published``, ``updated`` (the default, also for ``''``) or ``reserved``.
        sort_order: ``desc`` (the default) or ``asc``.
        source: Only records of this source; a GNA publishes only its own (``gna-<GNA>``).
        cwe: Only records with this CWE (``79`` or ``CWE-79``).
        product: Only records affecting a product whose name contains this (any vendor).
        assigner: With ``product``, only records of this assigner's short name.

    Raises:
        QueryError: For an unknown ``date_sort`` or ``sort_order``.
    """
    field = DATE_FIELDS.get(date_sort or DEFAULT_DATE_SORT)
    if field is None:
        msg = "date_sort must be published, updated or reserved"
        raise QueryError(msg)
    order = (sort_order or "desc").lower()
    if order not in ("asc", "desc"):
        msg = "sort_order must be asc or desc"
        raise QueryError(msg)

    if source and source.lower() != f"gna-{gna_id}":
        return []
    chosen = list(records)
    if since is not None:
        chosen = [
            record
            for record in chosen
            if any(moment is not None and moment >= since for moment in (_moment(record, "datePublished"), _moment(record, "dateUpdated")))
        ]
    if cwe:
        match = _CWE.match(cwe.strip())
        wanted = f"CWE-{match.group(1)}" if match else cwe.strip().upper()
        chosen = [record for record in chosen if wanted in _cwe_ids(record)]
    if product:
        needle = product.strip().lower()
        chosen = [record for record in chosen if any(needle in name for name in _products(record))]
        if assigner:
            # GCVE-BCP-03: the assigner narrows a product query.
            chosen = [
                record
                for record in chosen
                if str(record.get("cveMetadata", {}).get("assignerShortName") or "").lower() == assigner.strip().lower()
            ]
    oldest = datetime.min.replace(tzinfo=UTC)
    chosen.sort(
        key=lambda record: (_moment(record, field) or oldest, record_id(record)),
        reverse=order == "desc",
    )
    return chosen


def page_of(records: list[dict], page: int, per_page: int) -> list[dict]:
    """One page of the records, from 1."""
    start = (page - 1) * per_page
    return records[start : start + per_page]


def light(records: list[dict]) -> list[list[Any]]:
    """The minimal tuples of light mode: ``[GCVE identifier, CVE identifier or null]``."""
    return [[record_id(record) or None, record.get("cveMetadata", {}).get("cveId")] for record in records]


def ndjson(records: list[dict]) -> str:
    """The records as newline-delimited JSON, one per line, as the dump serves them."""
    return "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)


def security_txt(hostname: str, contact: str, now: datetime | None = None) -> str:
    """A security.txt (RFC 9116) that declares the web's GCVE publication endpoint (GCVE-BCP-03).

    Args:
        hostname: The web's base URL (``https://...``).
        contact: Its security contact, a ``mailto:`` or https URI; a bare e-mail address gets ``mailto:``.
        now: The moment it is written (for ``Expires``).
    """
    now = now or datetime.now(UTC)
    if "@" in contact and ":" not in contact:
        contact = f"mailto:{contact}"
    expires = (now + SECURITY_TXT_VALIDITY).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"Contact: {contact}",
        f"Expires: {expires}",
        "Preferred-Languages: en",
        f"Canonical: {hostname}/.well-known/security.txt",
        f"GCVE: {hostname}/api/gcve/publication",
    ]
    return "\n".join(lines) + "\n"


def _merge(computed: dict, given: dict) -> dict:
    merged = dict(computed)
    for key, value in given.items():
        merged[key] = _merge(merged[key], value) if isinstance(value, dict) and isinstance(merged.get(key), dict) else value
    return merged


def conformance(
    records: list[dict],
    *,
    gna_id: int | None,
    hostname: str,
    license_name: str | None,
    details: dict | None,
    today: date | None = None,
) -> dict:
    """The GNA conformance document of GCVE-BCP-06 (a draft), for the web's records.

    What can be known from the records and the endpoint is filled in; the governance and the
    disclosure process come from ``details`` (the conformance details of the organization whose
    records the web publishes, see core's model.organization_gna), which may also override
    anything computed.
    """
    today = today or datetime.now(UTC).date()
    cnas = [record.get("containers", {}).get("cna", {}) for record in records]
    descriptions = [len(str((cna.get("descriptions") or [{}])[0].get("value") or "")) for cna in cnas]
    has_cvss = any(key.startswith("cvss") for cna in cnas for metric in cna.get("metrics") or [] for key in metric)
    has_cwe = any(_cwe_ids(record) for record in records)
    computed = {
        "gcve_bcp_version": BCP_06_VERSION,
        "gna_id": str(gna_id) if gna_id is not None else None,
        "last_updated": today.isoformat(),
        "license": license_name,
        "governance": {},
        "disclosure_process": {"automated_allocation": True},
        "allocation_quality": {
            "identifier_reuse_detected": False,
            "identifier_reassignment_detected": False,
            "uses_permalinks": True,
            "average_description_length": round(sum(descriptions) / len(descriptions)) if descriptions else 0,
            "has_cwe_classification": has_cwe,
            "has_cvss_score": has_cvss,
            "has_epss_score": False,
            "average_fields_per_record": round(sum(len(cna) for cna in cnas) / len(cnas)) if cnas else 0,
        },
        "interoperability": {
            "provides_machine_readable_feed": True,
            "feed_format": ["json", "ndjson"],
            "schema_version_declared": True,
            "uses_cwe": has_cwe,
            "uses_cvss": has_cvss,
            "uses_openvex": False,
            "uses_ossf_schema": False,
        },
        "synchronization": {
            "provides_sync_endpoint": True,
            "sync_endpoint_url": f"{hostname}/api/gcve/publication",
            "sync_protocol_version": SYNC_PROTOCOL,
        },
    }
    return _merge(computed, details or {})
