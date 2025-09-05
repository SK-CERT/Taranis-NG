"""PDF Presenter.

Returns:
    dict: mime type and base64 encoded data of the generated PDF document

"""

import io
import os
from base64 import b64encode

import jinja2
from weasyprint import HTML

from shared.config_presenter import ConfigPresenter

from .base_presenter import BasePresenter

JINJA_TEMPLATES_PATH = os.getenv("JINJA_TEMPLATES_PATH", "/app/templates")


class PDFPresenter(BasePresenter):
    """PDF Presenter class.

    Args:
        BasePresenter (class): Base presenter class

    """

    type = "PDF_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
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
            head, tail = BasePresenter.resolve_template_path(template_path)

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head), autoescape=True)
            BasePresenter.load_filters(env)
            pdf = env.get_template(tail)
            output_text = pdf.render(data=input_data)
            pdf_buffer = io.BytesIO()
            # Restrict resource loading to the template directory
            HTML(string=output_text, base_url=head).write_pdf(target=pdf_buffer)
            pdf_buffer.seek(0)

            encoding = "UTF-8"
            byte_content = pdf_buffer.read()
            base64_bytes = b64encode(byte_content)
            data = base64_bytes.decode(encoding)

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {
                "mime_type": "text/plain",
                "data": b64encode(("TEMPLATING ERROR\n" + str(error)).encode()).decode("UTF-8"),
            }
        else:
            return {"mime_type": "application/pdf", "data": data}
