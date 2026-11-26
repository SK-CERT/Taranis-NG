"""Rich Text attribute values for templates: formatting in HTML output, plain text everywhere else.

A Rich Text attribute is stored as the HTML the report editor writes. HTML and PDF products, and
MESSAGE bodies in an ``.html`` template, are rendered with autoescaping, so the raw value showed
its tags - and printing it unescaped would pass on whatever markup a report value carries (links,
images, styles, scripts). Plain-text output (the TEXT presenter, ``.txt`` MESSAGE bodies, titles
and headers, MISP) printed the tags themselves.

So the presenter cleans the value against the editor's own allow-list and hands templates a
:class:`RichText`: printed into HTML output it is the cleaned formatting, printed anywhere else it
is plain text - paragraphs and line breaks kept, list items bulleted, link targets written out,
no tags.
"""

from __future__ import annotations

import re
from typing import Self
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, CData, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction, Tag
from markupsafe import escape

# What the report editor produces (the GUI's sanitizeRichTextHtml allow-list), without `class`.
ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "b",
        "i",
        "u",
        "s",
        "em",
        "strong",
        "span",
        "div",
        "ul",
        "ol",
        "li",
        "a",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        "code",
    },
)
# Elements whose content is not text to keep: dropped whole rather than unwrapped.
DROPPED_WITH_CONTENT = frozenset(
    {"script", "style", "template", "iframe", "object", "embed", "noscript", "svg", "math", "head", "title", "textarea", "select"},
)
LINK_SCHEMES = frozenset({"http", "https", "mailto"})
NOT_TEXT = (Comment, CData, Declaration, Doctype, ProcessingInstruction)

# In plain text: elements that stand apart as paragraphs, and those that start a line.
PARAGRAPHS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"})
LINES = frozenset({"div"})


class RichText(str):
    """A sanitized Rich Text value: its plain text as a string, its formatting as ``__html__``.

    Jinja prints a value into autoescaped (HTML) output through ``markupsafe.escape``, which takes
    ``__html__`` as markup that is already safe: the formatting. Any other output prints the
    string itself: the plain text. Template filters (``| truncate``, ``| upper``, ...) work on the
    plain text, and their result is escaped in HTML output like any other text.
    """

    __slots__ = ("_html",)

    def __new__(cls, html: str, text: str | None = None) -> Self:
        """Hold the sanitized ``html`` and its plain ``text`` (derived from it when not given)."""
        value = super().__new__(cls, html_to_text(html) if text is None else text)
        value._html = html
        return value

    def __html__(self) -> str:
        """The sanitized formatting, for HTML output."""
        return self._html

    def __reduce__(self) -> tuple[type[RichText], tuple[str, str]]:
        """Copy and pickle keep both forms."""
        return RichText, (self._html, str(self))


def _link(href: str | None) -> str | None:
    """The link target if it is a web or mail address, else None."""
    if not href:
        return None
    try:
        scheme = urlsplit(href.strip()).scheme.lower()
    except ValueError:
        return None
    return href.strip() if scheme in LINK_SCHEMES else None


def rich_text(value: object) -> object:
    """Sanitize a Rich Text value for templates (see the module docstring).

    Allowed elements keep their content but lose every attribute except a link's ``href`` to an
    http(s) or mailto address. Other elements are unwrapped (their text stays), and scripts,
    styles, frames and the like are dropped with their content, as are comments.

    Args:
        value (object): The stored value; anything that is not a non-empty string is returned as it is.

    Returns:
        object: A RichText, or ``value`` unchanged.
    """
    if not isinstance(value, str) or not value:
        return value
    soup = BeautifulSoup(value, "html.parser")
    if soup.find(name=True) is None:
        # No markup at all (a value stored before the editor, or through the API): it is text,
        # with its line breaks.
        return RichText(str(escape(value)).replace("\n", "<br>\n"), value)
    for node in soup.find_all(string=lambda text: isinstance(text, NOT_TEXT)):
        node.extract()
    for element in soup.find_all(name=True):
        if element.decomposed:
            continue
        if element.name in DROPPED_WITH_CONTENT:
            element.decompose()
        elif element.name not in ALLOWED_TAGS:
            element.unwrap()
        else:
            href = _link(element.get("href")) if element.name == "a" else None
            element.attrs = {"href": href, "rel": "noopener noreferrer"} if href else {}
    return RichText(str(soup))


class _PlainText:
    """Collects the plain text of an element tree: paragraphs, lines and list items as text."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def text(self) -> str:
        text = re.sub(r"[ \t]+\n", "\n", "".join(self.parts))
        return re.sub(r"\n{3,}", "\n\n", text).strip("\n").rstrip()

    def _at_line_start(self) -> bool:
        return not self.parts or "".join(self.parts[-2:]).endswith("\n")

    def _break(self, count: int) -> None:
        """End the current line, so that ``count`` line breaks (at most) precede what follows."""
        if not self.parts:
            return
        tail = "".join(self.parts).rstrip(" \t")
        present = len(tail) - len(tail.rstrip("\n"))
        self.parts = [tail]
        if present < count:
            self.parts.append("\n" * (count - present))

    def walk(self, node: Tag, *, pre: bool = False, depth: int = 0) -> None:
        counter = 0
        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child) if pre else re.sub(r"\s+", " ", str(child))
                if not pre and self._at_line_start():
                    text = text.lstrip(" ")
                if text:
                    self.parts.append(text)
            elif isinstance(child, Tag):
                counter = self._element(node, child, counter, pre=pre, depth=depth)

    def _element(self, parent: Tag, child: Tag, counter: int, *, pre: bool, depth: int) -> int:
        name = child.name
        if name == "br":
            self._break(1)
        elif name == "li":
            counter += 1
            self._break(1)
            self.parts.append("  " * max(depth - 1, 0) + (f"{counter}. " if parent.name == "ol" else "- "))
            self.walk(child, pre=pre, depth=depth)
        elif name in ("ul", "ol"):
            self._break(1)
            self.walk(child, pre=pre, depth=depth + 1)
            self._break(1)
        elif name in PARAGRAPHS:
            self._break(2)
            self.walk(child, pre=pre or name == "pre", depth=depth)
            self._break(2)
        elif name in LINES:
            self._break(1)
            self.walk(child, pre=pre, depth=depth)
            self._break(1)
        elif name == "a":
            label = _PlainText()
            label.walk(child, pre=pre, depth=depth)
            text = "".join(label.parts)
            self.parts.append(text)
            href = child.get("href")
            if href and href not in text:
                self.parts.append(f" ({href})" if text.strip() else str(href))
        else:
            self.walk(child, pre=pre, depth=depth)
        return counter


def html_to_text(html: str) -> str:
    """The plain text of sanitized Rich Text HTML (see the module docstring)."""
    collector = _PlainText()
    collector.walk(BeautifulSoup(html, "html.parser"))
    return collector.text()


def as_html(data: object) -> object:
    """``data`` with every RichText replaced by its HTML, for output that serializes values (JSON)."""
    if isinstance(data, RichText):
        return data.__html__()
    if isinstance(data, dict):
        return {key: as_html(value) for key, value in data.items()}
    if isinstance(data, list):
        return [as_html(value) for value in data]
    return data
