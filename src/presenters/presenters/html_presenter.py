"""HTML Presenter.

Returns:
    A dictionary containing the MIME type and the base64-encoded HTML data.
"""

import jinja2

from base64 import b64encode

from .base_presenter import BasePresenter
from shared.config_presenter import ConfigPresenter


class HTMLPresenter(BasePresenter):
    """Presenter for generating HTML documents.

    Arguments:
        BasePresenter -- The base presenter class.

    Returns:
        A dictionary containing the MIME type and the base64-encoded HTML data.
    """

    type = "HTML_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input):
        """Generate the HTML presentation.

        Arguments:
            presenter_input -- The input data for the presenter.

        Returns:
            A dictionary containing the MIME type and the base64-encoded HTML data.
        """
        try:
            template_path = presenter_input.param_key_values["HTML_TEMPLATE_PATH"]
            head, tail = BasePresenter.resolve_template_path(template_path)
            input_data = BasePresenter.generate_input_data(presenter_input)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            BasePresenter.load_filters(env)
            output_text = env.get_template(tail).render(data=input_data).encode()
            base64_bytes = b64encode(output_text)
            data = base64_bytes.decode("UTF-8")

            presenter_output = {"mime_type": "text/html", "data": data}
            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
            return presenter_output
