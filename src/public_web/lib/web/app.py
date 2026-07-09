"""Flask application factory for the public-web service.

Defines the app, wires Jinja filters/globals, registers blueprints and error
handlers, and injects the per-request site context into templates.
"""

from flask import (
    Flask,
    request,
)
from lib import config
from lib.report import get_cvss_severity
from lib.web import (
    do_clean,
    transform_link_references,
    translate_report,
    translate_ui,
)
from lib.web.exceptions import register_error_handlers
from lib.web.management import management_bp
from lib.web.routes import reports_bp
from lib.web.site import current_site

# Flask application definition and the definition of jinja functions.
app = Flask(__name__)
app.jinja_env.filters["clean"] = do_clean
app.jinja_env.globals.update(
    translate_report=translate_report,
    translate_ui=translate_ui,
    transform_link_references=transform_link_references,
    get_cvss_severity=get_cvss_severity,
)

register_error_handlers(app)

# Blueprints
app.register_blueprint(management_bp)
app.register_blueprint(reports_bp)


@app.context_processor
def inject_site() -> dict[str, object]:
    """Inject the current request's site branding + URL into the Jinja templates.

    Branding is resolved per web (by Host header) and per language (see site.py).
    """
    site = current_site()
    return {
        "hostname": site.hostname,
        "metadata": site.metadata,
        "content": site.content,
        "images": site.images,
        "current_url": request.url,
    }


if __name__ == "__main__":
    app.run(debug=not config.is_production())
