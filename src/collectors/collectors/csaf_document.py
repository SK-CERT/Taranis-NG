"""Turning a CSAF document into a news item.

Handles CSAF 2.0 and 2.1. Where the two differ, a small reader function knows both shapes
(`cwes`, `scores`, `tlp_label`, `disclosure_date`), so each difference is handled in one
place. Every field is read defensively: publishers do not all follow the profiles (Intel's
security advisories have no product tree), and a missing field must never cost the document.

Identity comes from inside the document, never from its file name:
- `version_key` - publisher namespace, tracking id and language - is shared by every revision
  of an advisory, so core can store a newer revision on the item it already has;
- `hash` adds the tracking version and release date, so each revision is recognised as itself.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from html import escape
from typing import TYPE_CHECKING

from shared.common import TZ
from shared.schema.news_item import NewsItemAttribute, NewsItemData

from .csaf_sources import parse_datetime

if TYPE_CHECKING:
    from collections.abc import Iterable

SUPPORTED_VERSIONS = {"2.0", "2.1"}

# Caps that keep very large documents readable. An Oracle Critical Patch Update lists some 800
# vulnerabilities; every one still becomes a CVE attribute, only the text is shortened.
MAX_DETAILED_VULNERABILITIES = 50
MAX_PRODUCTS = 20
MAX_REVISIONS = 50
MAX_REFERENCES = 50
MAX_REMEDIATIONS = 100

# Profiles 2.1 added for documents that retract an earlier one.
RETRACTED_CATEGORIES = {"csaf_withdrawn": "Withdrawn", "csaf_superseded": "Superseded"}

_AFFECTED = ("known_affected", "first_affected", "last_affected")
_FIXED = ("fixed", "first_fixed")


# A byte that is not valid UTF-8, as `surrogateescape` decodes it.
_STRAY_BYTE = re.compile("[\udc80-\udcff]")


def loads(body: bytes) -> object:
    """Parse a downloaded document.

    JSON is UTF-8, but some providers write a few characters - names in acknowledgments - in
    Windows-1252 (Oracle). Those bytes are read as such rather than losing the whole document;
    the hash and signature are still checked against the bytes as downloaded.

    Args:
        body (bytes): The document as downloaded.

    Returns:
        The parsed JSON.

    Raises:
        ValueError: The body is not JSON.
    """
    try:
        return json.loads(body)
    except UnicodeDecodeError:
        text = body.decode("utf-8-sig", errors="surrogateescape")
        return json.loads(_STRAY_BYTE.sub(lambda match: bytes([ord(match.group()) - 0xDC00]).decode("cp1252", errors="replace"), text))


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def is_csaf(data: object) -> bool:
    """Whether parsed JSON is a CSAF document at all (CVE records and metadata are JSON too)."""
    return bool(_text(_as_dict(_as_dict(data).get("document")).get("csaf_version")))


def csaf_version(data: dict) -> str:
    """The CSAF specification version the document declares."""
    return _text(_as_dict(data.get("document")).get("csaf_version"))


def category(data: dict) -> str:
    """The document category (profile), e.g. csaf_security_advisory or csaf_vex."""
    return _text(_as_dict(data.get("document")).get("category"))


def release_date(data: dict) -> datetime.datetime | None:
    """When the revision held in the document was released."""
    return parse_datetime(_as_dict(_as_dict(data.get("document")).get("tracking")).get("current_release_date"))


# --- readers for fields that differ between 2.0 and 2.1 --------------------------------------


def tlp_label(data: dict) -> str:
    """The TLP label, in TLP 2.0 naming: 2.0's WHITE is 2.1's CLEAR."""
    label = _text(_as_dict(_as_dict(_as_dict(data.get("document")).get("distribution")).get("tlp")).get("label")).upper()
    return "CLEAR" if label == "WHITE" else label


def cwes(vulnerability: dict) -> list[tuple[str, str]]:
    """(id, name) of each weakness: 2.0 has one `cwe`, 2.1 a `cwes` list."""
    entries = _as_list(vulnerability.get("cwes")) or [vulnerability.get("cwe")]
    return [(_text(entry.get("id")), _text(entry.get("name"))) for entry in entries if isinstance(entry, dict) and _text(entry.get("id"))]


def cvss_scores(vulnerability: dict) -> list[dict]:
    """Every CVSS score: 2.0 `scores[].cvss_v2/v3`, 2.1 `metrics[].content.cvss_v2/v3/v4`.

    Returns:
        Dicts with version, score, severity and vector, highest score first.
    """
    containers = [_as_dict(score) for score in _as_list(vulnerability.get("scores"))]
    containers += [_as_dict(_as_dict(metric).get("content")) for metric in _as_list(vulnerability.get("metrics"))]
    scores, vectors = [], set()
    for container in containers:
        for key, default_version in (("cvss_v4", "4.0"), ("cvss_v3", "3.x"), ("cvss_v2", "2.0")):
            cvss = _as_dict(container.get(key))
            vector = _text(cvss.get("vectorString"))
            if not cvss or vector in vectors:
                continue
            vectors.add(vector)
            score = cvss.get("baseScore")
            scores.append(
                {
                    "version": _text(cvss.get("version")) or default_version,
                    "score": score if isinstance(score, int | float) else None,
                    "severity": _text(cvss.get("baseSeverity")),
                    "vector": vector,
                },
            )
    return sorted(scores, key=lambda entry: entry["score"] or 0, reverse=True)


def top_score(vulnerability: dict) -> float:
    """The highest CVSS base score of a vulnerability, 0 without one."""
    scores = [entry["score"] for entry in cvss_scores(vulnerability) if entry["score"] is not None]
    return max(scores, default=0)


def epss(vulnerability: dict) -> list[dict]:
    """EPSS entries, 2.1 only."""
    return [
        _as_dict(_as_dict(metric).get("content")).get("epss")
        for metric in _as_list(vulnerability.get("metrics"))
        if _as_dict(_as_dict(metric).get("content")).get("epss")
    ]


def qualitative_ratings(vulnerability: dict) -> list[str]:
    """Qualitative severity ratings, 2.1 only."""
    ratings = [
        _text(_as_dict(_as_dict(metric).get("content")).get("qualitative_severity_rating"))
        for metric in _as_list(vulnerability.get("metrics"))
    ]
    return list(dict.fromkeys(rating for rating in ratings if rating))


def disclosure_date(vulnerability: dict) -> str:
    """When the vulnerability was disclosed: 2.1 `disclosure_date`, 2.0 `release_date`."""
    return _text(vulnerability.get("disclosure_date")) or _text(vulnerability.get("release_date"))


def exploitation_dates(vulnerability: dict) -> list[str]:
    """When exploitation was first known, 2.1 only."""
    return [
        _text(_as_dict(entry).get("exploitation_date"))
        for entry in _as_list(vulnerability.get("first_known_exploitation_dates"))
        if _text(_as_dict(entry).get("exploitation_date"))
    ]


def product_names(data: dict) -> dict[str, str]:
    """Product id to name, from the whole product tree. Empty when there is no tree."""
    tree = _as_dict(data.get("product_tree"))
    names: dict[str, str] = {}

    def add(product: object) -> None:
        product = _as_dict(product)
        if _text(product.get("product_id")):
            names[product["product_id"]] = _text(product.get("name")) or product["product_id"]

    def walk(branches: object) -> None:
        for branch in map(_as_dict, _as_list(branches)):
            add(branch.get("product"))
            walk(branch.get("branches"))

    walk(tree.get("branches"))
    for product in _as_list(tree.get("full_product_names")):
        add(product)
    for relationship in _as_list(tree.get("relationships")):
        add(_as_dict(relationship).get("full_product_name"))
    return names


# --- identity ------------------------------------------------------------------------------


def version_key(data: dict) -> str:
    """Identity shared by every revision of the advisory.

    The language is part of it: a publisher releasing the same advisory in two languages
    releases two documents, and neither is a revision of the other.
    """
    document = _as_dict(data.get("document"))
    namespace = _text(_as_dict(document.get("publisher")).get("namespace"))
    tracking_id = _text(_as_dict(document.get("tracking")).get("id"))
    lang = _text(document.get("lang")).lower()
    return hashlib.sha256(f"{namespace}|{tracking_id}|{lang}".encode()).hexdigest()


def revision_hash(data: dict) -> str:
    """Identity of this exact revision of the advisory."""
    tracking = _as_dict(_as_dict(data.get("document")).get("tracking"))
    return hashlib.sha256(
        f"{version_key(data)}|{_text(tracking.get('version'))}|{_text(tracking.get('current_release_date'))}".encode(),
    ).hexdigest()


# --- rendering -----------------------------------------------------------------------------


def _paragraphs(text: str) -> str:
    """Escaped text as paragraphs; single line breaks are kept."""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if block.strip()]
    return "".join(f"<p>{escape(block).replace(chr(10), '<br>')}</p>" for block in blocks)


def _link(url: str, label: str | None = None) -> str:
    if not url.lower().startswith(("http://", "https://")):
        return escape(label or url)
    return f'<a href="{escape(url, quote=True)}">{escape(label or url)}</a>'


def _date(value: str) -> str:
    parsed = parse_datetime(value)
    return (
        parsed.strftime("%Y-%m-%d %H:%M UTC")
        if parsed and (parsed.hour or parsed.minute)
        else (parsed.strftime("%Y-%m-%d") if parsed else value)
    )


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _item(label: str, value: str) -> str:
    return f"<li><strong>{escape(label)}:</strong> {value}</li>" if value else ""


def _products(ids: Iterable[str], names: dict[str, str]) -> str:
    unique = list(dict.fromkeys(ids))
    shown = ", ".join(escape(names.get(product_id, product_id)) for product_id in unique[:MAX_PRODUCTS])
    more = len(unique) - MAX_PRODUCTS
    return f"{shown} (+{more} more)" if more > 0 else shown


def _render_metadata(data: dict) -> str:
    document = _as_dict(data.get("document"))
    tracking = _as_dict(document.get("tracking"))
    version = escape(_text(tracking.get("version")))
    status = _text(tracking.get("status"))
    items = [
        _item("ID", escape(_text(tracking.get("id")))),
        _item("Version", f"{version} ({escape(status)})" if status else version),
        _item("Initial release", escape(_date(_text(tracking.get("initial_release_date"))))),
        _item("Current release", escape(_date(_text(tracking.get("current_release_date"))))),
        _item("Publisher", escape(_text(_as_dict(document.get("publisher")).get("name")))),
        _item("Category", escape(category(data))),
        _item("TLP", escape(tlp_label(data))),
        _item("Aggregate severity", escape(_text(_as_dict(document.get("aggregate_severity")).get("text")))),
        _item("License", escape(_text(document.get("license_expression")))),
    ]
    return "<ul>" + "".join(items) + "</ul>"


def _render_notes(notes: object, *, nested: bool = False) -> str:
    """Notes, except legal disclaimers. Nested ones (a vulnerability's) get bold titles, not headings."""
    parts = []
    for note in map(_as_dict, _as_list(notes)):
        if note.get("category") == "legal_disclaimer" or not _text(note.get("text")):
            continue
        title = escape(_text(note.get("title")) or _humanize(_text(note.get("category")) or "note"))
        heading = f"<p><strong>{title}</strong></p>" if nested else f"<h4>{title}</h4>"
        parts.append(heading + _paragraphs(note["text"]))
    return "".join(parts)


def _render_vulnerability(vulnerability: dict, names: dict[str, str]) -> str:
    cve = _text(vulnerability.get("cve"))
    other_ids = [_text(_as_dict(entry).get("text")) for entry in _as_list(vulnerability.get("ids"))]
    label = cve or next((entry for entry in other_ids if entry), "") or "Vulnerability"
    title = _text(vulnerability.get("title"))
    heading = f"{escape(label)}: {escape(title)}" if title else escape(label)

    details = [_item("CWE", ", ".join(escape(f"{cwe_id} {name}".strip()) for cwe_id, name in cwes(vulnerability)))]
    for score in cvss_scores(vulnerability):
        value = " ".join(part for part in (str(score["score"]) if score["score"] is not None else "", escape(score["severity"])) if part)
        details.append(_item(f"CVSS {score['version']}", f"{value} <code>{escape(score['vector'])}</code>".strip()))
    details.extend(
        _item("EPSS", escape(f"probability {entry.get('probability', '?')}, percentile {entry.get('percentile', '?')}"))
        for entry in map(_as_dict, epss(vulnerability))
    )
    details.append(_item("Severity", escape(", ".join(qualitative_ratings(vulnerability)))))
    details.append(_item("Disclosed", escape(_date(disclosure_date(vulnerability)))))
    details.append(_item("Exploited since", escape(", ".join(_date(value) for value in exploitation_dates(vulnerability)))))

    status = _as_dict(vulnerability.get("product_status"))
    affected = [product for key in _AFFECTED for product in _as_list(status.get(key))]
    fixed = [product for key in _FIXED for product in _as_list(status.get(key))]
    details.append(_item("Affected", _products(affected, names)))
    details.append(_item("Fixed", _products(fixed, names)))
    details.append(_item("Under investigation", _products(_as_list(status.get("under_investigation")), names)))

    rendered = f"<h4>{heading}</h4><ul>{''.join(details)}</ul>"
    return rendered + _render_notes(vulnerability.get("notes"), nested=True)


def _render_remediations(vulnerabilities: list[dict]) -> str:
    """Every distinct remediation once, with the vulnerabilities it applies to.

    Advisories repeat the same remediation under each vulnerability and product (one
    Schneider Electric advisory does so 150 times), so it is listed once here.
    """
    applies_to: dict[tuple[str, str, str], list[str]] = {}
    for vulnerability in vulnerabilities:
        label = _text(vulnerability.get("cve")) or _text(vulnerability.get("title")) or "vulnerability"
        for remediation in map(_as_dict, _as_list(vulnerability.get("remediations"))):
            key = (_text(remediation.get("category")), _text(remediation.get("details")), _text(remediation.get("url")))
            if any(key):
                labels = applies_to.setdefault(key, [])
                if label not in labels:
                    labels.append(label)
    rows = []
    for (kind, details, url), labels in list(applies_to.items())[:MAX_REMEDIATIONS]:
        shown = ", ".join(escape(label) for label in labels[:MAX_PRODUCTS])
        if len(labels) > MAX_PRODUCTS:
            shown += f" (+{len(labels) - MAX_PRODUCTS} more)"
        link = f" ({_link(url)})" if url else ""
        rows.append(f"<li><strong>{escape(_humanize(kind or 'remediation'))}</strong> [{shown}]: {escape(details)}{link}</li>")
    if len(applies_to) > MAX_REMEDIATIONS:
        rows.append(f"<li>+{len(applies_to) - MAX_REMEDIATIONS} more</li>")
    return f"<h3>Remediations</h3><ul>{''.join(rows)}</ul>" if rows else ""


def render_content(data: dict, document_url: str) -> str:
    """The advisory as HTML, using only the tags news item content keeps.

    Every value from the document is escaped: it is untrusted text, and CSAF notes are plain
    text, where "versions < 2.1" must stay text.
    """
    document = _as_dict(data.get("document"))
    parts = []
    retracted = RETRACTED_CATEGORIES.get(category(data))
    if retracted:
        parts.append(f"<p><strong>This advisory is {retracted.lower()}.</strong></p>")
    parts.append(_render_metadata(data))
    parts.append(_render_notes(document.get("notes")))

    vulnerabilities = [_as_dict(vulnerability) for vulnerability in _as_list(data.get("vulnerabilities"))]
    if vulnerabilities:
        names = product_names(data)
        detailed = vulnerabilities
        if len(vulnerabilities) > MAX_DETAILED_VULNERABILITIES:
            detailed = sorted(vulnerabilities, key=top_score, reverse=True)
        parts.append(f"<h3>Vulnerabilities ({len(vulnerabilities)})</h3>")
        parts.extend(_render_vulnerability(vulnerability, names) for vulnerability in detailed[:MAX_DETAILED_VULNERABILITIES])
        remaining = detailed[MAX_DETAILED_VULNERABILITIES:]
        if remaining:
            listed = ", ".join(
                escape(f"{_text(v.get('cve')) or 'unnamed'}" + (f" ({top_score(v)})" if top_score(v) else "")) for v in remaining
            )
            parts.append(f"<h4>{len(remaining)} more vulnerabilities</h4><p>{listed}</p>")
        parts.append(_render_remediations(vulnerabilities))

    revisions = sorted(
        (_as_dict(revision) for revision in _as_list(_as_dict(document.get("tracking")).get("revision_history"))),
        key=lambda revision: parse_datetime(revision.get("date")) or datetime.datetime.min.replace(tzinfo=datetime.UTC),
        reverse=True,
    )
    if revisions:
        rows = "".join(
            f"<li>{escape(_text(str(revision.get('number', ''))))} &ndash; {escape(_date(_text(revision.get('date'))))}"
            + (f": {escape(_text(revision.get('summary')))}" if _text(revision.get("summary")) else "")
            + "</li>"
            for revision in revisions[:MAX_REVISIONS]
        )
        parts.append(f"<h3>Revision history</h3><ul>{rows}</ul>")

    references = [_as_dict(reference) for reference in _as_list(document.get("references")) if _text(_as_dict(reference).get("url"))]
    rows = [f"<li>{_link(reference['url'], _text(reference.get('summary')) or None)}</li>" for reference in references[:MAX_REFERENCES]]
    if len(references) > MAX_REFERENCES:
        rows.append(f"<li>+{len(references) - MAX_REFERENCES} more</li>")
    rows.append(f"<li>{_link(document_url, 'CSAF document (JSON)')}</li>")
    parts.append(f"<h3>References</h3><ul>{''.join(rows)}</ul>")
    return "".join(part for part in parts if part)


# --- news item -----------------------------------------------------------------------------


def _review(data: dict) -> str:
    notes = [_as_dict(note) for note in _as_list(_as_dict(data.get("document")).get("notes"))]
    for wanted in ("summary", "description"):
        text = next((_text(note.get("text")) for note in notes if note.get("category") == wanted and _text(note.get("text"))), "")
        if text:
            return text
    return _text(_as_dict(data.get("document")).get("title"))


def _link_of(data: dict, fallback: str) -> str:
    """The human-readable page of the advisory when the document names one, else the fallback."""
    references = [_as_dict(reference) for reference in _as_list(_as_dict(data.get("document")).get("references"))]
    own = [_text(reference.get("url")) for reference in references if reference.get("category") == "self" and _text(reference.get("url"))]
    return next((url for url in own if not url.lower().endswith(".json")), own[0] if own else fallback)


def attributes(data: dict, integrity: dict[str, str] | None = None) -> list[NewsItemAttribute]:
    """The structured facts as attributes, under the keys the extraction rules use.

    CVEs and CVSS vectors are not capped: every CVE of a large advisory stays searchable even
    though the text details only some.
    """
    pairs: list[tuple[str, str]] = []
    for vulnerability in map(_as_dict, _as_list(data.get("vulnerabilities"))):
        if _text(vulnerability.get("cve")):
            pairs.append(("CVE", _text(vulnerability["cve"]).upper()))
        pairs.extend(("CWE", cwe_id.upper()) for cwe_id, _name in cwes(vulnerability))
        pairs.extend(("CVSS", score["vector"]) for score in cvss_scores(vulnerability) if score["vector"])
    if tlp_label(data):
        pairs.append(("TLP", tlp_label(data)))
    pairs.extend((integrity or {}).items())
    return [NewsItemAttribute(key, value, "", "") for key, value in dict.fromkeys(pairs)]


def build_news_item(
    data: dict,
    document_url: str,
    source: object,
    integrity: dict[str, str] | None = None,
    page_url: str | None = None,
) -> NewsItemData:
    """Build the news item for one CSAF document.

    Args:
        data (dict): The parsed document.
        document_url (str): Where it was downloaded from.
        source (object): The OSINT source.
        integrity (dict | None): CSAF_HASH and CSAF_SIGNATURE results, when checked.
        page_url (str | None): A page showing the document to people, used as the link when
            the document names none of its own (a GitHub page instead of the raw file).

    Returns:
        NewsItemData
    """
    document = _as_dict(data.get("document"))
    tracking = _as_dict(document.get("tracking"))
    tracking_id = _text(tracking.get("id"))
    title = _text(document.get("title"))
    if tracking_id and not title.lower().startswith(tracking_id.lower()):
        title = f"{tracking_id}: {title}" if title else tracking_id
    retracted = RETRACTED_CATEGORIES.get(category(data))
    if retracted:
        title = f"[{retracted}] {title}"

    released = release_date(data)
    return NewsItemData(
        uuid.uuid4(),
        revision_hash(data),
        title,
        _review(data),
        getattr(source, "url", ""),
        _link_of(data, page_url or document_url),
        released.astimezone(TZ).strftime("%d.%m.%Y - %H:%M") if released else "",
        _text(_as_dict(document.get("publisher")).get("name")),
        datetime.datetime.now(TZ),
        render_content(data, document_url),
        getattr(source, "id", None),
        attributes(data, integrity),
        version=_text(tracking.get("version")) or None,
        version_key=version_key(data),
    )
