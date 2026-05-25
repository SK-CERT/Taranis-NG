"""HTML Presenter.

Returns:
    A dictionary containing the MIME type and the base64-encoded HTML data.
"""

from base64 import b64encode

from shared.config_presenter import ConfigPresenter

from .base_presenter import BasePresenter


class HTMLPresenter(BasePresenter):
    """Presenter for generating HTML documents.

    Arguments:
        BasePresenter(class): The base presenter class.

    Returns:
        A dictionary containing the MIME type and the base64-encoded HTML data.
    """

    presenter_type = "HTML_PRESENTER"
    config = ConfigPresenter().get_config_by_type(presenter_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input: dict) -> dict[str, str]:
        """Generate the HTML presentation.

        Arguments:
            presenter_input(dict): The input data for the presenter.

        Returns:
            A dictionary containing the MIME type and the base64-encoded HTML data.
        """
        try:
            template_path = presenter_input.param_key_values["HTML_TEMPLATE_PATH"]
            data = BasePresenter.render_jinja(presenter_input, template_path, escape_html=True)
            return {"mime_type": "text/html", "data": data}

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
