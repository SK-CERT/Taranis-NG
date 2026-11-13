"""WebSub (W3C): tell a web's hub that its feeds changed, so subscribers learn it at once.

A web with a hub (``websub_hub`` in its configuration) names it in its feeds (``rel="hub"``).
Feed readers that support WebSub subscribe there instead of polling; when the node's cache is
reset - core does so when a published product, a web or a template changes, and when an
administrator clears it - the node tells the hub which feeds changed. The hub then fetches them
and passes on what is new.

The feeds are the topics the hub knows: every address a reader may have subscribed to, the plain
``/rss``, ``/feed`` and ``/atom`` and, on a web with several languages, each language's. Only first
pages: older pages change when a report is added, but nobody subscribes to them.

Telling the hub is best effort, on a thread of its own: a hub that is down only means readers
learn the news at their next poll.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import requests
from lib.logger import get_logger
from lib.web.site import SiteContext

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = get_logger("websub", silent=True)

_TIMEOUT = 10
FEED_PATHS = ("/rss", "/feed", "/atom")


def topics(web: dict) -> list[str]:
    """The feed addresses of ``web`` a reader may have subscribed to."""
    site = SiteContext(web, "")
    urls = [site.hostname + path for path in FEED_PATHS]
    if len(site.languages) > 1:
        urls += [f"{site.hostname}/{kind}?lang={code}" for code in site.languages for kind in ("rss", "atom")]
    return urls


def notify(webs: Iterable[dict]) -> None:
    """Tell the hub of each enabled web with one that its feeds changed (``hub.mode=publish``)."""
    for web in webs:
        hub = SiteContext(web, "").websub_hub
        if not hub or not web.get("hostname") or not web.get("enabled", True):
            continue
        for topic in topics(web):
            try:
                response = requests.post(hub, data={"hub.mode": "publish", "hub.url": topic}, timeout=_TIMEOUT)
            except requests.RequestException as error:
                logger.warning("WebSub hub %s could not be told about %s: %s", hub, topic, error)
                continue
            if response.status_code >= 400:  # noqa: PLR2004 - any HTTP error
                logger.warning("WebSub hub %s refused %s: HTTP %s", hub, topic, response.status_code)


def notify_in_background(webs: Callable[[], list[dict]]) -> None:
    """Run :func:`notify` on a thread of its own, with the webs ``webs`` returns then."""

    def run() -> None:
        try:
            notify(webs())
        except Exception:  # the thread has no supervisor; never let it die with a traceback
            logger.exception("Telling the WebSub hubs about the changed feeds failed")

    threading.Thread(target=run, daemon=True).start()
