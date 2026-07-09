"""Gunicorn entrypoint module.

The shared Taranis-NG start scripts launch ``$MODULE_NAME:$VARIABLE_NAME``
(defaults ``run:app``), so expose the Flask application object here.
"""

from lib.web.app import app

__all__ = ["app"]
