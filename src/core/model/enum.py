"""Enum class that is using across whole application."""

from enum import Enum


class StateEnum(Enum):
    """Enumeration for different states."""

    PUBLISHED = "published"
    WORK_IN_PROGRESS = "work_in_progress"
    COMPLETED = "completed"


class StateEntityTypeEnum(Enum):
    """Enumeration for different state entity types."""

    REPORT_ITEM = "report_item"
    PRODUCT = "product"
