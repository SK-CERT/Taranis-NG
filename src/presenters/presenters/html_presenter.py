"""HTML Presenter.

Returns:
    A dictionary containing the MIME type and the base64-encoded HTML data.
"""

import os
from base64 import b64encode
import jinja2

from .base_presenter import BasePresenter
from shared.config_presenter import ConfigPresenter


class HTMLPresenter(BasePresenter):
    """Presenter for generating HTML documents.

    Arguments:
        BasePresenter -- The base presenter class.

    Returns:
        A dictionary containing the MIME type and the base64-encoded HTML data.
    """

    type = "HTML_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input):
        """Generate the HTML presentation.

        Arguments:
            presenter_input -- The input data for the presenter.

        Returns:
            A dictionary containing the MIME type and the base64-encoded HTML data.
        """
        try:
            head, tail = os.path.split(presenter_input.parameter_values_map["HTML_TEMPLATE_PATH"])
            input_data = BasePresenter.generate_input_data(presenter_input)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            env.filters["strfdate"] = BasePresenter._filter_datetime
            output_text = env.get_template(tail).render(data=input_data).encode()
            base64_bytes = b64encode(output_text)
            data = base64_bytes.decode("UTF-8")

            presenter_output = {"mime_type": "text/html", "data": data}
            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
            return presenter_output
