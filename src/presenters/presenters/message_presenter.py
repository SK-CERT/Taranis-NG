"""Create a message presenter.

Returns:
    _description_
"""

from base64 import b64encode

from shared.config_presenter import ConfigPresenter

from presenters.pdf_presenter import PDFPresenter
from shared import common

from .base_presenter import BasePresenter


class MESSAGEPresenter(BasePresenter):
    """Class for MESSAGE presenter.

    Arguments:
        BasePresenter -- Superclass

    Returns:
        _description_
    """

    presenter_type = "MESSAGE_PRESENTER"
    config = ConfigPresenter().get_config_by_type(presenter_type)
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

        try:
            presenter_output["message_title"] = BasePresenter.render_jinja(presenter_input, message_title_template_path)
            presenter_output["message_body"] = BasePresenter.render_jinja(presenter_input, message_body_template_path)
            if att_file_name:
                presenter_output["att_file_name"] = BasePresenter.render_jinja(presenter_input, None, att_file_name)
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
