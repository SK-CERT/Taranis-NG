"""The presenter's Jinja environment must be sandboxed.

Report templates are edited by users inside the GUI; news-item content flowing
into them is attacker-controlled OSINT. A plain ``jinja2.Environment`` turns a
malicious template into RCE on the presenter container. These tests pin the two
properties that prevent it:

1. ``SandboxedEnvironment`` blocks attribute/private-dunder escapes.
2. The ``vars`` builtin (which used to be injected as a template global and
   reaches the module namespace) is gone.
"""

from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from jinja2.exceptions import SecurityError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from presenters.base_presenter import BasePresenter


def _render(template_string: str) -> str:
    output = BasePresenter.render_jinja({}, None, template_string=template_string)
    return base64.b64decode(output).decode("UTF-8")


def test_plain_template_string_still_renders() -> None:
    assert _render("hello {{ 'wor' + 'ld' }}") == "hello world"


def test_mro_walk_is_blocked() -> None:
    with pytest.raises(SecurityError):
        _render("{{ ''.__class__.__mro__ }}")


def test_subclasses_escape_is_blocked() -> None:
    with pytest.raises(SecurityError):
        _render("{{ ''.__class__.__mro__[1].__subclasses__() }}")


def test_attr_filter_escape_yields_nothing() -> None:
    # the |attr() variant of the same climb must not hand out the MRO either:
    # it renders empty (no escalation) rather than reachable classes.
    assert _render("{{ ''|attr('__class__')|attr('__mro__') }}") == ""


def test_vars_global_is_gone() -> None:
    # `vars` used to expose the module namespace to the template; removed,
    # it is now an undefined name - indexing it fails as undefined.
    assert _render("{{ vars }}") == ""
    with pytest.raises(UndefinedError):
        _render("{{ vars['os'] }}")


def test_template_path_is_confined_to_the_templates_root() -> None:
    with TemporaryDirectory() as tmp:
        outside = Path(tmp) / "outside.html"
        outside.write_text("secret")
        with pytest.raises(ValueError, match="outside the allowed templates directory"):
            BasePresenter.render_jinja({}, str(outside))


def test_custom_filters_still_registered() -> None:
    assert _render("{{ '2026-08-28' | strfdate(fmtout='%Y/%m/%d') }}") == "2026/08/28"
    assert _render("{{ none | strfdate }}") == ""


def test_html_output_escapes_attacker_markup() -> None:
    """SK-CERT#724: a report attribute must not carry script into the rendered HTML.

    The pentest captured `test<script>alert(1)</script>test1` intact in a
    text/html product. The HTML presenter renders with ``escape_html=True``
    (``html_presenter.py:42``) and no shipped template uses ``|safe``, so the
    payload comes back escaped. This pins that: autoescape is what stands
    between OSINT content and stored XSS, and it is one keyword away from off.
    """
    payload = "test<script>alert(1)</script>test1"
    env = SandboxedEnvironment(autoescape=True)
    BasePresenter.load_filters(env)
    rendered = env.from_string("<td>{{ data.v }}</td>").render(data={"v": payload})

    assert "<script>" not in rendered
    assert rendered == "<td>test&lt;script&gt;alert(1)&lt;/script&gt;test1</td>"


def test_no_shipped_template_disables_escaping() -> None:
    # a single `| safe` in a template would reopen SK-CERT#724 for that report
    templates = Path(__file__).resolve().parents[1] / "templates"
    offenders = [
        path.relative_to(templates)
        for path in templates.rglob("*.html")
        if "|safe" in path.read_text(encoding="utf-8", errors="replace").replace(" ", "")
    ]
    assert not offenders, f"templates bypassing autoescape: {offenders}"
