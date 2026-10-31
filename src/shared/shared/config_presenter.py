"""Definition for presenter modules."""

from shared.schema.parameter import ParameterType

from .config_base import ConfigBase, ModuleType, ParamType


class ConfigPresenter(ConfigBase):
    """Configuration for presenter modules."""

    def __init__(self) -> None:
        """Initialize presenter modules."""
        self.modules: list[ModuleType] = []

        mod = ModuleType("HTML_PRESENTER", "HTML Presenter", "Presenter for generating html documents")
        mod.parameters = [
            ParamType(
                "HTML_TEMPLATE_PATH",
                "Path to template",
                "Path to HTML template file",
                ParameterType.STRING,
                "/app/templates/template.html",
                translate=True,
            ),
        ]
        self.modules.append(mod)

        mod = ModuleType("JSON_PRESENTER", "JSON Presenter", "Presenter for generating JSON files")
        mod.parameters = [ParamType("JSON_INDENT", "JSON indent", "Indentation of JSON output", ParameterType.NUMBER, "4")]
        self.modules.append(mod)

        mod = ModuleType("MESSAGE_PRESENTER", "MESSAGE Presenter", "Presenter for generating message title and body")
        mod.parameters = [
            ParamType(
                "TITLE_TEMPLATE_PATH",
                "Path to Title template",
                "Path of message title template file",
                ParameterType.STRING,
                "/app/templates/email_subject_template.txt",
                translate=True,
            ),
            ParamType(
                "BODY_TEMPLATE_PATH",
                "Path to Body template",
                "Path to message body template file",
                ParameterType.STRING,
                "/app/templates/email_body_template.txt",
                translate=True,
            ),
            ParamType(
                "HEADERS_TEMPLATE_PATH",
                "Path to Headers template",
                "Optional. Path to a message headers template file. Each rendered 'X-Name: value' line becomes a "
                "custom mail header; repeat a name to send several values. Leave empty to send no custom headers. "
                "Example: /app/templates/email_headers_template.txt",
                ParameterType.STRING,
                translate=True,
            ),
            ParamType(
                "ATTACHMENT_TEMPLATE_PATH",
                "Path to PDF attachment template",
                "Path to PDF template file",
                ParameterType.STRING,
                translate=True,
            ),
            ParamType(
                "ATTACHMENT_FILE_NAME",
                "Attachment file name",
                "Leave empty for default file name 'file_YYYYmmddHHMMSS'. Alternatively, you may specify a custom file name or "
                "provide a template string. Example: my_report_{{ data.product.title }}",
                ParameterType.STRING,
                translate=True,
            ),
        ]
        self.modules.append(mod)

        mod = ModuleType("MISP_PRESENTER", "MISP Presenter", "Presenter for generating MISP platform")
        mod.parameters = [
            ParamType(
                "MISP_TEMPLATE_PATH",
                "Path to template",
                "Path to MISP template file",
                ParameterType.STRING,
                "/app/templates/misp.json",
                translate=True,
            ),
        ]
        self.modules.append(mod)

        mod = ModuleType("PDF_PRESENTER", "PDF Presenter", "Presenter for generating PDF documents")
        mod.parameters = [
            ParamType(
                "PDF_TEMPLATE_PATH",
                "Path to template",
                "Path to PDF template file",
                ParameterType.STRING,
                "/app/templates/pdf_template.html",
                translate=True,
            ),
            ParamType(
                "PDF_FILE_NAME",
                "Pdf file name",
                "Leave empty for default file name 'product.title'. Alternatively, you may specify a custom file name or "
                "provide a template string. Example: my_report_{{ data.product.title }}",
                ParameterType.STRING,
                translate=True,
            ),
        ]
        self.modules.append(mod)

        mod = ModuleType("TEXT_PRESENTER", "TEXT Presenter", "Presenter for generating text documents")
        mod.parameters = [
            ParamType(
                "TEXT_TEMPLATE_PATH",
                "Path to template",
                "Path to TEXT template file",
                ParameterType.STRING,
                "/app/templates/template-show-all-data.txt",
                translate=True,
            ),
        ]
        self.modules.append(mod)
