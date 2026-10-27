"""Traffic Light Protocol levels, in order, for deciding what may leave the instance.

An AI provider may cap the TLP of the reports whose text it receives (``ai_provider.max_tlp``).
"""

from __future__ import annotations

# Lowest to highest. WHITE is the TLP 1.0 name of CLEAR and still turns up in older reports.
TLP_LEVELS = ("CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED")
_ALIASES = {"WHITE": "CLEAR"}


def normalize(value: object) -> str | None:
    """The TLP level a value names, or None when it names none.

    Args:
        value (object): A stored TLP value such as "amber" or "TLP:RED".

    Returns:
        str | None: One of TLP_LEVELS.
    """
    if not isinstance(value, str):
        return None
    level = value.strip().upper().removeprefix("TLP:")
    level = _ALIASES.get(level, level)
    return level if level in TLP_LEVELS else None


def rank(level: str) -> int:
    """Position of a level in TLP_LEVELS (CLEAR is 0).

    Args:
        level (str): One of TLP_LEVELS.

    Returns:
        int: Its rank.
    """
    return TLP_LEVELS.index(level)


def clean_limit(value: object) -> str | None:
    """Validate a provider's TLP limit; empty means no limit.

    Args:
        value (object): The submitted value.

    Returns:
        str | None: The level, or None for no limit.

    Raises:
        ValueError: If a value was given that is not a TLP level.
    """
    if value is None or value == "":
        return None
    level = normalize(value)
    if level is None:
        msg = f"Unknown TLP level: {value}"
        raise ValueError(msg)
    return level
