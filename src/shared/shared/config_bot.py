"""Definition for bot modules."""

from .config_base import ConfigBase, module_type, param_type
from typing import List
from shared.schema.parameter import ParameterType


class ConfigBot(ConfigBase):
    """Definition for bot modules."""

    def add_default(self) -> List[param_type]:
        """Add default parameters."""
        return [
            param_type(
                "REFRESH_INTERVAL",
                "Refresh interval in minutes (0 to disable)",
                "How often and when is this bot doing its job. Examples:<ul><li>10 --- perform the task every 10 minutes</li><li>10:30"
                " --- perform the task every day at 10:30</li><li>Tuesday,10:30 --- perform the task every Tuesday at 10:30</li></ul>",
                ParameterType.NUMBER,
            )
        ]

    def __init__(self):
        """Initialize bot modules."""
        self.modules: List[module_type] = []

        mod = module_type("ANALYST_BOT", "Analyst Bot", "Bot for news items analysis")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("SOURCE_GROUP", "Source Group", "OSINT Source group to inspect", ParameterType.STRING),
                param_type("REGULAR_EXPRESSION", "Regular Expression", "Regular expression for data analysis", ParameterType.STRING),
                param_type("ATTRIBUTE_NAME", "Attribute name", "Name of attribute for extracted data", ParameterType.STRING),
            ]
        )
        self.modules.append(mod)

        mod = module_type("GROUPING_BOT", "Grouping Bot", "Bot for grouping news items into aggregates")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("SOURCE_GROUP", "Source Group", "OSINT Source group to inspect", ParameterType.STRING),
                param_type("REGULAR_EXPRESSION", "Regular Expression", "Regular expression for items matching", ParameterType.STRING),
            ]
        )
        self.modules.append(mod)

        mod = module_type("WORDLIST_UPDATER_BOT", "Wordlist Updater Bot", "Bot for updating word lists")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("WORD_LIST_ID", "Word list ID", "ID of word list to update", ParameterType.NUMBER),
                param_type("WORD_LIST_CATEGORY", "Word list category name", "Name of category of word entries", ParameterType.STRING),
                param_type("DATA_URL", "Data URL or file path", "Source for words", ParameterType.STRING),
                param_type("FORMAT", "Data format", "Format of words source", ParameterType.STRING),
                param_type(
                    "DELETE", "Delete before update (yes or no)", "Delete word entries before update, default yes", ParameterType.STRING
                ),
            ]
        )
        self.modules.append(mod)
