"""API Manager to initialize all API endpoints."""

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
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError


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
        if isinstance(e, IntegrityError):
            msg = (
                "The record is still in use and could not be deleted"
                if request.method == "DELETE"
                else "The change conflicts with existing data"
            )
            _log_safely(msg, e)
            return self.make_response({"error": msg}, 409)
        return super().handle_error(e)


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


def initialize(app: object) -> None:
    """Initialize all API endpoints."""
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
