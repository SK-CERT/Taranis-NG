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
from html import unescape
from typing import TYPE_CHECKING, Self
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, CData, Comment, Declaration, Doctype, NavigableString, ParserRejectedMarkup, ProcessingInstruction, Tag
from markupsafe import escape

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bs4 import PageElement

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
# Elements nested deeper than this keep only their text. The editor nests a few levels; a value
# nesting hundreds made the plain-text conversion recurse until it failed, and with it the render.
MAX_NESTING = 64
# Anything that looks like a tag, for a value the HTML parser refuses.
TAG_LIKE = re.compile(r"<[^<>]*>")


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
    styles, frames and the like are dropped with their content, as are comments. Allowed
    elements nested deeper than MAX_NESTING are unwrapped too. A value the HTML parser refuses
    is taken as text, its tags removed.

    Args:
        value (object): The stored value; anything that is not a non-empty string is returned as it is.

    Returns:
        object: A RichText, or ``value`` unchanged.
    """
    if not isinstance(value, str) or not value:
        return value
    try:
        soup = BeautifulSoup(value, "html.parser")
        if soup.find(name=True) is None:
            # No markup at all (a value stored before the editor, or through the API): it is
            # text, with its line breaks.
            return _text(value)
        return RichText(_sanitized_html(soup))
    except (ParserRejectedMarkup, RecursionError):
        # Never seen with html.parser, but a report value must not cost the whole product.
        return _text(unescape(TAG_LIKE.sub("", value)))


def _text(text: str) -> RichText:
    """Plain text as a RichText: escaped, with its line breaks, in HTML output."""
    return RichText(str(escape(text)).replace("\n", "<br>\n"), text)


def _sanitized_html(soup: BeautifulSoup) -> str:
    """The allowed elements of a parsed value, written out in one pass over the tree.

    The tree is read, never changed: Beautiful Soup's ``unwrap``, ``decompose`` and ``decomposed``
    each search the siblings or the subtree, so cleaning the tree in place took time growing with
    the square of the input (seconds for a few thousand nested or sibling elements). The output
    is what ``str(soup)`` printed for the cleaned tree.
    """
    formatter = soup.formatter_for_name("minimal")
    pieces: list[str] = []
    # Children still to write, and the end tag that follows them (None for an unwrapped element).
    stack: list[tuple[Iterator[PageElement], str | None]] = [(iter(soup.contents), None)]
    nesting = 0
    while stack:
        children, end_tag = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            if end_tag is not None:
                pieces.append(end_tag)
                nesting -= 1
        elif isinstance(child, NavigableString):
            if not isinstance(child, NOT_TEXT):
                pieces.append(child.output_ready(formatter))
        elif not isinstance(child, Tag) or child.name in DROPPED_WITH_CONTENT:
            continue  # left out, with everything in it
        elif child.name not in ALLOWED_TAGS or nesting >= MAX_NESTING:
            stack.append((iter(child.contents), None))
        else:
            href = _link(child.get("href")) if child.name == "a" else None
            attributes = {"href": href, "rel": "noopener noreferrer"} if href else {}
            start = f"<{child.name}" + "".join(
                f" {key}={formatter.quoted_attribute_value(formatter.attribute_value(text))}" for key, text in attributes.items()
            )
            if child.is_empty_element:
                pieces.append(f"{start}{formatter.void_element_close_prefix or ''}>")
            else:
                pieces.append(f"{start}>")
                stack.append((iter(child.contents), f"</{child.name}>"))
                nesting += 1
    return "".join(pieces)


def _kind(piece: str) -> str:
    """What the line-start test needs of a piece of text: empty, ending a line, or neither."""
    if not piece:
        return ""
    return "\n" if piece.endswith("\n") else "x"


class _PlainText:
    """Collects the plain text of an element tree: paragraphs, lines and list items as text.

    The text is kept as the pieces written and looked at from its end only; it is joined once, in
    :meth:`text` (joining it at every line break took time growing with the square of the input).
    Whether a line has just started is judged as before, from the last two pieces written - an
    empty link label counts as one - which ``_recent`` keeps as their kinds (see :func:`_kind`).
    """

    def __init__(self) -> None:
        self.parts: list[str] = []
        self._written = False
        self._recent = ("", "")

    def text(self) -> str:
        lines = "".join(self.parts).split("\n")
        # Spaces and tabs ending a line go (a regular expression for that takes quadratic time
        # on a long run of spaces in <pre>).
        text = "\n".join([line.rstrip(" \t") for line in lines[:-1]] + lines[-1:])
        return re.sub(r"\n{3,}", "\n\n", text).strip("\n").rstrip()

    def _write(self, piece: str) -> None:
        self._written = True
        self._recent = (self._recent[1], _kind(piece))
        if piece:
            self.parts.append(piece)

    def _at_line_start(self) -> bool:
        return not self._written or "".join(self._recent).endswith("\n")

    def _trailing_newlines(self, limit: int) -> int:
        """How many line breaks end the text, counted up to ``limit``."""
        found = 0
        for part in reversed(self.parts):
            index = len(part)
            while index and found < limit and part[index - 1] == "\n":
                index -= 1
                found += 1
            if index or found >= limit:
                break
        return found

    def _break(self, count: int) -> None:
        """End the current line, so that ``count`` line breaks (at most) precede what follows."""
        if not self._written:
            return
        # Spaces and tabs at the end of the text go.
        while self.parts:
            trimmed = self.parts[-1].rstrip(" \t")
            if trimmed:
                self.parts[-1] = trimmed
                break
            self.parts.pop()
        present = self._trailing_newlines(count)
        tail = ("\n" if present else "x") if self.parts else ""
        if present < count:
            self.parts.append("\n" * (count - present))
            self._recent = (tail, "\n")
        else:
            self._recent = ("", tail)

    def _string(self, text: str, *, pre: bool) -> None:
        if not pre:
            text = re.sub(r"\s+", " ", text)
            if self._at_line_start():
                text = text.lstrip(" ")
        if text:
            self._write(text)

    def walk(self, node: Tag, *, pre: bool = False, depth: int = 0, nesting: int = 0) -> None:
        counter = 0
        for child in node.children:
            if isinstance(child, NavigableString):
                self._string(str(child), pre=pre)
            elif isinstance(child, Tag) and nesting >= MAX_NESTING:
                # Too deep for structure (see MAX_NESTING): the element's text, read without recursion.
                self._string("".join(str(text) for text in child.descendants if isinstance(text, NavigableString)), pre=pre)
            elif isinstance(child, Tag):
                counter = self._element(node, child, counter, pre=pre, depth=depth, nesting=nesting + 1)

    def _element(self, parent: Tag, child: Tag, counter: int, *, pre: bool, depth: int, nesting: int) -> int:
        name = child.name
        if name == "br":
            self._break(1)
        elif name == "li":
            counter += 1
            self._break(1)
            self._write("  " * max(depth - 1, 0) + (f"{counter}. " if parent.name == "ol" else "- "))
            self.walk(child, pre=pre, depth=depth, nesting=nesting)
        elif name in ("ul", "ol"):
            self._break(1)
            self.walk(child, pre=pre, depth=depth + 1, nesting=nesting)
            self._break(1)
        elif name in PARAGRAPHS:
            self._break(2)
            self.walk(child, pre=pre or name == "pre", depth=depth, nesting=nesting)
            self._break(2)
        elif name in LINES:
            self._break(1)
            self.walk(child, pre=pre, depth=depth, nesting=nesting)
            self._break(1)
        elif name == "a":
            label = _PlainText()
            label.walk(child, pre=pre, depth=depth, nesting=nesting)
            text = "".join(label.parts)
            self._write(text)
            href = child.get("href")
            if href and href not in text:
                self._write(f" ({href})" if text.strip() else str(href))
        else:
            self.walk(child, pre=pre, depth=depth, nesting=nesting)
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
