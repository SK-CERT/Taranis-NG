"""Module for MISP presenter.

Returns:
    dict: The presenter output containing the MIME type and data.
"""

import json
from base64 import b64encode

from markupsafe import Markup
from shared.config_presenter import ConfigPresenter

from .base_presenter import BasePresenter


def json_string_content(value: object) -> object:
    """Print a template value as the inside of a JSON string.

    The MISP template writes every value between double quotes (``"info": "{{ ... }}"``) and is
    rendered without autoescaping, so a quote or a newline in an analyst's text used to end the
    string: ``x"}], "published": true, "distribution": "3", ...`` published the event to every
    community. Escaping here holds for any MISP template, including the copies of misp.json
    deployments keep in the presenters' templates volume.

    Markup - what ``| tojson`` and ``| safe`` return - is printed as it is: the template chose
    to emit JSON there itself. A Rich Text value is not Markup: its plain text is printed.

    Args:
        value (object): A value the template prints.

    Returns:
        object: The JSON-escaped text, or the Markup unchanged.
    """
    if isinstance(value, Markup):
        return value
    return json.dumps(value if isinstance(value, str) else str(value), ensure_ascii=False)[1:-1]


class MISPPresenter(BasePresenter):
    """Presenter class for generating MISP platform.

    This presenter is responsible for generating the MISP platform using a template file.

    Arguments:
        BasePresenter (class): The base presenter class.

    Returns:
        dict: The presenter output containing the MIME type and data.
    """

    presenter_type = "MISP_PRESENTER"
    config = ConfigPresenter().get_config_by_type(presenter_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input: dict) -> dict[str, str]:
        """Generate the output data based on the presenter input.

        Arguments:
            presenter_input (PresenterInput): The input data for the presenter.

        Returns:
            dict: The presenter output containing the mime type and data.
        """
        try:
            template_path = presenter_input.param_key_values["MISP_TEMPLATE_PATH"]
            input_data = BasePresenter.generate_input_data(presenter_input)
            data = BasePresenter.render_jinja(input_data, template_path, finalize=json_string_content)
            return {"mime_type": "application/json", "data": data}

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
