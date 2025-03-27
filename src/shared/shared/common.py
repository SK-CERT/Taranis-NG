"""Common functions used across whole application."""

import re
from bs4 import BeautifulSoup


def strip_html(html_string: str) -> str:
    """Strip HTML tags from the given string.

    Arguments:
        html_string (string): The HTML string.

    Returns:
        string: The string without HTML tags.
    """
    soup = BeautifulSoup(html_string, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def smart_truncate(content, length=500, suffix=" [...]") -> str:
    """Truncate the given content to a specified length and adds a suffix if necessary.

    Parameters:
        content (str): The content to be truncated.
        length (int): The maximum length of the truncated content. Default is 500.
        suffix (str): The suffix to be added at the end of the truncated content. Default is " [...]".
    Returns:
        (str): The truncated content.
    """
    if len(content) <= length:
        return content
    else:
        truncated = re.compile(r"\s+").split(content[: length + 1])[0:-1]
        if truncated:
            return " ".join(truncated) + suffix
        return content[:length] + suffix  # cut at length if no spaces exist
