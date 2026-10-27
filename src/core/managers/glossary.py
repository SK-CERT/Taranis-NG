"""Which glossary entries go into an AI translation prompt, and how they are worded.

An entry applies when one of its terms occurs in the texts being translated: its term in the
source language, or any of its terms when the source language is not set or the term is kept as
written. Matching ignores case and finds a term inside a longer word, so an inflected form
("zranitelnosti") still finds its base form ("zranitelnost"). The first entry for a term wins,
so the report type's own entries, which come first, override the instance's.

The answer is not checked against the glossary: Czech and Slovak inflect terms, so a check for
the exact term would reject good translations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from model.glossary import GlossaryEntry

# Prompts stay short: no more entries than this go into one.
MAX_ENTRIES = 50


def glossary_lines(entries: Iterable[GlossaryEntry], texts: Iterable[str], source: str | None, target: str) -> list[str]:
    """The glossary instructions for translating ``texts`` from ``source`` into ``target``.

    Args:
        entries (Iterable[GlossaryEntry]): The entries that apply, most specific first.
        texts (Iterable[str]): The texts being translated.
        source (str | None): Their language, None when not set.
        target (str): The language translated into.

    Returns:
        list[str]: One line per entry that occurs in the texts, at most :data:`MAX_ENTRIES`.
    """
    haystack = "\n".join(text for text in texts if text).casefold()
    lines: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        terms = entry.terms or {}
        if entry.keep:
            candidates = list(terms.values())
            wanted = None
        else:
            wanted = terms.get(target)
            if not wanted:
                continue
            candidates = [terms[source]] if source and terms.get(source) else ([] if source else list(terms.values()))
        term = next((term for term in candidates if term and term != wanted and term.casefold() in haystack), None)
        if term is None or term.casefold() in seen:
            continue
        seen.add(term.casefold())
        line = f"Keep «{term}» exactly as written." if wanted is None else f"Translate «{term}» as «{wanted}»."
        if entry.note:
            line = f"{line} ({entry.note})"
        lines.append(line)
        if len(lines) >= MAX_ENTRIES:
            break
    return lines
