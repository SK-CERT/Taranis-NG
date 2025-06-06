"""Common functions used across whole application."""

import re
from bs4 import BeautifulSoup
from shared.log_manager import logger


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
        return clean_whitespace(content)
    else:
        truncated = re.compile(r"\s+").split(content[: length + 1])[0:-1]
        if truncated:
            return " ".join(truncated) + suffix
        return content[:length] + suffix  # cut at length if no spaces exist


def clean_whitespace(string: str) -> str:
    """Replace whitespace (spaces, tabs, newlines) for single space.

    Arguments:
        string (string): The string to be replaced.

    Returns:
        string: The string without whitespace.
    """
    return re.sub(r"\s+", " ", string.strip())


def read_int_parameter(name, default_value, object):
    """Read an integer parameter from a source dictionary.

    Parameters:
        name (str): The name of the parameter to read.
        default_value (int): The default value to return if the parameter is not found or is not a valid integer.
        object (dict): The dictionary containing the parameter values.
    Returns:
        val (int): The value of the parameter, or the default value if the parameter is not found or is not a valid integer.
    """
    val = default_value
    try:
        par_val = object.param_key_values[name]
        if par_val != "":
            val = int(par_val)
            if val <= 0:
                val = default_value
    except KeyError:
        logger.error(f"Integer parameter '{name}' doesn't exist. Use 'python db_migration.py regenerate' to rebuild parameters.")
    except Exception as error:
        object.logger.exception(f"Reading of integer parameter failed: {error}")
    return val


def read_str_parameter(name, default_value, object):
    """Read a string parameter from a source dictionary.

    Parameters:
        name (str): The name of the parameter to read.
        default_value (str): The default value to return if the parameter is not found.
        object (dict): The dictionary containing the parameter values.
    Returns:
        val (str): The value of the parameter, or the default value if the parameter is not found.
    """
    val = default_value
    try:
        par_val = object.param_key_values[name]
        if par_val != "":
            val = par_val
    except KeyError:
        logger.error(f"String parameter '{name}' doesn't exist. Use 'python db_migration.py regenerate' to rebuild parameters.")
    except Exception as error:
        logger.exception(f"Reading of string parameter failed: {error}")
    return val
