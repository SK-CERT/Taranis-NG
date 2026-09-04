"""What each OSINT source is doing right now, and when it is next due.

Both are cache, not record. They describe a collector node that is running: the schedule is rebuilt
from scratch whenever a node starts or refreshes, and a run in progress belongs to a process that
may not survive the hour. Storing either in the database would mean serving a promise no node
intends to keep, and would need a sweeper to clean up after a node that died mid-run.

Redis expiry does that work instead. A run marked as collecting stops being collecting once its key
expires, so a node killed halfway through a collection frees its source on its own. Nothing here is
a correctness mechanism: what actually stops two runs colliding on one source is the claim the
collector holds inside its own process. This is what the GUI shows.
"""

import os
from datetime import timedelta

from managers.cache_manager import redis_client
from managers.log_manager import logger

NEXT_RUN_PREFIX = "osint-source:next-run:"
COLLECTING_PREFIX = "osint-source:collecting:"

# Comfortably longer than the node's ~55s heartbeat, so a couple of missed beats do not blank the
# countdown, but short enough that a node which has gone away stops claiming a schedule.
NEXT_RUN_TTL_SECONDS = 300

# How long a run may go unreported before it is assumed dead. Erring short only means the play
# button re-enables early: pressing it then gets a "already collecting" answer from the node, which
# is a graceful way to be wrong.
COLLECTING_TTL_SECONDS = int(timedelta(hours=int(os.getenv("OSINT_SOURCE_COLLECTING_STALE_HOURS", "6"))).total_seconds())


def _decode(value: bytes | str | None) -> str | None:
    return value.decode("utf-8") if isinstance(value, bytes) else value


def set_next_run(source_id: str, next_run: str) -> None:
    """Record when a source is next due.

    Args:
        source_id (str): The OSINT source id.
        next_run (str): An ISO 8601 timestamp.
    """
    try:
        redis_client.set(f"{NEXT_RUN_PREFIX}{source_id}", next_run, ex=NEXT_RUN_TTL_SECONDS)
    except Exception:
        # A countdown is not worth failing a request over.
        logger.exception("Could not cache the next run of an OSINT source")


def get_next_runs(source_ids: list[str]) -> dict[str, str]:
    """Look up when each of the given sources is next due.

    Args:
        source_ids (list): The OSINT source ids to look up.

    Returns:
        (dict): Source id to ISO 8601 timestamp, only for sources that have one.
    """
    if not source_ids:
        return {}
    try:
        values = redis_client.mget([f"{NEXT_RUN_PREFIX}{source_id}" for source_id in source_ids])
    except Exception:
        logger.exception("Could not read the next run of OSINT sources")
        return {}
    return {source_id: _decode(value) for source_id, value in zip(source_ids, values, strict=False) if value}


def mark_collecting(source_id: str) -> None:
    """Record that a run has begun for a source.

    The entry expires on its own, so a collector that dies mid-run does not leave the source
    looking busy forever.

    Args:
        source_id (str): The OSINT source id.
    """
    try:
        redis_client.set(f"{COLLECTING_PREFIX}{source_id}", "1", ex=COLLECTING_TTL_SECONDS)
    except Exception:
        logger.exception("Could not mark an OSINT source as collecting")


def clear_collecting(source_id: str) -> None:
    """Record that a run has finished for a source.

    Args:
        source_id (str): The OSINT source id.
    """
    try:
        redis_client.delete(f"{COLLECTING_PREFIX}{source_id}")
    except Exception:
        logger.exception("Could not clear the collecting state of an OSINT source")


def get_collecting(source_ids: list[str]) -> set[str]:
    """Find which of the given sources are being collected right now.

    Args:
        source_ids (list): The OSINT source ids to look up.

    Returns:
        (set): The ids that have a run in progress.
    """
    if not source_ids:
        return set()
    try:
        values = redis_client.mget([f"{COLLECTING_PREFIX}{source_id}" for source_id in source_ids])
    except Exception:
        logger.exception("Could not read the collecting state of OSINT sources")
        return set()
    return {source_id for source_id, value in zip(source_ids, values, strict=False) if value}


def clear_all() -> None:
    """Forget every cached schedule and every run marked as in progress.

    Called when core starts. Neither half survives a restart usefully: a node rebuilds its schedule
    from scratch, and a run that was in progress belongs to a process nobody can still ask about.

    Clearing the runs matters most when the whole stack goes down together, which is the ordinary
    case - a compose restart takes core and the collector nodes at once. Nothing is then left to
    report those runs finishing, so without this every source caught mid-run would sit there
    claiming to be collecting until its entry expired hours later.

    The cost is small and self-correcting: if a node did survive, its run shows as idle for a
    moment, and a play button pressed in that window is simply told the source is already being
    collected.
    """
    try:
        keys = [key for prefix in (NEXT_RUN_PREFIX, COLLECTING_PREFIX) for key in redis_client.scan_iter(match=f"{prefix}*")]
        if keys:
            redis_client.delete(*keys)
        logger.debug(f"Cleared {len(keys)} cached OSINT source run-state entries")
    except Exception:
        logger.exception("Could not clear the cached OSINT source run state")
