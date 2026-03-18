"""Authentication manager for the API.

Returns:
    _type_: _description_
"""

import os
import ssl
from functools import wraps
from http import HTTPStatus

from config import Config
from flask import request

if os.getenv("SSL_VERIFICATION") == "False":
    try:
        _create_unverified_https_context = ssl._create_unverified_context  # noqa: SLF001
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context  # noqa: SLF001


def api_key_required(fn):  # noqa: ANN001, ANN201
    """Check if the API key is valid.

    Args:
        fn: The function to be decorated.

    Returns:
        wrapper: Wrapper function for the API endpoints.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs) -> tuple[dict, HTTPStatus]:  # noqa: ANN002, ANN003
        if "Authorization" not in request.headers or request.headers["Authorization"] != (f"ApiKey {Config.API_KEY}"):
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        return fn(*args, **kwargs)

    return wrapper
