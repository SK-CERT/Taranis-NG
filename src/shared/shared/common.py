"""Common functions used across whole application."""

import os
import re
from collections.abc import Callable
from functools import wraps
from html import escape
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Comment

from shared.log_manager import logger

TZ = ZoneInfo(os.getenv("TZ", "UTC"))

# Tags kept as-is. Same list as the GUI's DOMPurify allowlist
# (src/gui-v3/src/utils/sanitizeNewsItemHtml.ts), so what is stored is also what renders.
ALLOWED_HTML_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "b",
    "strong",
    "i",
    "em",
    "a",
    "pre",
    "code",
    "br",
    "div",
    "span",
    "blockquote",
    "mark",
    "small",
    "del",
    "ins",
    "sup",
    "sub",
    "u",
    "s",
}
ALLOWED_HTML_ATTRS = {"a": ["href"]}

# Tags dropped together with everything inside them: their content is styling, scripting
# or metadata, never body text. This mirrors DOMPurify's FORBID_CONTENTS handling.
DISCARDED_HTML_TAGS = {
    "applet",
    "base",
    "button",
    "embed",
    "form",
    "frame",
    "frameset",
    "head",
    "iframe",
    "input",
    "link",
    "math",
    "meta",
    "noscript",
    "object",
    "option",
    "script",
    "select",
    "style",
    "svg",
    "template",
    "textarea",
    "title",
}

# Everything else is unwrapped, keeping its text. For block-level tags that would glue
# two lines together, so they become a plain <div> instead - nested <div>s still render
# as a single line break. Table rows are the reason this matters: HTML mail is usually
# laid out in tables, and <td>/<th> are unwrapped so a row stays on one line.
BLOCK_HTML_TAGS = {
    "address",
    "article",
    "aside",
    "caption",
    "center",
    "colgroup",
    "dd",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "h5",
    "h6",
    "header",
    "hr",
    "legend",
    "main",
    "nav",
    "section",
    "table",
    "tbody",
    "tfoot",
    "thead",
    "tr",
}

# Unwrapped inline tags that need a separator, or their text runs into the next cell.
SEPARATED_HTML_TAGS = {"td", "th"}


def simplify_html_text(html_string: str) -> str:
    """Return text with only allowed tags preserved.

    Tags carrying no body text (``<script>``, ``<style>``, ``<head>``...) are dropped with
    their content; every other unsupported tag is unwrapped, so its text survives. That
    matters for anything wrapped in markup this application does not render itself - a
    full ``<html>`` document or a table-based HTML email would otherwise come out empty.

    Args:
        html_string (string): The HTML string.

    Returns:
        string: The simplified string with only allowed tags.
    """
    soup = BeautifulSoup(html_string, "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(list(DISCARDED_HTML_TAGS)):
        tag.decompose()
    for tag in soup.find_all(name=True):
        if tag.name in ALLOWED_HTML_TAGS:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in ALLOWED_HTML_ATTRS.get(tag.name, [])}
        elif tag.name in BLOCK_HTML_TAGS:
            tag.name = "div"
            tag.attrs = {}
        else:
            if tag.name in SEPARATED_HTML_TAGS:
                tag.append(" ")
            tag.unwrap()
    return str(soup)


def resolve_relative_links(html_string: str, base_url: str) -> str:
    """Rewrite relative ``<a href>`` targets against the page the markup was collected from.

    Collected content keeps whatever the source site wrote, and sites routinely link
    root-relatively (``/security/advisory-1``). Selenium hands back the literal markup for
    ``innerHTML``, so those hrefs stay relative even though the item's own link is absolute.
    Stored that way, the browser rendering a news item resolves them against the Taranis
    origin and the link points back at this instance instead of the source. Resolving them
    once, at collection time, keeps the GUI, presenters and publishers consistent.

    Absolute URLs and non-network schemes (``mailto:``, and anything else ``urljoin`` treats
    as non-relative) pass through untouched.

    Args:
        html_string (string): The HTML string.
        base_url (string): The URL the markup was collected from. Falsy leaves the HTML as is.

    Returns:
        string: The HTML with every ``<a href>`` resolved against base_url.
    """
    if not base_url or not html_string:
        return html_string
    soup = BeautifulSoup(html_string, "html.parser")
    for tag in soup.find_all("a", href=True):
        tag["href"] = urljoin(base_url, tag["href"])
    return str(soup)


def remove_empty_html_tags(html_string: str) -> str:
    """Remove empty HTML tags from the given string.

    Args:
        html_string (string): The HTML string.

    Returns:
        string: The string without empty HTML tags.
    """
    soup = BeautifulSoup(html_string, "html.parser")
    changed = True
    while changed:
        changed = False
        for tag in soup.find_all():
            # Skip certain tags that are allowed to be empty
            if tag.name in ["br", "img"]:
                continue
            # Remove if no text content and no meaningful attributes
            if not tag.get_text(strip=True) and not tag.find_all():
                tag.decompose()
                changed = True
    return str(soup).strip()


def strip_html(html_string: str) -> str:
    """Strip HTML tags from the given string.

    Args:
        html_string (string): The HTML string.

    Returns:
        string: The string without HTML tags.

    """
    soup = BeautifulSoup(html_string, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def text_to_simple_html(text: str, preformatted_text: bool) -> str:
    """Convert a plain text string into a simple, safe HTML fragment.

    - Escapes HTML special characters.
    - Converts CRLF / CR / LF to <br> or to <pre>.

    Args:
        text: input string (None treated as empty).
        preformatted_text: if True, wrap the text in <pre> tags instead of <p> and <br>.

    Returns:
        A safe HTML fragment.
    """
    if not text:
        return ""
    if preformatted_text:
        # Escaped, not stripped: <pre> is used where the line breaks and indentation are
        # the point, and an unescaped '<' would be parsed as a tag and dropped by
        # simplify_html_text - taking things like <https://example.com/> with it.
        return f"<pre>{escape(text)}</pre>"
    escaped = strip_html(text)
    normalized = escaped.replace("\r\n", "\n").replace("\r", "\n")
    with_br = normalized.replace("\n", "<br>")
    return f"<p>{with_br}</p>"


def smart_truncate(content: str, length: int = 500, suffix: str = " [...]") -> str:
    """Truncate the given content to a specified length and adds a suffix if necessary.

    Args:
        content (str): The content to be truncated.
        length (int): The maximum length of the truncated content. Default is 500.
        suffix (str): The suffix to be added at the end of the truncated content. Default is " [...]".

    Returns:
        (str): The truncated content.

    """
    if len(content) <= length:
        return clean_whitespace(content)
    truncated = re.compile(r"\s+").split(content[: length + 1])[0:-1]
    if truncated:
        return " ".join(truncated) + suffix
    return content[:length] + suffix  # cut at length if no spaces exist


def clean_whitespace(string: str) -> str:
    """Replace whitespace (spaces, tabs, newlines) for single space.

    Args:
        string (string): The string to be replaced.

    Returns:
        string: The string without whitespace.

    """
    return re.sub(r"\s+", " ", string.strip())


def read_int_parameter(name: str, default_value: int, object_dict: dict) -> int:
    """Read an integer parameter from a source dictionary.

    Args:
        name (str): The name of the parameter to read.
        default_value (int): The default value to return if the parameter is not found or is not a valid integer.
        object_dict (dict): The dictionary containing the parameter values.

    Returns:
        val (int): The value of the parameter, or the default value if the parameter is not found or is not a valid integer.

    """
    val = default_value
    try:
        par_val = object_dict.param_key_values[name]
        if par_val != "":
            val = int(par_val)
            if val <= 0:
                val = default_value
    except KeyError:
        logger.error(f"Integer parameter '{name}' doesn't exist. Use 'python db_migration.py regenerate' to rebuild parameters.")
    except Exception:
        object_dict.logger.exception("Reading of integer parameter failed")
    return val


def read_str_parameter(name: str, default_value: str, object_dict: dict) -> str:
    """Read a string parameter from a source dictionary.

    Args:
        name (str): The name of the parameter to read.
        default_value (str): The default value to return if the parameter is not found.
        object_dict (dict): The dictionary containing the parameter values.

    Returns:
        val (str): The value of the parameter, or the default value if the parameter is not found.

    """
    val = default_value
    try:
        par_val = object_dict.param_key_values[name]
        if par_val != "":
            val = par_val
    except KeyError:
        logger.error(f"String parameter '{name}' doesn't exist. Use 'python db_migration.py regenerate' to rebuild parameters.")
    except Exception:
        logger.exception("Reading of string parameter failed")
    return val


def read_bool_parameter(name: str, *, default_value: bool, object_dict: dict) -> bool:
    """Read a boolean parameter from a source dictionary.

    Args:
        name (str): The name of the parameter to read.
        default_value (bool): The default value to return if the parameter is not found or is not a valid boolean.
        object_dict (dict): The dictionary containing the parameter values.

    Returns:
        val (bool): The value of the parameter, or the default value if the parameter is not found or is not a valid boolean.
    """
    val = default_value
    try:
        par_val = object_dict.param_key_values[name]
        if par_val.lower() in ["true", "yes", "1"]:
            val = True
        elif par_val.lower() in ["false", "no", "0"]:
            val = False
    except KeyError:
        logger.error(f"Boolean parameter '{name}' doesn't exist. Use 'python db_migration.py regenerate' to rebuild parameters.")
    except Exception:
        object_dict.logger.exception("Reading of boolean parameter failed")
    return val


def ignore_exceptions(func: Callable) -> Callable:
    """Wrap scheduled action with exception handling."""

    @wraps(func)
    def wrapper(self: object) -> None:
        """Handle exceptions during scheduled runs.

        Raises:
            Exception: If an unhandled exception occurs during the run.

        """
        try:
            func(self)
        except Exception:
            logger.exception("An unhandled exception occurred during scheduled run")

    return wrapper
