"""Module for MISP presenter.

Returns:
    dict: The presenter output containing the MIME type and data.
"""

from base64 import b64encode

from shared.config_presenter import ConfigPresenter

from .base_presenter import BasePresenter


class MISPPresenter(BasePresenter):
    """Presenter class for generating MISP platform.

    This presenter is responsible for generating the MISP platform using a template file.

    Arguments:
        BasePresenter (class): The base presenter class.

    Returns:
        dict: The presenter output containing the MIME type and data.
    """

    presenter_type = "MISP_PRESENTER"
    config = ConfigPresenter().get_config_by_type(presenter_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def generate(self, presenter_input: dict) -> dict[str, str]:
        """Generate the output data based on the presenter input.

        Arguments:
            presenter_input (PresenterInput): The input data for the presenter.

        Returns:
            dict: The presenter output containing the mime type and data.
        """
        try:
            template_path = presenter_input.param_key_values["MISP_TEMPLATE_PATH"]
            data = BasePresenter.render_jinja(presenter_input, template_path)
            return {"mime_type": "application/json", "data": data}

        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
