"""Turn rendered template text into mail headers that are safe to hand to an MTA.

Header values here originate in analyst-entered report item attributes, so this module is
the boundary where untrusted text stops being data and becomes a protocol element. Two
facts drive every rule below:

* Header **values** are guarded by the standard library — ``EmailMessage.__setitem__``
  under ``policy.default`` raises ``ValueError`` on CR/LF. But that exception would escape
  the email publisher (``envelope`` catches only ``TypeError``) and kill the whole send, so
  we scrub instead of relying on it.
* Header **names** are guarded by nothing. ``"X-Colon: Injected"``, ``"X Bad Name"``,
  ``"X-ü"`` and ``""`` are all accepted and serialised verbatim, so we validate them here.

The deny-list is not defence in depth, it is the primary control: ``envelope.header()``
reroutes ``bcc``/``cc``/``to`` to its own setters, and ``_send_now`` builds the SMTP
recipient list from ``self._to + self._cc + self._bcc``. A rendered ``Bcc:`` line would
therefore add a **real recipient**, not a decorative header.

Do **not** RFC 2047-encode and do **not** fold values here. ``EmailMessage.__setitem__``
already does both; pre-encoding delivers literal ``=?utf-8?q?...?=`` text to the reader.

Failure policy: warn and drop, never raise. A malformed line is nearly always a template
typo or an analyst pasting a colon into free text, and killing a product publish over a
decorative header is the worse outcome.

Residual risk, stated plainly: unfolding means a value containing a bare newline starts a
*new* logical line rather than continuing the current one. ``Bcc:`` and everything else
that changes delivery is caught by the deny-list, but a benign ``X-Whatever:`` could slip
through that way. Three things mitigate it, in order of importance: the deny-list; the
presenters' ``collect_attrs`` filter scrubbing control characters out of every value it
emits; and the ``header_value`` filter being mandatory for raw ``{{ }}`` interpolation.
"""

import re
from collections.abc import Iterable, Mapping

from shared.log_manager import logger

MAX_HEADERS = 20
MAX_NAME_LENGTH = 64
MAX_VALUE_LENGTH = 998  # RFC 5322 section 2.1.1 line length limit, reused as a per-header budget
MAX_TOTAL_LENGTH = 8192  # total of all values; stays clear of MTA header section limits

# RFC 5322 ftext: printable ASCII (%d33-57 / %d59-126), i.e. everything but space and ":".
_FIELD_NAME = re.compile(r"[!-9;-~]+")

# Everything str.splitlines() treats as a line break, not just CR/LF: the standard library's
# header folder splits on all of these, so U+2028 is a live line-break vector that a naive
# "\r\n"-only scrub misses.
_CONTROL = re.compile("[\x00-\x1f\x7f\u0085\u2028\u2029]")

_WHITESPACE_RUN = re.compile(r"\s+")

RESERVED_HEADERS = frozenset(
    {
        # envelope.header() reroutes these to its own setters; "bcc" adds a real SMTP recipient
        "to",
        "cc",
        "bcc",
        "reply-to",
        "from",
        "subject",
        "sender",
        # MIME structure the publisher builds itself
        "content-type",
        "content-transfer-encoding",
        "content-disposition",
        "content-id",
        "mime-version",
        # envelope fills these in; a duplicate makes a malformed message
        "date",
        "message-id",
        # trace and envelope headers - forging them is spoofing
        "received",
        "return-path",
        "delivered-to",
        "dkim-signature",
        "authentication-results",
        # envelope derives behaviour from this one
        "list-unsubscribe",
    },
)

RESERVED_PREFIXES = ("resent-", "arc-", "x-original-")


def scrub_header_text(value: object) -> str:
    """Make a single value safe to sit on one header line.

    Strips every character that could break the header out of its line, collapses the
    resulting whitespace and trims the ends. Used both here and by the presenters' Jinja
    filters, so a value is already safe by the time a template interpolates it.

    Args:
        value (object): The raw value. ``None`` and non-strings are accepted.

    Returns:
        str: The scrubbed value, possibly empty.
    """
    if value is None:
        return ""
    text = _CONTROL.sub(" ", str(value))
    return _WHITESPACE_RUN.sub(" ", text).strip()


def sanitize_header(name: str, value: object) -> tuple[str, str] | None:
    """Validate one header name/value pair.

    Args:
        name (str): The header field name.
        value (object): The header value.

    Returns:
        tuple[str, str] | None: The safe pair, or None when the header must be dropped.
    """
    name = str(name).strip()

    if not _FIELD_NAME.fullmatch(name):
        logger.warning(f"Custom header dropped, not a valid field name: {name!r}")
        return None

    if len(name) > MAX_NAME_LENGTH:
        logger.warning(f"Custom header dropped, name longer than {MAX_NAME_LENGTH} characters: {name[:MAX_NAME_LENGTH]!r}")
        return None

    lowered = name.lower()
    if lowered in RESERVED_HEADERS or lowered.startswith(RESERVED_PREFIXES):
        # This is the line that stops a rendered "Bcc:" from adding a recipient.
        logger.warning(f"Custom header '{name}' refused: the publisher owns this header.")
        return None

    value = scrub_header_text(value)
    if not value:
        # The common case rather than an edge case: "X-Report-Category: {{ ... | join(', ') }}"
        # renders an empty value whenever no report item carries the attribute.
        return None

    if len(value) > MAX_VALUE_LENGTH:
        logger.warning(f"Custom header '{name}' truncated to {MAX_VALUE_LENGTH} characters.")
        value = f"{value[: MAX_VALUE_LENGTH - 1]}…"

    return name, value


def sanitize_headers(pairs: Iterable[Mapping[str, object] | tuple[str, object]]) -> list[dict[str, str]]:
    """Validate a whole set of headers and enforce the size limits.

    Idempotent: running the result back through returns the same list. The email publisher
    relies on that to re-check what a presenter sent it.

    Args:
        pairs (Iterable): Header pairs, either ``{"name": ..., "value": ...}`` mappings or
            ``(name, value)`` tuples.

    Returns:
        list[dict[str, str]]: The headers that survived, as ``{"name", "value"}`` dicts.
    """
    headers: list[dict[str, str]] = []
    total_length = 0

    for pair in pairs:
        if len(headers) >= MAX_HEADERS:
            logger.warning(f"Custom headers truncated at {MAX_HEADERS}, the rest were dropped.")
            break

        if isinstance(pair, Mapping):
            name, value = pair.get("name", ""), pair.get("value", "")
        else:
            name, value = pair

        sanitized = sanitize_header(name, value)
        if sanitized is None:
            continue

        name, value = sanitized
        if total_length + len(value) > MAX_TOTAL_LENGTH:
            logger.warning(f"Custom header '{name}' dropped, total header size would exceed {MAX_TOTAL_LENGTH} characters.")
            break

        total_length += len(value)
        headers.append({"name": name, "value": value})

    return headers


def parse_header_block(text: str) -> list[dict[str, str]]:
    """Parse rendered template output into sanitized mail headers.

    Understands RFC 5322 folding (a line starting with whitespace continues the previous
    one). Unlike a real message parser it does *not* stop at the first blank line: Jinja
    output is ragged, and a template author should not have to fight whitespace control to
    get a header block out.

    Args:
        text (str): The rendered headers template.

    Returns:
        list[dict[str, str]]: The headers that survived, as ``{"name", "value"}`` dicts.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    logical_lines: list[str] = []

    for raw_line in normalized.split("\n"):
        if not raw_line.strip():
            # Checked before the continuation test: a whitespace-only line is a Jinja
            # artefact, not a continuation appending nothing.
            continue

        if raw_line[0] in " \t":
            if not logical_lines:
                logger.warning(f"Custom header continuation without a header dropped: {raw_line.strip()[:80]!r}")
                continue
            logical_lines[-1] = f"{logical_lines[-1]} {raw_line.strip()}"
            continue

        logical_lines.append(raw_line.strip())

    pairs: list[tuple[str, str]] = []
    for line in logical_lines:
        name, separator, value = line.partition(":")
        if not separator:
            logger.warning(f"Custom header line without a colon dropped: {line[:80]!r}")
            continue
        pairs.append((name, value))

    return sanitize_headers(pairs)
