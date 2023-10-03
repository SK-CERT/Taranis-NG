"""PDF Presenter.

Returns:
    dict: mime type and base64 encoded data of the generated PDF document
"""
import datetime
import os
import tempfile
from base64 import b64encode
import jinja2
from weasyprint import HTML

from .base_presenter import BasePresenter
from shared.schema.parameter import Parameter, ParameterType


class PDFPresenter(BasePresenter):
    """PDF Presenter class.

    Args:
        BasePresenter (class): Base presenter class
    """

    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    parameters = [Parameter(0, "PDF_TEMPLATE_PATH", "Template path", "Path of header template file", ParameterType.STRING)]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):
        """Generate PDF document.

        Args:
            presenter_input (_type_): Parameters from settings

        Returns:
            dict: mime type and base64 encoded data of the generated PDF document
        """
        try:
            temporary_directory = tempfile.gettempdir() + "/"
            output_html = temporary_directory + "pdf_body.html"
            output_pdf = temporary_directory + "pdf_report__" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".pdf"

            head, tail = os.path.split(presenter_input.parameter_values_map["PDF_TEMPLATE_PATH"])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            env.filters["strfdate"] = BasePresenter._filter_datetime
            pdf = env.get_template(tail)
            output_text = pdf.render(data=input_data)
            with open(output_html, "w") as output_file:
                output_file.write(output_text)

            if not os.path.exists(temporary_directory):
                os.mkdir(temporary_directory)

            # options = {
            #     'dpi': 500,
            #     'page-size': 'A4',
            #     'margin-top': '1.55in',
            #     'margin-right': '0.75in',
            #     'margin-bottom': '1.55in',
            #     'margin-left': '0.75in',
            #     'encoding': "UTF-8",
            #     'header-html': pdf_header_template,
            #     'footer-html': pdf_footer_template,
            #     'custom-header': [
            #         ('Accept-Encoding', 'gzip')
            #     ],
            #     'no-outline': None,
            #     'enable-local-file-access': None
            # }
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
