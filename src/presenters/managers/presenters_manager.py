"""Manager of all presenters.

Returns:
    _description_
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from presenters.html_presenter import BasePresenter

from http import HTTPStatus

from shared.schema.presenter import PresenterInputSchema, PresenterOutputSchema

from presenters.html_presenter import HTMLPresenter
from presenters.json_presenter import JSONPresenter
from presenters.message_presenter import MESSAGEPresenter
from presenters.misp_presenter import MISPPresenter
from presenters.pdf_presenter import PDFPresenter
from presenters.text_presenter import TEXTPresenter

presenters = {}


def initialize() -> None:
    """Initialize all presenters."""
    register_presenter(PDFPresenter())
    register_presenter(HTMLPresenter())
    register_presenter(TEXTPresenter())
    register_presenter(MISPPresenter())
    register_presenter(JSONPresenter())
    register_presenter(MESSAGEPresenter())


def register_presenter(presenter: BasePresenter) -> None:
    """Register a presenter.

    Args:
        presenter: Presenter module
    """
    presenters[presenter.presenter_type] = presenter


def get_registered_presenters_info() -> list[dict]:
    """Get info about all presenters.

    Returns:
        List with presenter type as key and info as value
    """
    return [p.get_info() for p in presenters.values()]


def generate(presenter_input_json: dict) -> tuple[dict, HTTPStatus]:
    """Generate.

    Args:
        presenter_input_json: JSON

    Returns:
        Presenter output JSON and HTTP status code
    """
    # print(f"=== PRESENTER INPUT ===\n{json.dumps(presenter_input_json, indent=4)}", flush=True)
    presenter_input_schema = PresenterInputSchema()
    presenter_input = presenter_input_schema.load(presenter_input_json)

    presenter_output = presenters[presenter_input.type].generate(presenter_input)
    if presenter_output is not None:
        presenter_output_schema = PresenterOutputSchema()
        return presenter_output_schema.dump(presenter_output), HTTPStatus.OK

    return {"error": "Generating presenter output failed"}, HTTPStatus.INTERNAL_SERVER_ERROR
