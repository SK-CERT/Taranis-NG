"""Authorization manager for the API.

Returns:
    wrapper: Wrapper function for the API endpoints.
"""

import os
import ssl
from config import Config
from flask import request
from functools import wraps


if os.getenv("SSL_VERIFICATION") == "False":
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context


def api_key_required(fn):
    """Check for API key in the request header.

    Arguments:
        fn -- The function to be decorated.
    Returns:
        wrapper: Wrapper function for the API endpoints.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "Authorization" not in request.headers or request.headers["Authorization"] != (f"Bearer {Config.API_KEY}"):
            return {"error": "not authorized"}, 401
        else:
            return fn(*args, **kwargs)

    return wrapper
