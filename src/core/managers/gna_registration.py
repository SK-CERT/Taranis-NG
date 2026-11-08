"""What a web publishing an organization's GCVE records serves, and whether it answers.

A GNA registers its publication at gcve.eu: the GNA directory (managers.gna_directory) then lists
its website (``gcve_url``), its pull API (``gcve_pull_api``) and its dumps (``gcve_dump``). This
compares what the webs publishing the organization's records serve with what the directory lists,
and asks each endpoint of a web (GCVE-BCP-03, GCVE-BCP-06) whether it answers as it should, the
way a GCVE consumer would: over HTTPS, without redirects.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import requests

from shared import gcve

if TYPE_CHECKING:
    from model.organization_gna import OrganizationGna
    from model.public_web import PublicWeb

PROBE_TIMEOUT = (3.05, 10)
PROBE_BYTES = 512 * 1024
PROBED = ("publication", "dump", "conformance", "security_txt")
JSON_TYPES = ("application/json",)


def _same(left: str | None, right: str | None) -> bool:
    return bool(left and right) and left.strip().rstrip("/").lower() == right.strip().rstrip("/").lower()


def web_urls(web: PublicWeb, gna: OrganizationGna | None) -> list[dict]:
    """What a web serves for the GNA, ``{key, field, url, registered, matches}``.

    ``registered`` is what the GNA directory lists for ``field`` (None: nothing, or not a
    directory field); ``matches`` whether it is this web's address.
    """
    if gna is None or not (web.hostname or "").strip():
        return []
    entry = gna.directory or {}
    security_txt = bool(str((web.config or {}).get("security_contact") or "").strip())
    urls = []
    for url in gcve.registration_urls(web.hostname, gna.gna_id, security_txt=security_txt):
        registered = entry.get(url.field) if url.field else None
        urls.append({"key": url.key, "field": url.field, "url": url.url, "registered": registered, "matches": _same(url.url, registered)})
    return urls


def _read(url: str) -> tuple[requests.Response, bytes, bool]:
    """GET ``url`` without redirects; the response, at most PROBE_BYTES of its body, and whether it was cut."""
    with requests.get(url, timeout=PROBE_TIMEOUT, stream=True, allow_redirects=False, headers={"Accept": "*/*"}) as response:
        body = response.raw.read(PROBE_BYTES + 1, decode_content=True)
    return response, body[:PROBE_BYTES], len(body) > PROBE_BYTES


def _unreachable(error: requests.RequestException) -> str:
    """Why an endpoint could not be asked, in a few words."""
    if isinstance(error, requests.Timeout):
        return "not reachable from Taranis: no answer in time"
    if isinstance(error, requests.exceptions.SSLError):
        return "not reachable from Taranis: its TLS certificate was not accepted"
    if isinstance(error, requests.ConnectionError):
        return "not reachable from Taranis: the name does not resolve or the connection was refused"
    return f"not reachable from Taranis: {type(error).__name__}"


def probe(key: str, url: str) -> dict:
    """Ask one endpoint: ``{key, url, ok, status, detail}``; ``detail`` says what came back, or what is wrong."""
    try:
        response, body, cut = _read(url)
    except requests.RequestException as error:
        return {"key": key, "url": url, "ok": False, "status": None, "detail": _unreachable(error)}
    status = response.status_code
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    result = {"key": key, "url": url, "ok": False, "status": status, "detail": ""}
    if 300 <= status < 400:  # noqa: PLR2004
        result["detail"] = f"redirects to {response.headers.get('Location') or '?'}; GCVE consumers do not follow redirects"
        return result
    if status != 200:  # noqa: PLR2004
        result["detail"] = f"HTTP {status}"
        return result
    if key in ("publication", "conformance"):
        if content_type not in JSON_TYPES:
            result["detail"] = f"served as {content_type or 'nothing'}, not JSON"
            return result
        if cut:
            result.update(ok=key == "publication", detail="more than can be read here")
            return result
        try:
            payload = json.loads(body)
        except ValueError:
            result["detail"] = "not JSON"
            return result
        if key == "publication":
            if not isinstance(payload, list):
                result["detail"] = "not a list of records"
                return result
            result.update(ok=True, detail=f"{len(payload)} records on the first page")
        else:
            result.update(ok=isinstance(payload, dict), detail="a conformance document" if isinstance(payload, dict) else "not an object")
        return result
    if key == "dump":
        lines = sum(1 for line in body.splitlines() if line.strip())
        result.update(ok=True, detail=f"{lines}{' or more' if cut else ''} records")
        if content_type != "application/x-ndjson":
            result["detail"] += f", served as {content_type or 'nothing'}"
        return result
    text = body.decode("utf-8", errors="replace")
    contact = any(line.lower().startswith("contact:") for line in text.splitlines())
    result.update(ok=contact, detail="names a contact" if contact else "names no contact")
    return result


def check_web(web: PublicWeb, gna: OrganizationGna) -> dict:
    """Ask every endpoint of a web: ``{web_id, hostname, results: [probe ...]}``."""
    results = [probe(url["key"], url["url"]) for url in web_urls(web, gna) if url["key"] in PROBED]
    return {"web_id": web.id, "hostname": web.hostname, "results": results}
