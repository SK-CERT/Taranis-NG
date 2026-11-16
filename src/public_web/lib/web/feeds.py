"""The web's feeds: RSS 2.0 and Atom (RFC 4287), written from one description of the reports.

A feed page carries the web's newest reports (``feed_page_size``, 50 unless the web says
otherwise); the older ones are on further pages, linked as an RFC 5005 paged feed (``first``,
``previous``, ``next``, ``last``). Each item has the report's summary as plain text and its whole
text as HTML (Atom ``content``, RSS ``content:encoded``), so a reader can show it without the web.
The feed carries the web's logo and icon, a copyright line naming the web's organization, and,
when the web has one, the WebSub hub that tells subscribers about changes as they happen (see
``websub.py``).

Dates: an item's publication is its RSS ``pubDate`` and Atom ``published``; Atom also gives when
it last changed (``updated``). The feed changed last when its most recently changed item did (RSS
``lastBuildDate``, Atom ``updated``); its newest item was published at the channel's ``pubDate``.

Authors: the Atom feed's author is the web's organization, as the report pages name it. Each
item's is the product's author: an Atom entry ``author`` and, since RSS's own ``author`` must be an
e-mail address, a Dublin Core ``dc:creator`` in RSS. A product without one has neither, and its
Atom entry falls back on the feed's author.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from feedgen.ext.base import BaseExtension
from feedgen.feed import FeedGenerator
from lxml import etree

if TYPE_CHECKING:
    from collections.abc import Callable

    from lib.web.site import SiteContext

ATOM_NS = "http://www.w3.org/2005/Atom"

# Both feeds go out as plain XML: browsers show it in a tab (application/rss+xml and
# application/atom+xml they may download), feed readers know RSS from Atom by the content.
# The pages' <link rel="alternate"> say which is which.
FEED_TYPE = "application/xml; charset=utf-8"
# What the feeds say made them. No version: the public web tells it nowhere else either.
GENERATOR = "Taranis-NG"
GENERATOR_URI = "https://github.com/SK-CERT/Taranis-NG"

# An attribute value that is a path on the web itself ("/reports/7", "/static/logo.svg"), which a
# feed reader, reading the HTML elsewhere, needs absolute; "//host/..." is absolute already.
_SITE_PATH = re.compile(r'(\s(?:href|src)=")(/(?!/)[^"]*)"')


def _local_zone() -> ZoneInfo:
    """The zone core keeps its times in: the stack's ``TZ`` (docker/.env), UTC without a valid one.

    Read here rather than from ``shared.common``, which needs packages this image does not have.
    """
    try:
        return ZoneInfo(os.getenv("TZ") or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


TZ = _local_zone()


def this_year() -> int:
    """The year now, in ``TZ``: the feeds' copyright line names it."""
    return datetime.now(TZ).year


def moment(value: str | None) -> datetime | None:
    """A date from core (ISO 8601) as an aware datetime: a naive one is in ``TZ``. None if it is not one."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)


def absolute(base: str, html: str) -> str:
    """``html`` with the web's own paths (``href``/``src`` starting with one ``/``) made absolute."""
    return _SITE_PATH.sub(lambda match: f'{match.group(1)}{base}{match.group(2)}"', html)


class AtomLinks(BaseExtension):
    """Atom's links in an RSS channel (``atom:link``): feedgen writes only ``rel="self"`` there.

    Paging (RFC 5005) and the WebSub hub are announced this way in RSS.
    """

    def __init__(self) -> None:
        """No links until they are given (``links``: ``(rel, href)`` pairs)."""
        self.links: list[tuple[str, str]] = []

    def extend_ns(self) -> dict[str, str]:
        """The Atom namespace, as feedgen declares it."""
        return {"atom": ATOM_NS}

    def extend_rss(self, feed):  # noqa: ANN001, ANN201 - feedgen's lxml element
        """Add the links to the channel."""
        channel = feed[0]
        for rel, href in self.links:
            etree.SubElement(channel, f"{{{ATOM_NS}}}link", href=href, rel=rel)
        return feed

    def extend_atom(self, feed):  # noqa: ANN001, ANN201 - unused: Atom has its own links
        """Atom writes its links itself."""
        return feed


def build(
    site: SiteContext,
    reports: list[dict],
    *,
    page_url: Callable[[int], str],
    page: int,
    pages: int,
    report_url: Callable[[dict], str],
    summary: Callable[[dict], str],
    content: Callable[[dict], str],
) -> tuple[FeedGenerator, datetime | None]:
    """One page of the web's feed, and when it last changed (None when nothing says).

    Args:
        site: The web and language the feed is for.
        reports: The reports on this page, newest first.
        page_url: The absolute address of a page of this feed (1 is the feed itself).
        page: This page.
        pages: How many pages there are.
        report_url: A report's absolute address.
        summary: A report's plain-text summary.
        content: A report's whole text as HTML.
    """
    fg = FeedGenerator()
    fg.load_extension("dc", atom=False, rss=True)
    fg.register_extension("atomlinks", AtomLinks, None, atom=False, rss=True)
    fg.generator(GENERATOR, uri=GENERATOR_URI)
    title = site.metadata.get("rss_title", "")
    fg.id(page_url(1))
    fg.title(title)
    fg.description(site.metadata.get("rss_description", ""))
    fg.language(site.language)

    organization = site.content.get("organization") or site.metadata.get("site_name") or site.hostname
    organization_url = site.content.get("organization_url") or ""
    fg.author({"name": organization, **({"uri": organization_url} if organization_url.startswith(("http://", "https://")) else {})})
    fg.rights(f"© {this_year()} {organization}")
    logo, icon = (site.image_url(kind) for kind in ("logo", "favicon"))
    if logo:
        # RSS <image> and Atom <logo>.
        fg.image(url=absolute_url(site.hostname, logo), title=title or organization, link=site.hostname)
    if icon:
        fg.icon(absolute_url(site.hostname, icon))

    # RFC 5005 paging, when there is more than one page.
    links = [("first", page_url(1)), ("last", page_url(pages))] if pages > 1 else []
    if page > 1:
        links.append(("previous", page_url(page - 1)))
    if page < pages:
        links.append(("next", page_url(page + 1)))
    if site.websub_hub:
        links.append(("hub", site.websub_hub))
    fg.link(href=page_url(page), rel="self")
    for rel, href in links:
        fg.link(href=href, rel=rel)
    fg.atomlinks.links = links
    # Last: feedgen takes the last link as the RSS channel's <link>, which is the web itself.
    fg.link(href=site.hostname, rel="alternate")

    published_dates, updated_dates = [], []
    # add_entry() adds items in a reverse order (the first added item will be
    # the last in the feed), that's why reversed() is needed.
    for report in reversed(reports):
        link = report_url(report)
        fe = fg.add_entry()
        fe.guid(link, permalink=True)
        fe.title(report["title"])
        fe.link(href=link)
        fe.description(summary(report), isSummary=True)
        fe.content(absolute(site.hostname, content(report)), type="html")
        if author := report.get("author"):
            fe.author({"name": author})
            fe.dc.dc_creator(author)
        published = moment(report.get("published_at"))
        updated = max((value for value in (moment(report.get("updated_at")), published) if value), default=None)
        if published:
            fe.published(published)
            published_dates.append(published)
        if updated:
            fe.updated(updated)
            updated_dates.append(updated)
    changed = max(updated_dates, default=None)
    if changed:
        fg.updated(changed)
    if published_dates:
        fg.pubDate(max(published_dates))
    return fg, changed


def absolute_url(base: str, url: str) -> str:
    """``url`` as an absolute address: a path on the web gets the web's address in front."""
    return f"{base}{url}" if url.startswith("/") and not url.startswith("//") else url
