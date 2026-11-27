"""A client of MITRE's CVE Services API, as an organization's CNA account uses it.

CVE Services (https://cveawg.mitre.org/api-docs/) is where a CVE Numbering Authority reserves CVE
IDs and publishes, updates and rejects CVE records. Every call carries the account's three
credentials as headers, except reading a published record, which anyone may. Only what Taranis
needs is here:

- ``reserve()``: ``POST /cve-id``, one ID of a year;
- ``publish()`` / ``update()``: ``POST`` / ``PUT /cve/{id}/cna`` with the record's CNA container;
- ``reject()``: ``POST /cve/{id}/reject`` for an ID never published, ``PUT`` for a published one;
- ``id_state()``: ``GET /cve-id/{id}``, where an ID stands (to catch up after a lost answer);
- ``org_info()``: ``GET /org/{short_name}`` and its ID quota, to test the account;
- ``published_record()``: ``GET /cve/{id}`` without credentials, any CNA's published record, from
  the CVE Services data provider (``public_source()``).

Every failure becomes a ``CveServicesError`` whose message says what went wrong in words an
administrator can act on (the service's own message and details where it gives them).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import requests
from config import Config
from managers.log_manager import logger
from shared.gcve import CVE_SERVICES_API_TYPE, CVE_SERVICES_PUBLIC_URL

if TYPE_CHECKING:
    from model.cve_services_account import CveServicesAccount
    from model.data_provider import DataProvider

# Connect and read timeouts: CVE Services validates a record before it answers.
TIMEOUT = (3.05, 30)
# What is kept of a service message, and how many of its detail lines.
MAX_MESSAGE = 1500
MAX_DETAILS = 5
# Where an ID can stand at CVE Services (the ``state`` of ``GET /cve-id/{id}``).
ID_STATES = ("RESERVED", "PUBLISHED", "REJECTED")
# The largest published record read (a record listing every affected kernel version runs to a few MB).
MAX_RECORD_BYTES = 8 * 1024 * 1024


class CveServicesError(Exception):
    """A call to CVE Services that failed; the message says why."""

    def __init__(self, message: str, status: int | None = None) -> None:
        """Keep the HTTP status (None when the service did not answer)."""
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Credentials:
    """What a call needs: where, and as whom."""

    base_url: str
    short_name: str
    username: str
    api_key: str
    # The organization whose account it is (its CNA's UUID is kept with the account).
    organization_id: int | None = None

    @classmethod
    def of(cls, account: CveServicesAccount, api_key: str | None = None) -> Credentials:
        """The credentials of an account; ``api_key`` replaces the stored key (testing an unsaved form).

        Raises:
            CveServicesError: When the account is incomplete or its key cannot be read.
        """
        key = api_key or account.get_api_key()
        if not (account.short_name or "").strip() or not (account.username or "").strip():
            msg = "The CVE Services account needs the CNA short name and a user"
            raise CveServicesError(msg)
        if not key:
            msg = "The CVE Services account has no API key (or it cannot be decrypted: enter it again)"
            raise CveServicesError(msg)
        return cls(account.base_url.rstrip("/"), account.short_name.strip(), account.username.strip(), key, account.organization_id)

    def headers(self) -> dict[str, str]:
        """The authentication headers of every call."""
        return {
            "CVE-API-ORG": self.short_name,
            "CVE-API-USER": self.username,
            "CVE-API-KEY": self.api_key,
            "Accept": "application/json",
        }


def _details(details: object) -> list[str]:
    """The lines of a service error's ``details``: request parameter or schema problems."""
    lines: list[str] = []
    if isinstance(details, dict) and isinstance(details.get("errors"), list):
        details = details["errors"]
    if isinstance(details, list):
        for entry in details:
            if isinstance(entry, dict):
                where = entry.get("instancePath") or entry.get("param") or entry.get("path") or ""
                text = entry.get("message") or entry.get("msg") or ""
                lines.append(f"{where}: {text}" if where else str(text))
            else:
                lines.append(str(entry))
    elif details:
        lines.append(str(details))
    return [line for line in lines if line][:MAX_DETAILS]


def _error(response: requests.Response) -> CveServicesError:
    """What a refused call says, as one message."""
    status = response.status_code
    try:
        body = response.json()
    except ValueError:
        body = None
    message = ""
    details: list[str] = []
    if isinstance(body, dict):
        message = str(body.get("message") or body.get("error") or "")
        details = _details(body.get("details"))
    if status == HTTPStatus.UNAUTHORIZED:
        message = "CVE Services refused the credentials (check the CNA short name, the user and the API key)"
    elif status == HTTPStatus.FORBIDDEN and not message:
        message = "The CVE Services user may not do this (it needs the CNA's rights over this CVE ID)"
    elif not message:
        message = f"CVE Services answered HTTP {status}"
    text = "; ".join([message, *details])
    return CveServicesError(text[:MAX_MESSAGE], status)


def _call(credentials: Credentials, method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> Any:  # noqa: ANN401
    """One call; its JSON answer.

    Raises:
        CveServicesError: When the service cannot be reached or refuses the call.
    """
    url = f"{credentials.base_url}{path}"
    try:
        response = requests.request(
            method,
            url,
            headers=credentials.headers(),
            params=params,
            json=body,
            timeout=TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as error:
        logger.warning(f"CVE Services at {credentials.base_url} cannot be reached: {error}")
        msg = f"CVE Services cannot be reached at {credentials.base_url}"
        raise CveServicesError(msg) from error
    if not response.ok:
        error = _error(response)
        logger.warning(f"CVE Services {method} {path}: HTTP {response.status_code}: {error}")
        raise error
    try:
        return response.json()
    except ValueError:
        return {}


def reserve(credentials: Credentials, year: int) -> str:
    """Reserve one CVE ID of ``year`` for the CNA.

    Returns:
        str: The ID, e.g. ``CVE-2026-1234``.
    """
    answer = _call(
        credentials,
        "POST",
        "/cve-id",
        params={"amount": 1, "cve_year": year, "short_name": credentials.short_name},
    )
    ids = answer.get("cve_ids") if isinstance(answer, dict) else None
    cve_id = ids[0].get("cve_id") if isinstance(ids, list) and ids and isinstance(ids[0], dict) else None
    if not cve_id:
        msg = "CVE Services reserved no CVE ID"
        raise CveServicesError(msg)
    return str(cve_id)


def publish(credentials: Credentials, cve_id: str, container: dict) -> None:
    """Publish the record of a reserved ID: its CNA container."""
    _call(credentials, "POST", f"/cve/{cve_id}/cna", body={"cnaContainer": container})


def update(credentials: Credentials, cve_id: str, container: dict) -> None:
    """Replace the CNA container of a published record."""
    _call(credentials, "PUT", f"/cve/{cve_id}/cna", body={"cnaContainer": container})


def reject(credentials: Credentials, cve_id: str, reason: str, *, published: bool, org_uuid: str | None = None) -> None:
    """Reject an ID: ``POST`` while it has no record, ``PUT`` to turn a published record into a rejected one."""
    container: dict[str, Any] = {"rejectedReasons": [{"lang": "en", "value": reason}]}
    if org_uuid:
        container["providerMetadata"] = {"orgId": org_uuid}
    _call(credentials, "PUT" if published else "POST", f"/cve/{cve_id}/reject", body={"cnaContainer": container})


def id_state(credentials: Credentials, cve_id: str) -> str:
    """Where an ID stands at CVE Services now: RESERVED, PUBLISHED or REJECTED.

    Raises:
        CveServicesError: When CVE Services cannot be asked, or does not say.
    """
    answer = _call(credentials, "GET", f"/cve-id/{cve_id}")
    state = answer.get("state") if isinstance(answer, dict) else None
    if state not in ID_STATES:
        msg = f"CVE Services did not say where {cve_id} stands"
        raise CveServicesError(msg)
    return str(state)


def org_info(credentials: Credentials) -> dict:
    """What CVE Services says about the CNA: its name, UUID and ID quota (testing the account)."""
    org = _call(credentials, "GET", f"/org/{credentials.short_name}")
    quota = _call(credentials, "GET", f"/org/{credentials.short_name}/id_quota")
    org = org if isinstance(org, dict) else {}
    quota = quota if isinstance(quota, dict) else {}
    return {
        "name": org.get("name") or credentials.short_name,
        "short_name": org.get("short_name") or credentials.short_name,
        "uuid": org.get("UUID") or org.get("uuid"),
        "roles": (org.get("authority") or {}).get("active_roles") or [],
        "id_quota": quota.get("id_quota"),
        "total_reserved": quota.get("total_reserved"),
        "available": quota.get("available"),
    }


@dataclass(frozen=True)
class PublicSource:
    """Where published records are read, and as whom."""

    base_url: str
    user_agent: str | None = None


def _cve_services_provider() -> DataProvider | None:
    """The CVE Services data provider (the first one, if an admin added more); None when there is none."""
    from model.data_provider import DataProvider  # noqa: PLC0415 - the client is imported by models, not the other way round

    return DataProvider.query.filter_by(api_type=CVE_SERVICES_API_TYPE).order_by(DataProvider.id).first()


def public_source() -> PublicSource:
    """Where published records are read.

    ``TARANIS_CVE_SERVICES_URL`` first (a test stub, as for the CNA accounts), then the CVE Services
    data provider (seeded with MITRE's public API, an admin may point it at a mirror), and MITRE's
    public API when there is no such provider.
    """
    if Config.CVE_SERVICES_URL:
        return PublicSource(Config.CVE_SERVICES_URL.rstrip("/"))
    provider = _cve_services_provider()
    if provider is not None and (provider.api_url or "").strip():
        return PublicSource(provider.api_url.strip().rstrip("/"), (provider.user_agent or "").strip() or None)
    return PublicSource(CVE_SERVICES_PUBLIC_URL.rstrip("/"))


def published_record(cve_id: str) -> dict:
    """The published record of a CVE ID, whichever CNA assigned it (no account needed).

    Raises:
        CveServicesError: When CVE Services cannot be reached, has no published record of the ID,
            or answers with something that is not one.
    """
    source = public_source()
    base_url = source.base_url
    url = f"{base_url}/cve/{cve_id}"
    headers = {"Accept": "application/json"}
    if source.user_agent:
        headers["User-Agent"] = source.user_agent
    try:
        with requests.get(url, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=False) as response:
            if response.status_code == HTTPStatus.NOT_FOUND:
                msg = f"CVE Services has no published record of {cve_id}"
                raise CveServicesError(msg, response.status_code)
            if not response.ok:
                raise _error(response)
            body = response.raw.read(MAX_RECORD_BYTES + 1, decode_content=True)
    except requests.RequestException as error:
        logger.warning(f"CVE Services at {base_url} cannot be reached: {error}")
        msg = f"CVE Services cannot be reached at {base_url}"
        raise CveServicesError(msg) from error
    if len(body) > MAX_RECORD_BYTES:
        msg = f"The record of {cve_id} is larger than {MAX_RECORD_BYTES // (1024 * 1024)} MB"
        raise CveServicesError(msg)
    try:
        record = json.loads(body)
    except ValueError as error:
        msg = f"CVE Services answered with something that is not a record of {cve_id}"
        raise CveServicesError(msg) from error
    if not isinstance(record, dict) or not isinstance(record.get("containers"), dict):
        msg = f"CVE Services answered with something that is not a record of {cve_id}"
        raise CveServicesError(msg)
    return record
