"""PDF Presenter.

Returns:
    dict: mime type and base64 encoded data of the generated PDF document
"""

import io
import jinja2

from base64 import b64encode
from weasyprint import HTML

from .base_presenter import BasePresenter
from shared.config_presenter import ConfigPresenter


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

    def generate(self, presenter_input):
        """Generate PDF document.

        Args:
            presenter_input (_type_): Parameters from settings

        Returns:
            dict: mime type and base64 encoded data of the generated PDF document
        """
        try:
            template_path = presenter_input.param_key_values["PDF_TEMPLATE_PATH"]
            head, tail = BasePresenter.resolve_template_path(template_path)

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            BasePresenter.load_filters(env)
            pdf = env.get_template(tail)
            output_text = pdf.render(data=input_data)
            pdf_buffer = io.BytesIO()
            HTML(string=output_text).write_pdf(target=pdf_buffer)
            pdf_buffer.seek(0)

            encoding = "UTF-8"
            byte_content = pdf_buffer.read()
            base64_bytes = b64encode(byte_content)
            data = base64_bytes.decode(encoding)

            presenter_output = {"mime_type": "application/pdf", "data": data}

            return presenter_output

        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode(("TEMPLATING ERROR\n" + str(error)).encode()).decode("UTF-8")}
            return presenter_output
