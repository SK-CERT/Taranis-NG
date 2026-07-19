"""Report item processing for public-web.

This module provides classes for processing vulnerability report items from Taranis.
"""

# pylint: disable=missing-function-docstring

import logging
import re
from enum import Enum
from typing import Any

from cvss import CVSS2, CVSS3, CVSS4
from lib import handle_exception, version_parser
from lib.report import (
    MissingFieldError,
    capitalize,
    fix_spaces,
    format_iso_date,
    reformat_date,
)


class EventsGeneration(Enum):
    """Enum for values representing if IDEA events should be generated from the report or not."""

    DISABLED = 1
    TEST = 2
    GENERATE = 3


class VulnerabilityReportPart:
    """Generic part of a vulnerability report from Taranis-NG core public-web API.

    Built from a report item dict with a flat list of attributes
    ({"key", "value", "description"}). Attributes with the same key are grouped into lists.
    """

    def __init__(self, item: dict[str, Any]) -> None:
        """Initialize the report part.

        Args:
            item: The report item dictionary.
        """
        self.item = item
        self._attrs: dict[str, list[dict[str, Any]]] = {}
        for attribute in item.get("attributes") or []:
            key = (attribute.get("key") or "").strip()
            self._attrs.setdefault(key, []).append(
                {"value": attribute.get("value"), "description": attribute.get("description")},
            )
        self.validate()

    def validate(self) -> None:
        """Validate the report item."""
        if self.item.get("attributes") is None:
            msg = "Attributes field is missing in the report item!"
            raise ValueError(msg)
        # These methods will fail if something is missing.
        self.get_name()
        self.get_description()

    def _get(
        self,
        field: str,
        invalid_value: dict[str, Any] | None = None,
        required: bool = False,
    ) -> dict[str, Any] | str | None:
        """Helper method for getting 'field' from the report item.

        'Invalid_value' specifies what to return if the field is missing.
        If required is True, Error is thrown if the field is missing.

        Args:
            field: The field name to get.
            invalid_value: Value to return if field is missing.
            required: Whether the field is required.

        Returns:
            The field value or invalid_value.
        """
        if self.item.get(field) is None and required:
            raise MissingFieldError(field, self)
        return self.item.get(field, invalid_value)

    def _attr_values(self, key: str) -> list[str]:
        """Returns all values of the attribute with the given key.

        Returns empty list if the attribute is not present.
        """
        return [attr["value"] for attr in self._attrs.get(key, []) if attr["value"] is not None]

    def _attr_first(
        self,
        key: str,
        invalid_value: dict[str, Any] | None = None,
        required: bool = False,
    ) -> dict[str, Any] | str | None:
        """Returns the first value of the attribute with the given key.

        'Invalid_value' specifies what to return if the attribute is missing.
        If required is True, Error is thrown if the attribute is missing.
        """
        values = self._attr_values(key)
        if not values:
            if required:
                raise MissingFieldError(key, self)
            return invalid_value
        return values[0]

    def _set_attr_value(self, key: str, index: int, value: str) -> None:
        """Replaces the attribute value at the given index.

        Used for link renumbering; operates on this object only, not on the source data.
        """
        self._attrs[key][index]["value"] = value

    def get_name(self) -> str:
        """Get the name of the report part."""
        return fix_spaces(
            self._get("title", required=True),
        )

    def get_created(self) -> str | None:
        """Get the created date of the report part."""
        created = self.item.get("created")
        if created is None:
            return None
        return format_iso_date(created)

    def get_last_updated(self) -> str | None:
        """Get the last updated date of the report part."""
        last_updated = self.item.get("last_updated")
        if last_updated is None:
            return None
        return format_iso_date(last_updated)

    def get_description(self) -> str:
        """Get the description of the report part."""
        return fix_spaces(
            self._attr_first("description", required=True),
        )

    def get_recommendations(self) -> str | None:
        """Get the recommendations of the report part."""
        if (recommendations := self._attr_first("recommendations")) is None:
            return None
        return capitalize(fix_spaces(recommendations))

    def get_links(self) -> list[str]:
        """Get the links of the report part."""
        return self._attr_values("links")

    def renumber_links(self, product_links: list[str]) -> None:
        """Replaces link references in the description and recommendations.

        So that they point to the indices in the report-wide product_links
        list instead of this part's own links list.
        """
        report_links = self.get_links()
        if not report_links:
            return
        mapping = {old_index + 1: product_links.index(link) + 1 for old_index, link in enumerate(report_links) if link in product_links}

        def replace_match(match: re.Match) -> str:
            old_index = int(match.group(1))
            new_index = mapping.get(old_index, old_index)
            return f"[{new_index}]"

        for key in ("description", "recommendations"):
            for i, attr in enumerate(self._attrs.get(key, [])):
                if attr["value"]:
                    self._set_attr_value(key, i, re.sub(r"\[(\d+)\]", replace_match, attr["value"]))


class VulnerabilityReportIntro(VulnerabilityReportPart):
    """This class represents Vulnerability Report - Intro from Taranis."""

    def should_generate_events(self) -> EventsGeneration:
        """Check if events should be generated from the intro."""
        value = self._attr_first("generate_events")
        if value == "generate":
            return EventsGeneration.GENERATE
        if value == "do not generate":
            return EventsGeneration.DISABLED
        return EventsGeneration.TEST


class ReportItem(VulnerabilityReportPart):
    """This class represents Report Item from Taranis."""

    def __init__(self, item: dict[str, Any]) -> None:
        """Initialize a new Report Item.

        Args:
            item: The report item dictionary.
        """
        super().__init__(item)
        self.search_in_sner = self.validate_versions()

    def _should_parse_versions(self) -> bool:
        """Returns if the version specification should be parsed.

        If the version is not parsed, the app will not try to find the vulnerability in Sner.
        """
        # If the value is missing, assume that it should be parsed.
        return self._attr_first("affected_versions_parsability", "Parse").lower() == "parse"

    def validate(self) -> None:
        """Basic report item validation from the input JSON.

        Mostly just if the field is there, not if the content is correct.
        """
        super().validate()
        self.get_affected_systems()
        if self.get_CVEs():
            for cve in self.get_CVEs():
                if cve and not re.fullmatch(r"CVE-\d{4}-\d{4,7}", cve):
                    msg = f"CVE '{cve}' has wrong format."
                    raise ValueError(msg)
        if self.get_CWEs():
            for cwe in self.get_CWEs():
                if cwe and not re.fullmatch(r"\d+", cwe):
                    msg = f"CWE '{cwe}' has wrong format."
                    raise ValueError(msg)

    def validate_versions(
        self,
        send_mail: bool = False,
        logger: logging.Logger | None = None,
    ) -> bool:
        """Tries to parse the version specification.

        If it fails, an info mail is sent (if send_mail is True).
        Returns True if all versions are valid, and False if one or more versions are invalid.
        """
        if not self._should_parse_versions():
            return False

        try:
            for i in range(1, len(self.get_affected_systems()) + 1):
                versions = self.get_versions(i)
                if versions:
                    version_parser.parse(versions)  # check if it can be parsed
            return True
        except version_parser.InvalidFormatError:
            message = (
                f"The app was unable to parse the version specifier from "
                f"the report item {self.get_name()}. Make sure the version "
                f"specification is correct. Until this problem is resolved, "
                f"the app will not search in Sner for the vulnerable services "
                f"described in this report."
            )
            subject = "[public-web] Unable to parse version specification"
            if send_mail:
                handle_exception(message, subject, logger, force_send=False)
            return False

    def should_search(self) -> bool:
        """Returns if this vulnerability should be searched in Sner."""
        return self.search_in_sner

    def get_description(self) -> str:
        """Get the description of the report item."""
        return capitalize(super().get_description())

    def get_CVEs(self) -> list[str]:  # noqa: N802
        """Get the CVEs of the report item."""
        return [cve.strip() for cve in self._attr_values("cve")]

    def get_CWEs(self) -> list[str]:  # noqa: N802
        """Get the CWEs of the report item."""
        return [cwe.strip() for cwe in self._attr_values("cwe")]

    def get_cwe_name(self, index: int) -> str | None:
        """Get the name of the CWE on index, which starts at number 1.

        The name is taken from the Taranis CWE dictionary (stored as the attribute's description).
        Returns None if there is no name for that CWE.
        """
        cwe_attrs = self._attrs.get("cwe", [])
        if len(cwe_attrs) < index:
            return None
        return cwe_attrs[index - 1].get("description") or None

    def get_iocs(self) -> str | None:
        """Get the IOCs of the report item."""
        # IOCs are in a form of a list, so they need to be joined into 1 string.
        return ", ".join(self._attr_values("ioc")) or None

    def get_cvss(self) -> str | None:
        """Get the CVSS score of the report item."""
        return self._attr_first("cvss")

    def get_cvss_vector(self) -> str | None:
        """Get the CVSS vector of the report item."""
        cvss = self.get_cvss()
        if cvss and "/" in cvss:
            return cvss.strip()
        return None

    def get_cvss_number(self) -> float | None:
        """Returns the CVSS base score.

        The attribute value is either a CVSS vector (parsed with the cvss library) or a plain number.
        """
        value = self.get_cvss()
        if not value:
            return None
        value = value.strip()
        try:
            if value.startswith("CVSS:3."):
                return float(CVSS3(value).as_json()["baseScore"])
            if value.startswith("CVSS:4.0/"):
                return float(CVSS4(value).as_json()["baseScore"])
            if "/" in value:
                return float(CVSS2(value).as_json()["baseScore"])
            return float(value)
        except Exception:  # pylint: disable=locally-disabled, broad-exception-caught
            return None

    def get_update_date(self) -> str | None:
        """Get the update date of the report item."""
        date = self._attr_first("update_date")
        if not date or len(date.split(".")) != 3:  # noqa: PLR2004
            return None
        return reformat_date(date)

    def get_exposure_date(self) -> str | None:
        """Get the exposure date of the report item."""
        date = self._attr_first("exposure_date", required=True)
        if not date or len(date.split(".")) != 3:  # noqa: PLR2004
            return None
        return reformat_date(date)

    def get_affected_systems(self) -> list[str]:
        """Get the affected systems of the report item."""
        if "affected_systems" not in self._attrs:
            msg = "affected_systems"
            raise MissingFieldError(msg, self)
        return self._attr_values("affected_systems")

    def get_affected_system(self, index: int) -> str | None:
        """Get the affected system at index 'index', starting from 1."""
        systems = self.get_affected_systems()
        if index > len(systems):  # Out of range.
            return None
        return systems[index - 1]

    def _get_product_part(self, index: int) -> str | None:
        """Get the product part of the affected system at index 'index', starting from 1.

        If the index is less than 1, ValueError is raised.
        """
        if index < 1:
            msg = f"Index must start from one, but was {index}."
            raise ValueError(msg)
        system = self.get_affected_system(index)
        if not system or not system.strip():
            return None
        if ";" not in system:  # Version was not specified ("product;" format).
            return system
        # Version was specified. ("product; versions" format).
        return system[: system.index(";")]

    def get_product_and_OS_specification(self, index: int) -> tuple[str, str] | None:  # noqa: N802
        """Get a tuple of product and OS specification of the affected system.

        At index 'index', starting from 1.
        """
        product = self._get_product_part(index)
        if product is None:
            return None
        if ":" not in product:  # Format without OS specification
            return product.strip(), ""
        product_parts = product.split(":", maxsplit=2)
        return product_parts[1].strip(), product_parts[0].strip().lower()

    def get_product_display(self, index: int) -> str | None:
        """Get a string representation of product and OS specification.

        Of the affected system at index 'index', starting from 1.
        """
        result = self.get_product_and_OS_specification(index)
        if result is None:
            return None
        product, os_spec = result
        # "*" is just internal symbol for SNER.
        if os_spec in ["", "*"]:
            return product
        return f"{product} ({os_spec})"

    def get_versions(self, index: int) -> str | None:
        """Get the version of the affected system at index 'index', starting from 1.

        If the index is less than 1, ValueError is raised.
        """
        if index < 1:
            msg = f"Index must start from one, but was {index}."
            raise ValueError(msg)
        system = self.get_affected_system(index)
        # If no version was specified.
        if not system or not system.strip() or ";" not in system:
            return None
        system = system.strip()
        if len(system) == system.index(";"):  # No version was specified.
            return None
        # Remove the product from the string
        versions = system[(system.index(";") + 1) :].strip()
        # If there is an extra ";" at the end, remove it.
        if len(versions) > 0 and versions[-1] == ";":
            versions = versions[:-1]
        return versions

    def get_formatted_versions(self, index: int) -> str | None:
        """Get the affected version of affected system at index 'index', starting from 1.

        And parse it into human-readable form with OR/AND and brackets.
        """
        versions = self.get_versions(index)
        if not versions:
            return None
        result = ""
        version_parts = versions.split(";")
        if len(version_parts) == 1:
            return version_parts[0].replace(",", " AND ").strip()

        for i, version_specifier in enumerate(version_parts):
            result += "(" + version_specifier.replace(",", " AND ").strip() + ")"
            if i < len(version_parts) - 1:
                result += " OR "
        return result
