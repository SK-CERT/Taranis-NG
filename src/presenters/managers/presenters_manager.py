"""Manager of all presenters.

Returns:
    _description_
"""
from presenters.pdf_presenter import PDFPresenter
from presenters.html_presenter import HTMLPresenter
from presenters.text_presenter import TEXTPresenter
from presenters.misp_presenter import MISPPresenter
from presenters.json_presenter import JSONPresenter
from presenters.message_presenter import MESSAGEPresenter
from shared.schema.presenter import PresenterInputSchema, PresenterOutputSchema

presenters = {}


def initialize():
    """Initialize all presenters."""
    register_presenter(PDFPresenter())
    register_presenter(HTMLPresenter())
    register_presenter(TEXTPresenter())
    register_presenter(MISPPresenter())
    register_presenter(JSONPresenter())
    register_presenter(MESSAGEPresenter())


def register_presenter(presenter):
    """Register a presenter.

    Arguments:
        presenter -- Presenter module
    """
    presenters[presenter.type] = presenter


def get_registered_presenters_info():
    """Get info about all presenters.

    Returns:
        List with presenter type as key and info as value
    """
    presenters_info = []
    for key in presenters:
        presenters_info.append(presenters[key].get_info())

    return presenters_info


def generate(presenter_input_json):
    """Generate.

    Arguments:
        presenter_input_json -- JSON

    Returns:
        _description_
    """
    presenter_input_schema = PresenterInputSchema()
    presenter_input = presenter_input_schema.load(presenter_input_json)

    presenter_output = presenters[presenter_input.type].generate(presenter_input)

    if presenter_output is not None:
        presenter_output_schema = PresenterOutputSchema()
        return presenter_output_schema.dump(presenter_output)
    else:
        return "", 500
