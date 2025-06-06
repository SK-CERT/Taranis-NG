"""PDF Presenter.

Returns:
    dict: mime type and base64 encoded data of the generated PDF document
"""

import os
import tempfile
from base64 import b64encode
import jinja2
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
            output_html = tempfile.NamedTemporaryFile(prefix="pdf_report_", suffix=".html", delete_on_close=False).name
            output_pdf = tempfile.NamedTemporaryFile(prefix="pdf_report_", suffix=".pdf", delete_on_close=False).name
            head, tail = os.path.split(presenter_input.param_key_values["PDF_TEMPLATE_PATH"])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            BasePresenter.load_filters(env)
            pdf = env.get_template(tail)
            output_text = pdf.render(data=input_data)
            with open(output_html, "w") as output_file:
                output_file.write(output_text)

            HTML(output_html).write_pdf(output_pdf)

            encoding = "UTF-8"
            file = output_pdf

            with open(file, "rb") as open_file:
                byte_content = open_file.read()

            base64_bytes = b64encode(byte_content)

            data = base64_bytes.decode(encoding)

            presenter_output = {"mime_type": "application/pdf", "data": data}

            os.remove(output_html)
            os.remove(file)

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode(("TEMPLATING ERROR\n" + str(error)).encode()).decode("UTF-8")}
            return presenter_output
