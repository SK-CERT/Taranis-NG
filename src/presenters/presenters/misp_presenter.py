"""Module for MISP presenter.

Returns:
    dict: The presenter output containing the MIME type and data.
"""

from base64 import b64encode

import jinja2

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

    type = "MISP_PRESENTER"
    config = ConfigPresenter().get_config_by_type(type)
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
            head, tail = BasePresenter.resolve_template_path(template_path)

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head), autoescape=False)  # noqa: S701 # no autoescape is safe for JSON

            output_text = env.get_template(tail).render(data=input_data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode("UTF-8")

            return {"mime_type": "application/json", "data": data}
        except Exception as error:
            BasePresenter.print_exception(self, error)
            return {"mime_type": "text/plain", "data": b64encode((f"TEMPLATING ERROR\n{error}").encode()).decode("UTF-8")}
