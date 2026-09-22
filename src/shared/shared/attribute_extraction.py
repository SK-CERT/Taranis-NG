"""Detect values in news item text and turn them into news item attributes.

Vulnerability identifiers (CVE, CWE, GHSA, CVSS vectors and so on) are pulled out of a news
item's text with operator-editable regular expressions, so a deployment can add its own
identifiers without a code change.

This module is deliberately dependency-free — no Flask, no database, no ORM. Both core and
the collectors call it, which is the point: the collectors run it as text arrives from RSS,
web or e-mail, and core runs it for manually entered items, which never pass through a
collector at all. One implementation, one behaviour, and it is unit-testable on its own.

The matching is the same shape the ANALYST_BOT used (``re.finditer``, group 1 when the
pattern defines one, else group 0), so rules written for that bot keep working.

Safety
------
The patterns come from an administrator through the GUI, and they run against every
collected item, which makes a catastrophic pattern a denial of service against collection
itself. Three bounds apply, in order:

* the analysed text is truncated to ``max_text`` characters;
* each rule gets a wall-clock budget, when the ``regex`` module is available;
* each rule can contribute at most ``max_matches`` values.

``regex`` is a drop-in superset of ``re`` that supports ``timeout=``. Where it is missing the
module still works and still truncates and caps, it just cannot interrupt a pathological
pattern mid-match; ``TIMEOUT_SUPPORTED`` says which mode is in effect.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


class _Logger(Protocol):
    """The slice of a logger this module uses.

    Structural rather than concrete so the collectors can pass their per-source
    ``TaranisLogger`` and core can pass its own, without either importing the other.
    """

    def warning(self, message: str) -> None:
        """Report a rule that was skipped."""

    def exception(self, message: str) -> None:
        """Report an unexpected failure in a rule."""


try:  # pragma: no cover - exercised by whichever branch the environment provides
    import regex as _regex

    TIMEOUT_SUPPORTED = True
except ImportError:  # pragma: no cover
    _regex = None
    TIMEOUT_SUPPORTED = False

DEFAULT_MAX_TEXT = 100_000
DEFAULT_MAX_MATCHES = 100
DEFAULT_TIMEOUT_SECONDS = 0.5


class ExtractionRule(NamedTuple):
    """A single detection rule, as configured by an administrator.

    Attributes:
        name (str): Human-readable name, used in log messages.
        attribute_key (str): Key of the news item attribute written on a hit.
        pattern (str): The regular expression.
        capture_group (int): Group to take; 0 means the whole match.
        max_matches (int): Upper bound on values contributed by this rule.
    """

    name: str
    attribute_key: str
    pattern: str
    capture_group: int = 0
    max_matches: int = DEFAULT_MAX_MATCHES

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionRule:
        """Build a rule from an API payload, tolerating missing optional keys.

        Args:
            data (dict): One rule as delivered by core.

        Returns:
            ExtractionRule: The parsed rule.
        """
        return cls(
            name=data.get("name") or data.get("attribute_key") or "",
            attribute_key=data.get("attribute_key") or "",
            pattern=data.get("pattern") or "",
            capture_group=int(data.get("capture_group") or 0),
            max_matches=int(data.get("max_matches") or DEFAULT_MAX_MATCHES),
        )


def build_text(title: str | None, review: str | None, content: str | None, *, max_text: int = DEFAULT_MAX_TEXT) -> str:
    """Join the searchable parts of a news item and bound the result.

    Args:
        title (str | None): News item title.
        review (str | None): News item review.
        content (str | None): News item content.
        max_text (int): Hard cap on the returned length.

    Returns:
        str: The text to search.
    """
    return " ".join(part for part in (title, review, content) if part)[:max_text]


def extract_attributes(
    title: str | None,
    review: str | None,
    content: str | None,
    rules: Iterable[ExtractionRule],
    *,
    max_text: int = DEFAULT_MAX_TEXT,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    logger: _Logger | None = None,
) -> list[tuple[str, str]]:
    """Find every configured value in a news item's text.

    Args:
        title (str | None): News item title.
        review (str | None): News item review.
        content (str | None): News item content.
        rules (Iterable[ExtractionRule]): The rules to apply.
        max_text (int): Truncate the searched text to this many characters.
        timeout (float): Per-rule wall-clock budget in seconds, when supported.
        logger (_Logger | None): Optional logger; a bad or slow pattern is reported here.

    Returns:
        list[tuple[str, str]]: ``(attribute_key, value)`` pairs, de-duplicated,
        in the order the rules were given.
    """
    text = build_text(title, review, content, max_text=max_text)
    if not text:
        return []

    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for rule in rules:
        if not rule.pattern or not rule.attribute_key:
            continue
        for value in _matches_for_rule(rule, text, timeout=timeout, logger=logger):
            pair = (rule.attribute_key, value)
            if pair not in seen:
                seen.add(pair)
                found.append(pair)

    return found


def _matches_for_rule(rule: ExtractionRule, text: str, *, timeout: float, logger: _Logger | None) -> list[str]:
    """Return the distinct values one rule finds, bounded by its max_matches.

    A rule that fails - bad pattern, or a timeout on a catastrophic one - yields nothing and
    never propagates: one broken rule must not stop the others, and must not stop collection.
    """
    values: list[str] = []
    seen: set[str] = set()
    try:
        for match in _finditer(rule.pattern, text, timeout=timeout):
            value = _value_of(match, rule.capture_group)
            if not value or value in seen:
                continue
            seen.add(value)
            values.append(value)
            if len(values) >= rule.max_matches:
                break
    except TimeoutError:
        _log(logger, "warning", f"Attribute extraction rule '{rule.name}' timed out after {timeout}s and was skipped")
        return []
    except re.error as error:
        _log(logger, "warning", f"Attribute extraction rule '{rule.name}' has an invalid pattern and was skipped: {error}")
        return []
    except Exception as error:  # a rule must never take collection down with it
        _log(logger, "exception", f"Attribute extraction rule '{rule.name}' failed: {error}")
        return []
    return values


def _finditer(pattern: str, text: str, *, timeout: float) -> Iterator[re.Match[str]]:
    """Iterate matches, with a wall-clock budget where the regex module allows it."""
    if _regex is not None:
        # regex raises its own TimeoutError subclass of Exception; normalise below.
        try:
            yield from _regex.finditer(pattern, text, timeout=timeout)
        except TimeoutError:
            raise
        except _regex.error as error:  # keep the same surface as re.error
            raise re.error(str(error)) from error
        return
    yield from re.finditer(pattern, text)


def _value_of(match: re.Match[str], capture_group: int) -> str:
    """Take the configured group, falling back to group 1 then the whole match.

    Mirrors ANALYST_BOT, which used group 1 whenever the pattern defined one.
    """
    if capture_group and match.re.groups >= capture_group:
        return (match.group(capture_group) or "").strip()
    if match.re.groups:
        return (match.group(1) or "").strip()
    return (match.group(0) or "").strip()


def _log(logger: _Logger | None, level: str, message: str) -> None:
    """Log through whatever logger the caller provided, if any."""
    if logger is None:
        return
    getattr(logger, level, None) and getattr(logger, level)(message)
