"""Create a message presenter.

Returns:
    _description_
"""

from base64 import b64encode

import jinja2

from presenters.pdf_presenter import PDFPresenter
from shared import common
from shared.config_presenter import ConfigPresenter

from .base_presenter import BasePresenter


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

    def generate(self, presenter_input: dict) -> dict[str, str]:
        """Generate message parts from Jinja templates.

        Arguments:
            presenter_input (dict): Input data for templating

        Returns:
            presenter_output (dict): with keys mime_type and data with message parts as subkeys
        """
        message_title_template_path = presenter_input.param_key_values["TITLE_TEMPLATE_PATH"]
        message_body_template_path = presenter_input.param_key_values["BODY_TEMPLATE_PATH"]
        att_template_path = common.read_str_parameter("ATTACHMENT_TEMPLATE_PATH", None, presenter_input)
        att_file_name = common.read_str_parameter("ATTACHMENT_FILE_NAME", None, presenter_input)
        presenter_output = {"mime_type": "text/plain", "message_title": None, "message_body": None, "data": None, "att_file_name": None}

        def generate_part(template_path: str, template_string: str | None = None) -> str:
            input_data = BasePresenter.generate_input_data(presenter_input)
            if template_string:
                env = jinja2.Environment(autoescape=False)  # noqa: S701 # no autoescape is safe for plaintext
                BasePresenter.load_filters(env)
                template = env.from_string(template_string)
            else:
                head, tail = BasePresenter.resolve_template_path(template_path)
                env = jinja2.Environment(loader=jinja2.FileSystemLoader(head), autoescape=False)  # noqa: S701 # no autoescape is safe for plaintext
                BasePresenter.load_filters(env)
                template = env.get_template(tail)
            func_dict = {
                "vars": vars,
            }
            template.globals.update(func_dict)
            output_text = template.render(data=input_data).encode()
            base64_bytes = b64encode(output_text)
            return base64_bytes.decode("UTF-8")

        try:
            presenter_output["message_title"] = generate_part(message_title_template_path)
            presenter_output["message_body"] = generate_part(message_body_template_path)
            if att_file_name:
                presenter_output["att_file_name"] = generate_part(None, att_file_name)
            if att_template_path:
                presenter_input.param_key_values.update({"PDF_TEMPLATE_PATH": att_template_path})
                pdf_presenter = PDFPresenter()
                pdf_output = pdf_presenter.generate(presenter_input)
                presenter_output["mime_type"] = pdf_output["mime_type"]
                presenter_output["data"] = pdf_output["data"]
            return presenter_output

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
