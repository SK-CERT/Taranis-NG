"""An organization's GCVE and CVE publishing: its GNA, its CVE Services account, and its webs.

Edited with the organization (Configuration -> Organizations -> GCVE & CVE):

- the GNA number gcve.eu allocated; its short and full name come from the GNA directory (see
  managers.gna_directory), checked when the number is saved and on request;
- the licence its records are published under, and what its conformance document adds;
- its CVE Services account (a CNA's credentials). The API key is write-only: the account answers
  with ``has_secret`` instead, and saving it with an empty key keeps the stored one. "Test
  connection" calls CVE Services with the form as it is, saved or not, and on success remembers the
  CNA's UUID (its records name it);
- and, read only, the webs publishing its records with what to register at gcve.eu, which a check
  compares with the directory and asks the endpoints of.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING

from flask import request
from flask_restful import Resource
from managers import cve_services, gna_directory, gna_registration, log_manager
from managers.auth_manager import auth_required, get_user_from_jwt
from managers.cve_services import Credentials, CveServicesError
from managers.db_manager import db
from model.cve_services_account import CveServicesAccount
from model.organization import Organization
from model.organization_gna import GnaSettingsError, OrganizationGna
from model.public_web import PublicWeb
from shared.gcve import CVE_ENVIRONMENTS

if TYPE_CHECKING:
    from flask_restful import Api

MAX_FIELD = 255


def _json() -> dict:
    return request.json if request.is_json and isinstance(request.json, dict) else {}


def _cve_form(data: object) -> tuple[dict, str | None]:
    """The CVE Services account fields of a request, and why they are not acceptable (None when they are)."""
    data = data if isinstance(data, dict) else {}
    form = {
        "environment": str(data.get("environment") or "test"),
        "short_name": str(data.get("short_name") or "").strip(),
        "username": str(data.get("username") or "").strip(),
        "api_key": str(data.get("api_key") or "").strip() or None,
    }
    if form["environment"] not in CVE_ENVIRONMENTS:
        return form, f"The environment is one of: {', '.join(CVE_ENVIRONMENTS)}"
    if len(form["short_name"]) > MAX_FIELD or len(form["username"]) > MAX_FIELD:
        return form, "The CNA short name and the user are at most 255 characters"
    return form, None


def _gna_form(data: object) -> tuple[dict, str | None]:
    """The GNA fields of a request, and why they are not acceptable (None when they are)."""
    data = data if isinstance(data, dict) else {}
    raw_number = data.get("gna_id")
    number = None
    if raw_number not in (None, ""):
        text = str(raw_number).strip()
        if not text.isdigit():
            return {}, "The GNA number is a whole number"
        number = int(text)
    conformance = data.get("conformance")
    if isinstance(conformance, str):
        try:
            conformance = json.loads(conformance) if conformance.strip() else None
        except ValueError:
            return {}, "The conformance details are a JSON object"
    if conformance is not None and not isinstance(conformance, dict):
        return {}, "The conformance details are a JSON object"
    license_name = data.get("records_license")
    return {"gna_id": number, "records_license": str(license_name) if license_name is not None else None, "conformance": conformance}, None


def _webs(organization_id: int) -> list[PublicWeb]:
    return sorted(
        (web for web in PublicWeb.query.all() if web.gcve_organization_id == organization_id),
        key=lambda web: (web.name or "", web.id),
    )


def _payload(organization: Organization, checks: list[dict] | None = None) -> dict:
    """What the organization's GCVE & CVE settings show."""
    gna = OrganizationGna.for_organization(organization.id)
    account = CveServicesAccount.get(organization.id) or CveServicesAccount(
        organization_id=organization.id,
        environment="test",
        short_name="",
        username="",
    )
    payload = {
        "organization_id": organization.id,
        "gna": gna.to_json() if gna is not None else None,
        "cve_services": account.to_json(),
        "directory": gna_directory.status(gna_directory.directory()),
        "webs": [
            {
                "id": web.id,
                "name": web.name,
                "hostname": web.hostname,
                "enabled": bool(web.enabled),
                "urls": gna_registration.web_urls(web, gna),
            }
            for web in _webs(organization.id)
        ],
    }
    if checks is not None:
        payload["checks"] = checks
    return payload


def _organization(organization_id: int) -> Organization | None:
    return Organization.find(organization_id)


class OrganizationGcveResource(Resource):
    """The organization's GNA and CVE Services account."""

    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    def get(self, organization_id: int) -> tuple[dict, HTTPStatus]:
        """The organization's GNA, its CVE Services account (never with its API key), and its webs.

        Returns:
            (dict, HTTPStatus): ``{organization_id, gna, cve_services, directory, webs}``.
        """
        organization = _organization(organization_id)
        if organization is None:
            return {"error": "Organization not found"}, HTTPStatus.NOT_FOUND
        return _payload(organization), HTTPStatus.OK

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id: int) -> tuple[dict, HTTPStatus]:
        """Save the organization's GNA (``gna``) and CVE Services account (``cve_services``).

        A GNA without a number is removed; an empty API key keeps the stored one. The GNA number is
        checked against the GNA directory at once.

        Returns:
            (dict, HTTPStatus): What the settings show now, or why they were refused (400, or 409 for
                a GNA number another organization holds or identifiers were allocated with).
        """
        organization = _organization(organization_id)
        if organization is None:
            return {"error": "Organization not found"}, HTTPStatus.NOT_FOUND
        data = _json()
        user = get_user_from_jwt()
        gna = None
        if "gna" in data:
            form, problem = _gna_form(data.get("gna"))
            if problem is not None:
                return {"error": problem}, HTTPStatus.BAD_REQUEST
            try:
                gna = OrganizationGna.save(organization_id, form["gna_id"], form["records_license"], form["conformance"], user.name)
            except GnaSettingsError as error:
                db.session.rollback()
                return {"error": str(error)}, HTTPStatus.CONFLICT if error.conflict else HTTPStatus.BAD_REQUEST
        else:
            gna = OrganizationGna.for_organization(organization_id)
        account = None
        if isinstance(data.get("cve_services"), dict):
            form, problem = _cve_form(data["cve_services"])
            if problem is not None:
                db.session.rollback()
                return {"error": problem}, HTTPStatus.BAD_REQUEST
            stored = CveServicesAccount.get(organization_id)
            if stored is not None or form["short_name"] or form["username"] or form["api_key"]:
                account = CveServicesAccount.save(
                    organization_id,
                    form["environment"],
                    form["short_name"],
                    form["username"],
                    form["api_key"],
                    user.name,
                )
        if gna is not None:
            db.session.flush()
            gna_directory.check_organization(gna, gna_directory.directory())
        db.session.commit()

        details = [f"GNA {gna.gna_id}" if gna is not None else "no GNA"]
        if account is not None:
            details.append(f"CVE Services {account.environment}, CNA {account.short_name}, user {account.username}")
        log_manager.store_user_activity(user, "ORGANIZATION_GCVE_UPDATE", f"Organization '{organization.name}': {'; '.join(details)}")
        if _webs(organization_id):
            gna_directory.notify_public_webs()
        return _payload(organization), HTTPStatus.OK


class OrganizationGcveCheckResource(Resource):
    """Check the organization's GNA against the directory, and the endpoints of its webs."""

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def post(self, organization_id: int) -> tuple[dict, HTTPStatus]:
        """Download the GNA directory again, copy the GNA's entry, and ask each web's endpoints.

        Returns:
            (dict, HTTPStatus): The settings as GET gives them, with ``checks``: per web,
                ``{web_id, hostname, results: [{key, url, ok, status, detail}]}``.
        """
        organization = _organization(organization_id)
        if organization is None:
            return {"error": "Organization not found"}, HTTPStatus.NOT_FOUND
        gna = OrganizationGna.for_organization(organization_id)
        if gna is None:
            return {"error": "The organization has no GNA number"}, HTTPStatus.BAD_REQUEST
        if gna_directory.check_organization(gna, gna_directory.directory(force=True)):
            db.session.commit()
            gna_directory.notify_public_webs()
        else:
            db.session.commit()
        checks = [gna_registration.check_web(web, gna) for web in _webs(organization_id) if web.enabled]
        return _payload(organization, checks), HTTPStatus.OK


class OrganizationCveServicesTestResource(Resource):
    """Try the organization's CVE Services account out."""

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def post(self, organization_id: int) -> tuple[dict, HTTPStatus]:
        """Ask CVE Services about the CNA with the form's credentials (an empty key: the stored one).

        Returns:
            (dict, HTTPStatus): ``{name, short_name, uuid, roles, id_quota, total_reserved, available}``,
            or why it failed (400 for an incomplete form, 502 when CVE Services refused).
        """
        if _organization(organization_id) is None:
            return {"error": "Organization not found"}, HTTPStatus.NOT_FOUND
        form, problem = _cve_form(_json())
        if problem is not None:
            return {"error": problem}, HTTPStatus.BAD_REQUEST
        stored = CveServicesAccount.get(organization_id)
        probe = CveServicesAccount(
            organization_id=organization_id,
            environment=form["environment"],
            short_name=form["short_name"],
            username=form["username"],
        )
        probe.api_key = stored.api_key if stored is not None else None
        try:
            credentials = Credentials.of(probe, form["api_key"])
        except CveServicesError as error:
            return {"error": str(error)}, HTTPStatus.BAD_REQUEST
        try:
            info = cve_services.org_info(credentials)
        except CveServicesError as error:
            return {"error": str(error)}, HTTPStatus.BAD_GATEWAY
        # The saved account is this one: remember its UUID, which every record names.
        if stored is not None and info.get("uuid") and stored.short_name == form["short_name"] and stored.environment == form["environment"]:
            stored.org_uuid = str(info["uuid"])
            db.session.commit()
        return info, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Register the organization GCVE & CVE endpoints."""
    api.add_resource(OrganizationGcveResource, "/api/v1/config/organizations/<int:organization_id>/gcve")
    api.add_resource(OrganizationGcveCheckResource, "/api/v1/config/organizations/<int:organization_id>/gcve/check")
    api.add_resource(OrganizationCveServicesTestResource, "/api/v1/config/organizations/<int:organization_id>/cve-services/test")
