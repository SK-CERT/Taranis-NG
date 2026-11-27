"""The types of the products a web shows - their product presets - which the homepage and the feeds split them by.

A web showing products of several types (e.g. its regular reports and the GCVE Advisories it
publishes) offers a tab for each, beside "All", and a feed for each. A type is named by its
product's preset: its ``key`` when it has one (the shipped presets, e.g. ``gcve``), which stays
the same everywhere, else its id. Keys are words and ids numbers, so they never clash. A product
from a core that does not say its preset has no type: it shows under "All" only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def type_of(report: dict) -> str | None:
    """The type of a report (``?type=``): its preset's key, else its id; None when it has no preset."""
    preset = report.get("product_preset") or {}
    if preset.get("key"):
        return str(preset["key"])
    if preset.get("id") is not None:
        return str(preset["id"])
    return None


def report_types(reports: Iterable[dict]) -> list[dict[str, str]]:
    """The types of these reports, ``{"id", "title"}``, each once, by title; untitled presets are left out."""
    found: dict[str, str] = {}
    for report in reports:
        type_id = type_of(report)
        title = str((report.get("product_preset") or {}).get("title") or "").strip()
        if type_id is not None and title and type_id not in found:
            found[type_id] = title
    kinds = [{"id": type_id, "title": title} for type_id, title in found.items()]
    return sorted(kinds, key=lambda kind: (kind["title"].casefold(), kind["id"]))


def find_type(reports: Iterable[dict], type_id: str | None) -> dict[str, str] | None:
    """The type ``type_id`` names among these reports' types; None when none does."""
    if not type_id:
        return None
    return next((kind for kind in report_types(reports) if kind["id"] == type_id), None)


def of_type(reports: Iterable[dict], type_id: str) -> list[dict]:
    """The reports of one type, in their order."""
    return [report for report in reports if type_of(report) == type_id]
