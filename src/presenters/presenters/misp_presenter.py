"""Module for MISP presenter.

Returns:
    dict: The presenter output containing the MIME type and data.
"""
import os
from base64 import b64encode
import jinja2

from .base_presenter import BasePresenter
from shared.schema.parameter import Parameter, ParameterType


class MISPPresenter(BasePresenter):
    """Presenter class for generating MISP platform.

    This presenter is responsible for generating the MISP platform using a template file.

    Arguments:
        BasePresenter (class): The base presenter class.

    Returns:
        dict: The presenter output containing the MIME type and data.
    """

    type = "MISP_PRESENTER"
    name = "MISP Presenter"
    description = "Presenter for generating MISP platform"

    parameters = [Parameter(0, "MISP_TEMPLATE_PATH", "MISP template with its path", "Path of MISP template file", ParameterType.STRING)]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):
        """Generate the output data based on the presenter input.

        Arguments:
            presenter_input (PresenterInput): The input data for the presenter.

        Returns:
            dict: The presenter output containing the mime type and data.
        """
        try:
            head, tail = os.path.split(presenter_input.parameter_values_map["MISP_TEMPLATE_PATH"])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            output_text = env.get_template(tail).render(data=input_data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode("UTF-8")

            presenter_output = {"mime_type": "application/json", "data": data}

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
            return presenter_output
