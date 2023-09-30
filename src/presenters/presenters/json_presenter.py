"""Presenter outputing JSON file.

Returns:
    _type_: _description_
"""
from base64 import b64encode
import json

from .base_presenter import BasePresenter
from shared.schema.parameter import Parameter, ParameterType


class JSONPresenter(BasePresenter):
    """Class for JSON presenter.

    Arguments:
        BasePresenter -- Superclass

    Returns:
        _description_
    """

    type = "JSON_PRESENTER"
    name = "JSON Presenter"
    description = "Presenter for generating JSON files"

    parameters = [Parameter(0, "JSON_INDENT", "JSON indent", "Indentation of JSON output", ParameterType.NUMBER)]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):
        """Generate method.

        Args:
            presenter_input (_type_): _description_

        Returns:
            _type_: _description_
        """
        try:
            indent = int(presenter_input.parameter_values_map["JSON_INDENT"])
        except ValueError:
            indent = 4

        try:
            input_data = BasePresenter.generate_input_data(presenter_input)
            json_object = json.dumps(input_data, sort_keys=True, indent=indent)
            base64_bytes = b64encode(json_object.encode())
            data = base64_bytes.decode("UTF-8")

            presenter_output = {"mime_type": "application/json", "data": data}
            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output = {"mime_type": "text/plain", "data": b64encode(("ERROR\n" + str(error)).encode()).decode("UTF-8")}
            return presenter_output
