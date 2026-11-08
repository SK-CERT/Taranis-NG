"""API Manager to initialize all API endpoints."""

import re

from api import (
    analyze,
    assess,
    assets,
    auth,
    bots,
    collectors,
    config,
    dashboard,
    isalive,
    notifications,
    public_web,
    publish,
    remote,
    sse,
    state,
    tag,
    traefik,
    user,
)
from flask import request
from flask_restful import Api
from managers import log_manager
from managers.db_manager import db
from marshmallow import ValidationError
from sqlalchemy.exc import DataError, IntegrityError

# A model built from a loaded schema (``Model(**data)`` in a ``post_load``) without the fields its
# constructor needs: the request left them out.
_CONSTRUCTOR_ARGUMENTS = re.compile(r"__init__\(\) (missing \d+ required|got an unexpected keyword argument)")


class SafeErrorApi(Api):
    """``Api`` that will not echo a rejected request body back to the client.

    ``flask_restful.Api.handle_error`` builds the error response from
    ``getattr(e, "data", ...)`` (flask_restful/__init__.py:340). Marshmallow's
    ``ValidationError`` sets ``.data`` to the *input it just rejected*, so any
    schema load that escapes a resource returns the whole request body - which
    for ``POST /config/users`` is the new account's cleartext password, and
    elsewhere API keys, client secrets and tokens. It is also a 500 for what is
    a client mistake.

    Both are fixed here rather than at the ~46 ``schema.load()`` call sites,
    because one missed call site reintroduces the leak.
    """

    def handle_error(self, e: Exception) -> object:
        """Turn a schema rejection into a 400 and an integrity violation into a 409.

        Resources that do not catch their own errors (user delete, the asset endpoints)
        would otherwise answer an IntegrityError with a 500, leaving the GUI unable to tell
        a record that is still referenced from a server fault.

        Both are logged, like any other failed request: a rejected payload is usually a
        client (often the GUI) sending something the schema does not take, and answering
        it quietly left nothing to find when a user reported "it did not save". The log
        names the fields and what was wrong with them, and the request body goes through
        the usual redaction of passwords and keys; it is never sent back to the client.
        """
        if isinstance(e, ValidationError):
            messages = e.normalized_messages()
            _log_safely(f"Request rejected, invalid fields: {', '.join(_field_names(messages))}", e)
            return self.make_response({"error": "Invalid request", "validation": messages}, 400)
        if isinstance(e, DataError):
            # A value the database cannot take: a NUL character in a text, a number out of range.
            db.session.rollback()
            _log_safely("Request rejected, a value the database cannot store", e)
            return self.make_response({"error": "A value in the request is not allowed (out of range, or a NUL character)"}, 400)
        if isinstance(e, TypeError) and _is_constructor_binding(e):
            _log_safely(f"Request rejected, incomplete: {e}", e)
            return self.make_response({"error": "Invalid request: required fields are missing or unknown"}, 400)
        if isinstance(e, IntegrityError):
            msg = (
                "The record is still in use and could not be deleted"
                if request.method == "DELETE"
                else "The change conflicts with existing data"
            )
            _log_safely(msg, e)
            return self.make_response({"error": msg}, 409)
        return super().handle_error(e)


def _is_constructor_binding(error: TypeError) -> bool:
    """Whether ``error`` is a constructor call failing on its arguments, not something raised inside it.

    Python raises the binding error in the caller's frame: the traceback ends in the function that
    made the call. One raised by the constructor's own code ends deeper, and stays a 500.
    """
    if not _CONSTRUCTOR_ARGUMENTS.search(str(error)):
        return False
    frame = error.__traceback__
    while frame is not None and frame.tb_next is not None:
        frame = frame.tb_next
    return frame is not None and frame.tb_frame.f_code.co_name == "make"


def _log_safely(detail: str, exception: Exception) -> None:
    """Record a rejected request in the activity log; a failure to log must not turn the answer into a 500."""
    try:
        log_manager.store_data_error_activity(None, detail, exception)
    except Exception:
        log_manager.logger.exception(f"Could not log a rejected request: {detail}")


def _field_names(messages: object, prefix: str = "") -> list[str]:
    """The fields a schema rejected, nested ones dotted (``deliveries.0.language``), for the log."""
    if not isinstance(messages, dict):
        return [prefix or "_schema"]
    names: list[str] = []
    for key, value in messages.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            names.extend(_field_names(value, name))
        else:
            names.append(name)
    return names


def _reject_scalar_json_body() -> tuple[dict, int] | None:
    """Refuse a JSON body that is a bare string, number or boolean: every endpoint wants an object or a list.

    Handlers call ``request.json.get(...)``, which failed with AttributeError (a 500) on such a body.
    """
    if request.method in ("POST", "PUT", "PATCH") and request.is_json:
        body = request.get_json(silent=True)
        if body is not None and not isinstance(body, dict | list):
            return {"error": "The request body must be a JSON object"}, 400
    return None


def initialize(app: object) -> None:
    """Initialize all API endpoints."""
    app.before_request(_reject_scalar_json_body)
    api = SafeErrorApi(app)

    assess.initialize(api)
    auth.initialize(api)
    collectors.initialize(api)
    isalive.initialize(api)
    config.initialize(api)
    sse.initialize(api)
    analyze.initialize(api)
    publish.initialize(api)
    public_web.initialize(api)
    user.initialize(api)
    assets.initialize(api)
    bots.initialize(api)
    remote.initialize(api)
    dashboard.initialize(api)
    state.initialize(api)
    tag.initialize(api)
    traefik.initialize(api)
    notifications.initialize(api)
