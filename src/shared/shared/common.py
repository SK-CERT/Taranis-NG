"""Common functions used across whole application."""

import os
import re
from collections.abc import Callable
from functools import wraps
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from shared.log_manager import logger

TZ = ZoneInfo(os.getenv("TZ", "UTC"))


def simplify_html_text(html_string: str) -> str:
    """Return text with only allowed tags preserved, stripping others and their content.

    Args:
        html_string (string): The HTML string.

    Returns:
        string: The simplified string with only allowed tags.
    """
    allowed_tags = {
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
    }
    allowed_attrs = {"a": ["href"]}
    soup = BeautifulSoup(html_string, "html.parser")
    for tag in soup.find_all(name=True):
        if tag.name not in allowed_tags:
            tag.decompose()
        else:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed_attrs.get(tag.name, [])}
    return str(soup)


def strip_html(html_string: str) -> str:
    """Strip HTML tags from the given string.

    Args:
        html_string (string): The HTML string.

    Returns:
        string: The string without HTML tags.

    """
    soup = BeautifulSoup(html_string, "html.parser")
    return soup.get_text(separator=" ", strip=True)


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
