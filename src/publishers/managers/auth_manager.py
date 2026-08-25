"""Authorization manager for the API.

The check itself lives in :mod:`shared.auth` so all satellites share one policy - this
module only supplies the two service-specific accessors. It used to hold a
byte-identical copy of the decorator, one per service.

Returns:
    wrapper: Wrapper function for the API endpoints.
"""

import os
import ssl

from config import Config
from flask import request
from shared.auth import make_api_key_required

if os.getenv("SSL_VERIFICATION") == "False":
    try:
        _create_unverified_https_context = ssl._create_unverified_context  # noqa: SLF001
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context  # noqa: SLF001


# Both accessors are read per request: Config.API_KEY so a reloaded key is honoured,
# and the header because `request` only exists inside a request context.
api_key_required = make_api_key_required(
    lambda: Config.API_KEY,
    lambda: request.headers.get("Authorization"),
)
