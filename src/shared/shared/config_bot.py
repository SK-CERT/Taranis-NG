"""Definition for bot modules."""

from shared.schema.parameter import ParameterType

from .config_base import ConfigBase, ModuleType, ParamType


class ConfigBot(ConfigBase):
    """Definition for bot modules."""

    def add_default(self) -> list[ParamType]:
        """Add default parameters."""
        return [
            ParamType(
                "REFRESH_INTERVAL",
                "Refresh interval in minutes (0 to disable)",
                "How often and when is this bot doing its job. Examples:<ul><li>10 --- perform the task every 10 minutes</li><li>10:30"
                " --- perform the task every day at 10:30</li><li>Tuesday,10:30 --- perform the task every Tuesday at 10:30</li></ul>",
                ParameterType.NUMBER,
                "180",
            ),
        ]

    def __init__(self) -> None:
        """Initialize bot modules."""
        self.modules: list[ModuleType] = []

        mod = ModuleType("ANALYST_BOT", "Analyst Bot", "Bot for news items analysis")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("SOURCE_GROUP", "Source Group", "OSINT Source group to inspect (not used)", ParameterType.STRING, "Default"),
                ParamType(
                    "REGULAR_EXPRESSION",
                    "Regular Expression",
                    "Regular expression for data analysis",
                    ParameterType.STRING,
                    "CVE-\\d{4}-\\d+",
                ),
                ParamType("ATTRIBUTE_NAME", "Attribute name", "Name of attribute for extracted data", ParameterType.STRING, "CVE"),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("GROUPING_BOT", "Grouping Bot", "Bot for grouping news items into aggregates")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("SOURCE_GROUP", "Source Group", "OSINT Source group GUID to inspect", ParameterType.STRING),
                ParamType("REGULAR_EXPRESSION", "Regular Expression", "Regular expression for items matching", ParameterType.STRING),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("WORDLIST_UPDATER_BOT", "Wordlist Updater Bot", "Bot for updating word lists")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("WORD_LIST_ID", "Word list ID", "ID of word list to update", ParameterType.NUMBER),
                ParamType("WORD_LIST_CATEGORY", "Word list category name", "Name of category of word entries", ParameterType.STRING),
                ParamType("DATA_URL", "Data URL or file path", "Source for words", ParameterType.STRING),
                ParamType("FORMAT", "Data format", "Format of words source", ParameterType.STRING),
                ParamType(
                    "DELETE",
                    "Delete before update (yes or no)",
                    "Delete word entries before update, default yes",
                    ParameterType.STRING,
                ),
            ],
        )
        self.modules.append(mod)
