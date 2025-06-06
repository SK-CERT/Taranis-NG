"""Definition for presenter modules."""

from .config_base import ConfigBase, module_type, param_type
from typing import List
from shared.schema.parameter import ParameterType


class ConfigPresenter(ConfigBase):
    """Configuration for presenter modules."""

    def __init__(self):
        """Initialize presenter modules."""
        self.modules: List[module_type] = []

        mod = module_type("HTML_PRESENTER", "HTML Presenter", "Presenter for generating html documents")
        mod.parameters = [
            param_type(
                "HTML_TEMPLATE_PATH",
                "Path to template",
                "Path to HTML template file",
                ParameterType.STRING,
                "/app/templates/template.html",
            )
        ]
        self.modules.append(mod)

        mod = module_type("JSON_PRESENTER", "JSON Presenter", "Presenter for generating JSON files")
        mod.parameters = [param_type("JSON_INDENT", "JSON indent", "Indentation of JSON output", ParameterType.NUMBER, "4")]
        self.modules.append(mod)

        mod = module_type("MESSAGE_PRESENTER", "MESSAGE Presenter", "Presenter for generating message title and body")
        mod.parameters = [
            param_type(
                "TITLE_TEMPLATE_PATH",
                "Path to Title template",
                "Path of message title template file",
                ParameterType.STRING,
                "/app/templates/email_subject_template.txt",
            ),
            param_type(
                "BODY_TEMPLATE_PATH",
                "Path to Body template",
                "Path to message body template file",
                ParameterType.STRING,
                "/app/templates/email_body_template.txt",
            ),
            param_type("ATTACHMENT_TEMPLATE_PATH", "Path to PDF attachment template", "Path to PDF template file", ParameterType.STRING, ""),
        ]
        self.modules.append(mod)

        mod = module_type("MISP_PRESENTER", "MISP Presenter", "Presenter for generating MISP platform")
        mod.parameters = [
            param_type(
                "MISP_TEMPLATE_PATH",
                "Path to template",
                "Path to MISP template file",
                ParameterType.STRING,
                "/app/templates/misp.json",
            )
        ]
        self.modules.append(mod)

        mod = module_type("PDF_PRESENTER", "PDF Presenter", "Presenter for generating PDF documents")
        mod.parameters = [
            param_type(
                "PDF_TEMPLATE_PATH", "Path to template", "Path to PDF template file", ParameterType.STRING, "/app/templates/pdf_template.html"
            )
        ]
        self.modules.append(mod)

        mod = module_type("TEXT_PRESENTER", "TEXT Presenter", "Presenter for generating text documents")
        mod.parameters = [
            param_type(
                "TEXT_TEMPLATE_PATH",
                "Path to template",
                "Path to TEXT template file",
                ParameterType.STRING,
                "/app/templates/template-show-all-data.txt",
            )
        ]
        self.modules.append(mod)
