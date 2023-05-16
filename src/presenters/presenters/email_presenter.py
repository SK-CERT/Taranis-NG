"""Create an email presenter.

Returns:
    _description_
"""
import os
from base64 import b64encode
import jinja2
import re


from .base_presenter import BasePresenter
from shared.schema.parameter import Parameter, ParameterType

class EMAILPresenter(BasePresenter):
    """Class for EMAIL presenter.

    Arguments:
        BasePresenter -- Superclass

    Returns:
        _description_
    """

    type = "EMAIL_PRESENTER"
    name = "EMAIL Presenter"
    description = "Presenter for generating email subject, message and signature"

    parameters = [
        Parameter(0, "SUBJECT_TEMPLATE_PATH", "Subject template with its path", "Path of text template file", ParameterType.STRING),
        Parameter(0, "BODY_TEMPLATE_PATH", "Body template with its path", "Path of text template file", ParameterType.STRING),
    ]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):
        """Generate email parts from Jinja templates.

        Arguments:
            presenter_input -- Input data for templating

        Returns:
            presenter_output -- dict with keys mime_type and data with email parts as subkeys
        """
        email_structure = {"subject": "SUBJECT_TEMPLATE_PATH", "body": "BODY_TEMPLATE_PATH"}
        presenter_output = {"mime_type": "email", "data": {}}

        def get_max_tlp(input_data):
            """Get highest TLP from input data.

            Arguments:
                input_data -- Input data for templating
            """
            color_values = {
                            'WHITE': 0,
                            'CLEAR': 1,
                            'GREEN': 2,
                            'AMBER': 3,
                            'AMBER+STRICT': 4,
                            'RED': 5
                            }

            colors = []

            for report in input_data["report_items"]:
                colors.append(report["attrs"]["tlp"])

            max_tlp = max(colors, key=lambda color: color_values.get(color, 0))
            if not max_tlp:
                max_tlp = "CLEAR"
            return max_tlp

        def adjust_links(input_data):
            """Adjust links in input data - adds letter in front of numbers."""

            pattern = r'\[(\d+)\]'

            for report in input_data["report_items"]:
                report["attrs"]["description"] = re.sub(pattern, lambda match: f"[A{match.group(1)}]", report["attrs"]["description"])

            return input_data


        def generate_part(part_name):
            input_data = BasePresenter.generate_input_data(presenter_input)
            max_tlp = get_max_tlp(input_data)
            input_data = adjust_links(input_data)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))
            func_dict = {
                "vars": vars,
            }
            template = env.get_template(tail)
            template.globals.update(func_dict)
            output_text = template.render(data=input_data, max_tlp=max_tlp).encode()
            base64_bytes = b64encode(output_text)
            part = base64_bytes.decode("UTF-8")
            return part

        try:
            for email_part, part_template in email_structure.items():
                head, tail = os.path.split(presenter_input.parameter_values_map[email_structure[email_part]])
                part = generate_part(email_part)
                presenter_output["data"][email_part] = part

            return presenter_output

        except Exception as error:
            BasePresenter.print_exception(self, error)
            presenter_output["data"] = b64encode(("TEMPLATING ERROR\n" + str(error)).encode()).decode("UTF-8")
            return presenter_output
