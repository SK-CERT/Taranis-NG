"""PDF Presenter.

Returns:
    dict: mime type and base64 encoded data of the generated PDF document

"""

import os
from base64 import b64encode

from shared.config_presenter import ConfigPresenter

from shared import common

from .base_presenter import BasePresenter

JINJA_TEMPLATES_PATH = os.getenv("JINJA_TEMPLATES_PATH", "/app/templates")


class PDFPresenter(BasePresenter):
    """PDF Presenter class.

    Args:
        BasePresenter (class): Base presenter class

    """

    presenter_type = "PDF_PRESENTER"
    config = ConfigPresenter().get_config_by_type(presenter_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input: dict) -> dict:
        """Generate PDF document.

        Args:
            presenter_input (dict): Parameters from settings

        Returns:
            dict: mime type and base64 encoded data of the generated PDF document

        """
        try:
            template_path = presenter_input.param_key_values["PDF_TEMPLATE_PATH"]
            pdf_file_name = common.read_str_parameter("PDF_FILE_NAME", None, presenter_input)

            data = BasePresenter.render_jinja(presenter_input, template_path, escape_html=True, is_pdf=True)
            if pdf_file_name:
                pdf_file_name = BasePresenter.render_jinja(presenter_input, None, pdf_file_name)
            return {"mime_type": "application/pdf", "data": data, "att_file_name": pdf_file_name}

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {
                "mime_type": "text/plain",
                "data": b64encode(("TEMPLATING ERROR\n" + str(error)).encode()).decode("UTF-8"),
            }
