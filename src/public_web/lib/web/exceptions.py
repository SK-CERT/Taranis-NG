"""Flask error handlers for the public-web service.

Maps HTTP error codes to custom error templates, and logs unexpected internal
server errors and mails them to the configured admin recipients.
"""

from datetime import UTC, datetime
from traceback import TracebackException

from flask import (
    Flask,
    render_template,
    request,
)
from lib import (
    config,
    send_mail,
)
from lib.logger import get_logger
from werkzeug.exceptions import HTTPException

logger = get_logger("web", silent=True)


def register_error_handlers(app: Flask) -> None:
    """Registers all error handlers for the Flask application."""

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(503)
    def http_exceptions_not_mailed(e: HTTPException) -> tuple[str, int]:
        """Handle codes and HTTP exceptions that should not be mailed."""
        return (
            render_template("error.html", code=e.code, name=e.name, desc=e.description),
            e.code or 400,
        )

    @app.errorhandler(Exception)
    def internal_server_error(e: Exception) -> tuple[str, int]:
        """Handle errors and exceptions that occurred in the application.

        A custom web page is shown to the user (error template). Exceptions are
        also logged, and mailed to admins - the mail alone is lost when no mail
        server is reachable.
        """
        code = e.code if (hasattr(e, "code") and e.code is not None) else 500
        logger.error("Unexpected exception (HTTP %s) on %s", code, request.full_path, exc_info=e)
        traceback = "".join(TracebackException.from_exception(e).format())
        send_mail(
            f"Unexpected Exception (HTTP {code}) occurred on the "
            f"web at {datetime.now(UTC)} UTC."
            f"\n\nRequest: {request.full_path}\n\nTraceback: {traceback}",
            "[public-web] Internal server error",
            recipients=config.admin_mail(),
        )
        name = e.name if hasattr(e, "name") else None
        description = e.description if hasattr(e, "description") else None
        return (
            render_template("error.html", code=code, name=name, desc=description),
            code,
        )
