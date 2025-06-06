"""Module for the TEXT presenter.

Returns:
    dict: The presenter output containing the mime type and data of the generated text document.
"""

import os
from base64 import b64encode
import jinja2

from .base_presenter import BasePresenter
from shared.config_presenter import ConfigPresenter


class TEXTPresenter(BasePresenter):
    """Presenter for generating text documents.

    This presenter is responsible for generating text documents based on a text template.

    Arguments:
        BasePresenter (class): The base presenter class.

    Returns:
        dict: The presenter output containing the mime type and data of the generated text document.
    """

    type = "TEXT_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input):
        """Generate the output text based on the presenter input.

        Arguments:
            presenter_input (PresenterInput): The input data for the presenter.

        Returns:
            dict: The presenter output containing the mime type and the generated text data.
        """
        try:
            head, tail = os.path.split(presenter_input.param_key_values["TEXT_TEMPLATE_PATH"])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            BasePresenter.load_filters(env)

            func_dict = {
                "vars": vars,
            }

            template = env.get_template(tail)
            template.globals.update(func_dict)

            output_text = template.render(data=input_data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode("UTF-8")

            presenter_output = {"mime_type": "text/plain", "data": data}

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
            return presenter_output
