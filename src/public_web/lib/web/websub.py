"""WebSub (W3C): tell a web's hub that its feeds changed, so subscribers learn it at once.

A web with a hub (``websub_hub`` in its configuration) names it in its feeds (``rel="hub"``).
Feed readers that support WebSub subscribe there instead of polling; when the node's cache is
reset - core does so when a published product, a web or a template changes, and when an
administrator clears it - the node tells the hub which feeds changed. The hub then fetches them
and passes on what is new.

The feeds are the topics the hub knows: every address a reader may have subscribed to, the plain
``/rss``, ``/feed`` and ``/atom`` and, on a web with several languages, each language's; then the
same for each type of reports the web shows (``?type=``, see ``report_types``). Only first pages:
older pages change when a report is added, but nobody subscribes to them.

Telling the hub is best effort, on a thread of its own: a hub that is down only means readers
learn the news at their next poll.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from urllib.parse import quote

import requests
from lib.logger import get_logger
from lib.web.site import SiteContext

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = get_logger("websub", silent=True)

_TIMEOUT = 10
FEED_PATHS = ("/rss", "/feed", "/atom")


def topics(web: dict, types: Iterable[str] = ()) -> list[str]:
    """The feed addresses of ``web`` a reader may have subscribed to; ``types``: the types of reports it shows.

    A type's feed is named as its own address (``rel="self"``) names it: ``type`` before ``lang``.
    """
    site = SiteContext(web, "")
    several = len(site.languages) > 1
    urls = [site.hostname + path for path in FEED_PATHS]
    if several:
        urls += [f"{site.hostname}/{kind}?lang={code}" for code in site.languages for kind in ("rss", "atom")]
    for type_id in types:
        of_type = f"type={quote(str(type_id), safe='')}"
        urls += [f"{site.hostname}/{kind}?{of_type}" for kind in ("rss", "atom")]
        if several:
            urls += [f"{site.hostname}/{kind}?{of_type}&lang={code}" for code in site.languages for kind in ("rss", "atom")]
    return urls


def notify(webs: Iterable[dict], types_of: Callable[[dict], Iterable[str]] | None = None) -> None:
    """Tell the hub of each enabled web with one that its feeds changed (``hub.mode=publish``).

    ``types_of`` gives the types of reports a web shows, whose feeds changed too.
    """
    for web in webs:
        hub = SiteContext(web, "").websub_hub
        if not hub or not web.get("hostname") or not web.get("enabled", True):
            continue
        try:
            types = list(types_of(web)) if types_of is not None else []
        except Exception:  # its reports could not be read: the main feeds are still worth telling
            logger.exception("The types of reports of %s could not be read", web.get("hostname"))
            types = []
        for topic in topics(web, types):
            try:
                response = requests.post(hub, data={"hub.mode": "publish", "hub.url": topic}, timeout=_TIMEOUT)
            except requests.RequestException as error:
                logger.warning("WebSub hub %s could not be told about %s: %s", hub, topic, error)
                continue
            if response.status_code >= 400:  # noqa: PLR2004 - any HTTP error
                logger.warning("WebSub hub %s refused %s: HTTP %s", hub, topic, response.status_code)


def notify_in_background(webs: Callable[[], list[dict]], types_of: Callable[[dict], Iterable[str]] | None = None) -> None:
    """Run :func:`notify` on a thread of its own, with the webs ``webs`` returns then (and ``types_of``)."""

    def run() -> None:
        try:
            notify(webs(), types_of)
        except Exception:  # the thread has no supervisor; never let it die with a traceback
            logger.exception("Telling the WebSub hubs about the changed feeds failed")

    threading.Thread(target=run, daemon=True).start()
