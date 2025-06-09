"""Create a message presenter.

Returns:
    _description_
"""

import os
from base64 import b64encode
import jinja2
from shared import common
from .base_presenter import BasePresenter
from shared.config_presenter import ConfigPresenter
from presenters.pdf_presenter import PDFPresenter


class MESSAGEPresenter(BasePresenter):
    """Class for MESSAGE presenter.

    Arguments:
        BasePresenter -- Superclass

    Returns:
        _description_
    """

    type = "MESSAGE_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input):
        """Generate message parts from Jinja templates.

        Arguments:
            presenter_input -- Input data for templating

        Returns:
            presenter_output -- dict with keys mime_type and data with message parts as subkeys
        """
        message_title_template_path = presenter_input.param_key_values["TITLE_TEMPLATE_PATH"]
        message_body_template_path = presenter_input.param_key_values["BODY_TEMPLATE_PATH"]
        att_template_path = common.read_str_parameter("ATTACHMENT_TEMPLATE_PATH", None, presenter_input)
        presenter_output = {"mime_type": "text/plain", "message_title": None, "message_body": None, "data": None}

        def generate_part(template_path):
            head, tail = os.path.split(template_path)
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
            return data

        try:
            presenter_output["message_title"] = generate_part(message_title_template_path)
            presenter_output["message_body"] = generate_part(message_body_template_path)
            if att_template_path:
                presenter_input.param_key_values.update({"PDF_TEMPLATE_PATH": att_template_path})
                pdf_presnter = PDFPresenter()
                pdf_output = pdf_presnter.generate(presenter_input)
                presenter_output["mime_type"] = pdf_output["mime_type"]
                presenter_output["data"] = pdf_output["data"]
            return presenter_output

        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
            return presenter_output
