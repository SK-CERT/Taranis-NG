"""A failing template must say which template failed.

The MESSAGE presenter renders up to five templates, and a failure comes back to the user
as the rendered product - a "TEMPLATING ERROR" body with no traceback. Naming the template
is the only clue the operator gets. The regression this pins: a body template failing on a
missing import read as though the newly added headers template were at fault.
"""

from __future__ import annotations

import types
from base64 import b64decode
from pathlib import Path

import pytest
from presenters.base_presenter import BasePresenter
from presenters.message_presenter import MESSAGEPresenter

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"


@pytest.fixture(autouse=True)
def _templates_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the template sandbox at the repo, not the container's /app/templates."""
    monkeypatch.setattr(BasePresenter, "JINJA_TEMPLATES_ROOT", str(TEMPLATES_ROOT))


@pytest.fixture
def presenter_input() -> object:
    """A minimal product with one report item carrying one attribute."""
    group_item = types.SimpleNamespace(id=10, title="Report Category", max_occurrence=5)
    report_type = types.SimpleNamespace(
        id=1,
        title="Vulnerability Report",
        description="",
        attribute_groups=[types.SimpleNamespace(attribute_group_items=[group_item])],
    )
    report = types.SimpleNamespace(
        title="R1",
        title_prefix="",
        uuid="u",
        created=None,
        last_updated=None,
        report_item_type_id=1,
        news_item_aggregates=[],
        attributes=[types.SimpleNamespace(attribute_group_item_id=10, value="Ransomware", value_description="")],
    )
    product = types.SimpleNamespace(
        title="P",
        description="d",
        product_type="T",
        product_type_description="",
        user=types.SimpleNamespace(name="Analyst"),
        id="1",
    )
    return types.SimpleNamespace(product=product, reports=[report], report_types=[report_type], param_key_values={})


def error_text(output: dict) -> str:
    """The TEMPLATING ERROR body a failed render returns."""
    return b64decode(output["data"]).decode("UTF-8")


def write_template(name: str, body: str) -> str:
    """Write a template inside the sandbox root so resolve_template_path accepts it."""
    path = TEMPLATES_ROOT / name
    path.write_text(body)
    return str(path)


def test_a_failing_body_template_names_the_body_template(presenter_input: object) -> None:
    # The reported case: the body template imports something that does not exist, and the
    # error must not read as though the headers template were at fault.
    body = write_template("_test_broken_body.txt", "{% import 'no_such_file' as missing %}")
    presenter_input.param_key_values = {
        "TITLE_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_subject_template.txt"),
        "BODY_TEMPLATE_PATH": body,
        "HEADERS_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_headers_template.txt"),
    }
    try:
        report = error_text(MESSAGEPresenter().generate(presenter_input))
    finally:
        Path(body).unlink()

    assert "TEMPLATING ERROR in body template" in report
    assert "_test_broken_body.txt" in report
    assert "headers template" not in report


def test_a_failing_headers_template_names_the_headers_template(presenter_input: object) -> None:
    headers = write_template("_test_broken_headers.txt", "{% import 'no_such_file' as missing %}")
    presenter_input.param_key_values = {
        "TITLE_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_subject_template.txt"),
        "BODY_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_body_template.txt"),
        "HEADERS_TEMPLATE_PATH": headers,
    }
    try:
        report = error_text(MESSAGEPresenter().generate(presenter_input))
    finally:
        Path(headers).unlink()

    assert "TEMPLATING ERROR in headers template" in report
    assert "_test_broken_headers.txt" in report


def test_a_missing_headers_template_path_is_not_an_error(presenter_input: object) -> None:
    # Leaving the parameter empty must publish normally with no custom headers.
    presenter_input.param_key_values = {
        "TITLE_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_subject_template.txt"),
        "BODY_TEMPLATE_PATH": str(TEMPLATES_ROOT / "email_body_template.txt"),
    }

    output = MESSAGEPresenter().generate(presenter_input)

    assert output["message_headers"] == []
    assert output["message_body"] is not None
