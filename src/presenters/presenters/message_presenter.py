"""Create a message presenter.

Returns:
    _description_
"""

from base64 import b64decode, b64encode
from pathlib import Path

from shared.config_presenter import ConfigPresenter

from presenters.pdf_presenter import PDFPresenter
from shared import common, mail_headers

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

    def generate(self, presenter_input: dict) -> dict[str, object]:
        """Generate message parts from Jinja templates.

        Arguments:
            presenter_input (dict): Input data for templating

        Returns:
            presenter_output (dict): with keys mime_type and data with message parts as subkeys
        """
        message_title_template_path = presenter_input.param_key_values["TITLE_TEMPLATE_PATH"]
        message_body_template_path = presenter_input.param_key_values["BODY_TEMPLATE_PATH"]
        headers_template_path = common.read_str_parameter("HEADERS_TEMPLATE_PATH", None, presenter_input)
        att_template_path = common.read_str_parameter("ATTACHMENT_TEMPLATE_PATH", None, presenter_input)
        att_file_name = common.read_str_parameter("ATTACHMENT_FILE_NAME", None, presenter_input)
        # `mime_type` describes the optional attachment — the PDF branch below overwrites it — so the
        # message body has to declare its own content type. Without it the EMAIL publisher is left to
        # sniff the body, and content-sniffing misreads plain text that merely contains a "<p"-like
        # placeholder (e.g. "port <port_numbers>") as HTML, collapsing every newline in the client.
        body_suffix = Path(message_body_template_path).suffix.lower()
        presenter_output = {
            "mime_type": "text/plain",
            "message_body_mime_type": "text/html" if body_suffix in (".html", ".htm") else "text/plain",
            "message_title": None,
            "message_body": None,
            "data": None,
            "att_file_name": None,
            "message_headers": [],
        }

        # Which template we are on, so a failure names it. This presenter renders up to five,
        # and the error reaches the user as the rendered product with no traceback: without
        # this, "'variables' not found" gives no clue which template asked for 'variables'.
        rendering = "the input data"

        try:
            input_data = BasePresenter.generate_input_data(presenter_input)
            rendering = f"title template '{message_title_template_path}'"
            presenter_output["message_title"] = BasePresenter.render_jinja(input_data, message_title_template_path)
            rendering = f"body template '{message_body_template_path}'"
            presenter_output["message_body"] = BasePresenter.render_jinja(input_data, message_body_template_path)
            if headers_template_path:
                rendering = f"headers template '{headers_template_path}'"
                # render_jinja base64-encodes every render, so decode our own output back to the
                # header block. Parsing here rather than in the publisher means the sanitizing
                # happens where untrusted attribute text first becomes a protocol element, and a
                # broken headers template surfaces in the product preview.
                rendered_headers = b64decode(BasePresenter.render_jinja(input_data, headers_template_path)).decode("UTF-8")
                presenter_output["message_headers"] = mail_headers.parse_header_block(rendered_headers)
            if att_file_name:
                rendering = f"attachment file name template '{att_file_name}'"
                presenter_output["att_file_name"] = BasePresenter.render_jinja(input_data, None, att_file_name)
            if att_template_path:
                rendering = f"attachment template '{att_template_path}'"
                presenter_input.param_key_values.update({"PDF_TEMPLATE_PATH": att_template_path})
                pdf_presenter = PDFPresenter()
                pdf_output = pdf_presenter.generate(presenter_input)
                presenter_output["mime_type"] = pdf_output["mime_type"]
                presenter_output["data"] = pdf_output["data"]
            return presenter_output

        except Exception as error:
            BasePresenter.print_exception(self, error)
            report = f"TEMPLATING ERROR in {rendering}\n{error}"
            return {"mime_type": "text/plain", "data": b64encode(report.encode()).decode("UTF-8")}
