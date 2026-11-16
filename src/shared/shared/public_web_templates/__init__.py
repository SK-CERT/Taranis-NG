"""Built-in report templates of the public web.

public-web renders every product through a Jinja template: a custom one stored in
core (Configuration -> Public Web -> Report templates) when the product's preset or the
report item type has one, otherwise one of these. They live here, in ``shared``, because both
sides need them: public-web renders them, core shows them read-only in the GUI so an
administrator can start a custom template from one, and validates that a custom
product template extends one of the bases.

The built-ins in ``DEFAULTS`` are what public-web falls back on; an administrator may switch
each of them off to rely on custom templates alone. The base layout and the macros cannot be
switched off: custom templates extend and import them.

They fit the report item types Taranis itself creates: ``item_vulnerability.html`` the
"Vulnerability Report" type as it ships (see ``VULNERABILITY_TYPE``), ``item_generic.html``
any other type. A type changed from these, or a type of one's own, takes a custom template.
"""

from importlib import resources

BUILTIN_PREFIX = "builtin/"

# A custom product template must extend one of these; the base decides, per ``view``,
# which of its blocks the page asks for (detail page, homepage entry, RSS text).
PRODUCT_BASES = ("builtin/product_base.html", "builtin/product_vulnerability.html")

# The built-ins public-web renders a product or a report item with when it has no custom
# template, which an administrator may switch off: off, public-web does not show a product
# whose preset has no template of its own (product_vulnerability), and renders a report item
# whose type has none with the next built-in that is on - the vulnerability one falls back on
# the generic one - or leaves it out when none is.
DEFAULTS = (
    "builtin/product_vulnerability.html",
    "builtin/item_vulnerability.html",
    "builtin/item_generic.html",
)

# The title of the report item type item_vulnerability.html is for: the one Taranis creates.
VULNERABILITY_TYPE = "Vulnerability Report"

# The parts of a product a page renders, passed to product templates as ``view``.
VIEWS = ("detail", "summary", "rss")

# Every filter public-web registers for report templates. Core compiles a custom
# template against these names on save, so a misspelt filter is reported in the form
# instead of breaking the public page; public-web's tests pin its registry to this list.
FILTER_NAMES = (
    "affected_system",
    "as_list",
    "capitalize_first",
    "clean",
    "clean_rich",
    "cvss_calculator_url",
    "cvss_score",
    "cvss_severity",
    "fix_spaces",
    "iso_date",
    "link_refs",
    "regex_replace",
    "safe_url",
    "single",
    "strfdate",
    "tlp_color",
    "truncate_on_symbol",
    "ymd_date",
)


def builtin_sources() -> dict[str, str]:
    """Return every built-in template's source, keyed by its loader name (``builtin/<file>``)."""
    root = resources.files(__name__)
    return {
        f"{BUILTIN_PREFIX}{entry.name}": entry.read_text(encoding="utf-8")
        for entry in sorted(root.iterdir(), key=lambda entry: entry.name)
        if entry.name.endswith(".html")
    }
