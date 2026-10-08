"""CSAF collector module.

Collects security advisories published in the CSAF format (2.0 and 2.1): from a provider's
metadata, a directory, a ROLIE or RSS/Atom feed, or a GitHub repository (see csaf_sources).
Each document becomes one news item. A newer revision of an advisory carries the same
`version_key`, so core stores it as a new version of the item already collected.
"""

from __future__ import annotations

import datetime
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar

from shared.common import TZ, ignore_exceptions, read_bool_parameter, read_int_parameter, read_str_parameter
from shared.config_collector import ConfigCollector

from . import csaf_document
from .base_collector import BaseCollector
from .csaf_integrity import INVALID, MISMATCH, MISSING, KeyRing, check_digest, looks_like_signature, parse_digest
from .csaf_sources import (
    FAILED,
    MAX_DOCUMENT_BYTES,
    MAX_SMALL_FILE_BYTES,
    NOT_MODIFIED,
    OK,
    RATE_LIMITED,
    RESTRICTED,
    Change,
    Fetcher,
    GitHubListing,
    Listing,
    ListingResult,
    Resolution,
    Resolver,
    rewrite_github_blob,
)

if TYPE_CHECKING:
    from shared.schema.news_item import NewsItemData

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)


@dataclass
class ListingState:
    """What the collector remembers about one listing between runs.

    Attributes:
        watermark: The newest change time handled (dated listings).
        etag, last_modified: Validators for the next conditional request.
        seen: Entries already handled - key to change time for dated listings, path to blob
            SHA for GitHub ones - so the overlap of a run does not download them again.
        initialized: Whether a GitHub listing has a baseline of blob SHAs.
    """

    watermark: datetime.datetime | None = None
    etag: str | None = None
    last_modified: str | None = None
    seen: dict[str, object] = field(default_factory=dict)
    initialized: bool = False


@dataclass
class SourceState:
    """What the collector remembers about one source: its resolution, keys and listings."""

    csaf_url: str = ""
    resolved_at: float | None = None
    resolution: Resolution | None = None
    keys: KeyRing = field(default_factory=KeyRing)
    listings: dict[str, ListingState] = field(default_factory=dict)


@dataclass
class Collected:
    """A handled change: its news item, or None when the document was skipped."""

    change: Change
    item: NewsItemData | None = None
    released_at: datetime.datetime | None = None


def _stamp(change: Change) -> datetime.datetime:
    return change.changed_at or EPOCH


def _path_order(path: str) -> tuple[list[int], str]:
    """Sort key guessing how recent a repository file is from the numbers in its path.

    Publishers number their advisories and file them under the year, so the numbers - not the
    text around them - carry the order: NVIDIA's 2026/5885 after 2025/9999, and Intel's
    INTEL-SA-01499 after INTEL-TA-01132.
    """
    return [int(number) for number in re.findall(r"\d+", path)], path.lower()


class CSAFCollector(BaseCollector):
    """Collector for CSAF security advisories.

    Arguments:
        BaseCollector: Base collector class.
    """

    collector_type = "CSAF_COLLECTOR"
    config = ConfigCollector().get_config_by_type(collector_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    # A provider's distributions and keys rarely change; re-read them daily.
    RESOLUTION_MAX_AGE = 24 * 60 * 60
    # How far before the newest change handled a later run looks again. Some providers stamp
    # whole days (BSI) or fixed times (CISA), so a document can appear with a time already past.
    OVERLAP = datetime.timedelta(hours=24)
    SEEN_RETENTION = datetime.timedelta(hours=48)
    # Keeps each request well within the 30 seconds the client waits for core to store it.
    PUBLISH_CHUNK = 25
    DEFAULT_MAX_DOCUMENTS = 100

    # Per source, on the class: `run_collector` builds a throwaway instance for every run, and
    # `source.last_collected` is only loaded on refresh, so neither can carry this between runs.
    # Lost on restart; a run then falls back to `last_collected`, which is fresh at startup.
    _states: ClassVar[dict[str, SourceState]] = {}
    _states_guard: ClassVar[threading.Lock] = threading.Lock()

    def _initialize_source(self, source: object) -> None:
        self.source = source
        super()._initialize_source(source)
        source.url = read_str_parameter("CSAF_URL", "", source).strip()
        source.user_agent = read_str_parameter("USER_AGENT", "", source).strip()
        source.proxy = read_str_parameter("PROXY_SERVER", "", source)
        # Read once per run: every document collected carries it to core.
        source.resurface_new_versions = read_bool_parameter("RESURFACE_NEW_VERSIONS", default_value=True, object_dict=source)
        source.parsed_proxy = self.get_parsed_proxy()
        proxies = {"http": source.proxy, "https": source.proxy} if source.parsed_proxy else None
        # No User-Agent unless one is configured: requests' own is accepted everywhere, where
        # providers block urllib's (SUSE), unknown (Cisco) or browser-like (Schneider) values.
        self.fetcher = Fetcher(source.user_agent or None, proxies)
        self.keys = KeyRing()
        self.integrity_counts: Counter = Counter()

    @ignore_exceptions
    def collect(self) -> None:
        """Collect the new and changed documents of every distribution of the source."""
        if not self.source.url:
            self.source.logger.error("CSAF URL is not set. Skipping collection.")
            return
        state = self._state_for(self.source)
        if not self._resolve(state):
            return
        self.keys = state.keys

        skip = self._skip_categories()
        listings = []
        for listing in state.resolution.listings:
            if listing.named_category in skip:
                self.source.logger.info(f"{listing.url}: not read, its name marks it as {listing.named_category}, a skipped category")
            else:
                listings.append(listing)
        restricted = 0
        for listing in listings:
            if self._collect_listing(listing, state) == RESTRICTED:
                restricted += 1
        if listings and restricted == len(listings):
            self.source.logger.warning(f"None of the {len(listings)} distributions could be read: they all require authentication")
        elif restricted:
            self.source.logger.info(f"{restricted} of {len(listings)} distributions require authentication and were skipped")

    @classmethod
    def _state_for(cls, source: object) -> SourceState:
        """The source's state, started afresh when its CSAF URL changed."""
        with cls._states_guard:
            state = cls._states.get(source.id)
            if state is None or state.csaf_url != source.url:
                state = SourceState(csaf_url=source.url)
                cls._states[source.id] = state
            return state

    def _resolve(self, state: SourceState) -> bool:
        """Resolve the CSAF URL into listings and keys, at most once a day."""
        if state.resolution is not None and state.resolved_at is not None and time.monotonic() - state.resolved_at < self.RESOLUTION_MAX_AGE:
            return True
        resolution = Resolver(self.fetcher).resolve(self.source.url)
        if resolution is None:
            if state.resolution is None:
                self.source.logger.warning(f"No CSAF provider metadata, feed, directory or repository found at {self.source.url}")
                return False
            # Keep the previous resolution rather than stop over a temporary failure.
            self.source.logger.info(f"Could not re-read {self.source.url}; using its previous distributions")
            state.resolved_at = time.monotonic()
            return True
        state.resolution = resolution
        state.keys = self._load_keys(resolution)
        state.resolved_at = time.monotonic()
        listings = ", ".join(listing.url for listing in resolution.listings)
        self.source.logger.info(
            f"{self.source.url}: {len(resolution.listings)} distribution(s), {len(state.keys.certs)} signing key(s): {listings}",
        )
        return True

    def _load_keys(self, resolution: Resolution) -> KeyRing:
        """Fetch the provider's public keys and any configured in PUBLIC_KEY_URLS."""
        keys = KeyRing()
        configured = [(url.strip(), None) for url in read_str_parameter("PUBLIC_KEY_URLS", "", self.source).split(",") if url.strip()]
        for url, fingerprint in resolution.key_urls + configured:
            response = self.fetcher.get(rewrite_github_blob(url), max_bytes=MAX_SMALL_FILE_BYTES)
            if not response.ok:
                self.source.logger.info(f"OpenPGP key not available (HTTP {response.status or response.error}): {url}")
                continue
            keys.add(response.body, fingerprint, origin=url)
        for message in keys.rejected:
            self.source.logger.warning(f"OpenPGP key refused - {message}")
        for message in keys.unusable:
            self.source.logger.info(f"OpenPGP key not used; signatures made with it are reported unverified - {message}")
        return keys

    def _collect_listing(self, listing: Listing, state: SourceState) -> str:
        """Collect one listing's new and changed documents.

        Returns:
            The listing outcome (OK, NOT_MODIFIED, RESTRICTED, RATE_LIMITED, FAILED).
        """
        listing_state = state.listings.setdefault(listing.key, ListingState())
        check_if_modified = read_bool_parameter("CHECK_IF_MODIFIED", default_value=True, object_dict=self.source)
        validators = (listing_state.etag, listing_state.last_modified) if check_if_modified else (None, None)
        result = listing.list_changes(self.fetcher, validators)
        if result.status == NOT_MODIFIED:
            self.source.logger.debug(f"{listing.url}: not modified")
            return NOT_MODIFIED
        if result.status == RESTRICTED:
            self.source.logger.debug(f"{listing.url}: {result.message}")
            return RESTRICTED
        if result.status in {RATE_LIMITED, FAILED}:
            self.source.logger.warning(f"{listing.url}: {result.message}")
            return result.status

        skip = self._skip_categories()
        # Entries the listing states a skipped category for (ROLIE) are left out before the limit,
        # which then counts only documents that can be collected.
        wanted = [change for change in result.changes if not (change.category and change.category.lower() in skip)]
        limit = read_int_parameter("MAX_DOCUMENTS", self.DEFAULT_MAX_DOCUMENTS, self.source)
        if listing.dated:
            selected, left_out = self._select_dated(listing, wanted, listing_state, limit)
        else:
            selected, left_out = self._select_by_content(listing, wanted, listing_state, limit), False

        self.integrity_counts = Counter()
        collected = [handled for change in selected if (handled := self._collect_change(change, skip)) is not None]
        published, complete = self._publish(collected)
        self._remember(listing, listing_state, result, published, complete=complete, left_out=left_out)

        items = sum(1 for handled in collected if handled.item is not None)
        integrity = ", ".join(f"{count} {name}" for name, count in sorted(self.integrity_counts.items()))
        summary = f"{listing.url}: {len(result.changes)} listed, {len(selected)} new or changed, {items} collected"
        self.source.logger.info(f"{summary} (integrity: {integrity})" if integrity else summary)
        return OK

    def _last_collected(self) -> datetime.datetime | None:
        value = getattr(self.source, "last_collected", None)
        if not isinstance(value, datetime.datetime):
            return None
        return value if value.tzinfo else value.replace(tzinfo=TZ)

    def _select_dated(self, listing: Listing, changes: list[Change], listing_state: ListingState, limit: int) -> tuple[list[Change], bool]:
        """Pick the changes to download from a listing that dates its entries.

        The first run takes the newest `limit` and never pages back through the archive. Later
        runs take what changed since the newest change handled, less the overlap, skipping
        entries already handled with the same time: the same file listed with a newer time is
        a new revision and is taken again.

        Returns:
            The changes to download, oldest first, and whether the limit left some out.
        """
        since = listing_state.watermark or self._last_collected()
        if since is None:
            candidates, truncated = list(changes), False
        else:
            floor = since - self.OVERLAP
            candidates = [change for change in changes if _stamp(change) >= floor and not self._already_seen(listing_state, change)]
            truncated = len(candidates) > limit
        candidates.sort(key=_stamp, reverse=True)
        if truncated:
            self.source.logger.warning(
                f"{listing.url}: {len(candidates)} documents changed, collecting the newest {limit}; "
                "raise MAX_DOCUMENTS or shorten the refresh interval to collect them all",
            )
        return sorted(candidates[:limit], key=_stamp), truncated

    @staticmethod
    def _already_seen(listing_state: ListingState, change: Change) -> bool:
        previous = listing_state.seen.get(change.key)
        return isinstance(previous, datetime.datetime) and previous >= _stamp(change)

    def _select_by_content(self, listing: Listing, changes: list[Change], listing_state: ListingState, limit: int) -> list[Change]:
        """Pick the changes to download from a GitHub listing, by blob SHA.

        The first run of a new source takes the newest `limit` by path. After a restart the
        commits API tells what changed while the collector was down.
        """
        newest_first = sorted(changes, key=lambda change: _path_order(change.key), reverse=True)
        if listing_state.initialized:
            changed = [change for change in newest_first if listing_state.seen.get(change.key) != change.blob_sha]
        else:
            since = self._last_collected()
            paths = listing.paths_changed_since(self.fetcher, since - self.OVERLAP) if since and isinstance(listing, GitHubListing) else None
            if paths is None:
                if since is not None:
                    self.source.logger.warning(
                        f"{listing.url}: could not tell what changed since the last collection; collecting the newest {limit} documents",
                    )
                return newest_first[:limit]
            changed = [change for change in newest_first if change.key in paths]
        if len(changed) > limit:
            self.source.logger.warning(
                f"{listing.url}: {len(changed)} documents changed, collecting the newest {limit}; "
                "raise MAX_DOCUMENTS or shorten the refresh interval to collect them all",
            )
        return changed[:limit]

    def _skip_categories(self) -> set[str]:
        return {
            category.strip().lower() for category in read_str_parameter("SKIP_CATEGORIES", "", self.source).split(",") if category.strip()
        }

    def _collect_change(self, change: Change, skip: set[str]) -> Collected | None:
        """Download one document and build its news item.

        Returns:
            The handled change - with no item when the document is skipped for good - or None
            when the download failed and it should be tried again.
        """
        response = self.fetcher.get(change.url, max_bytes=MAX_DOCUMENT_BYTES)
        if response.too_large:
            self.source.logger.warning(f"Skipping {change.url}: larger than {MAX_DOCUMENT_BYTES} bytes")
            return Collected(change)
        if not response.ok:
            self.source.logger.info(f"Download failed (HTTP {response.status or response.error}): {change.url}")
            return None
        try:
            data = csaf_document.loads(response.body)
        except ValueError:
            self.source.logger.debug(f"Not JSON, skipped: {change.url}")
            return Collected(change)
        if not csaf_document.is_csaf(data):
            self.source.logger.debug(f"Not a CSAF document, skipped: {change.url}")
            return Collected(change)
        if csaf_document.category(data).lower() in skip:
            self.source.logger.debug(f"Category {csaf_document.category(data)} is skipped: {change.url}")
            return Collected(change)
        version = csaf_document.csaf_version(data)
        if version not in csaf_document.SUPPORTED_VERSIONS:
            self.source.logger.warning(f"{change.url} declares CSAF {version}, which is not 2.0 or 2.1; reading it anyway")

        integrity = (
            self._integrity(change, response.body)
            if read_bool_parameter("VERIFY_SIGNATURES", default_value=True, object_dict=self.source)
            else None
        )
        item = csaf_document.build_news_item(data, change.url, self.source, integrity, change.page_url)
        # Core decides from it whether a newer version of an advisory it holds resurfaces it.
        item.resurface = self.source.resurface_new_versions
        item = self.sanitize_news_item(item, self.source)
        item.print_news_item(self.source.logger)
        return Collected(change, item, csaf_document.release_date(data))

    def _integrity(self, change: Change, document: bytes) -> dict[str, str]:
        """Check the document's hash and signature. Only a failed check is a warning.

        A missing file or a key we do not hold is common - several publishers do not sign - and
        warning about it would leave a permanent error on the source.
        """
        results = {"CSAF_HASH": self._hash_status(change, document), "CSAF_SIGNATURE": self._signature_status(change, document)}
        for key, status in results.items():
            self.integrity_counts[f"{key.removeprefix('CSAF_').lower()} {status}"] += 1
            if status in {MISMATCH, INVALID}:
                self.source.logger.warning(f"{key.removeprefix('CSAF_').capitalize()} check failed ({status}): {change.url}")
        return results

    def _hash_status(self, change: Change, document: bytes) -> str:
        candidates = list(change.hash_urls) or ([f"{change.url}.sha512", f"{change.url}.sha256"] if change.probe else [])
        for url in candidates:
            response = self.fetcher.get(url, max_bytes=MAX_SMALL_FILE_BYTES)
            # Checked by content: a missing file may redirect to an HTML page (Microsoft).
            digest = parse_digest(response.body) if response.ok else None
            if digest:
                return check_digest(document, digest)
        return MISSING

    def _signature_status(self, change: Change, document: bytes) -> str:
        url = change.signature_url or (f"{change.url}.asc" if change.probe else None)
        signature = None
        if url:
            response = self.fetcher.get(url, max_bytes=MAX_SMALL_FILE_BYTES)
            if response.ok and looks_like_signature(response.body):
                signature = response.body
        return self.keys.verify(document, signature)

    def _publish(self, collected: list[Collected]) -> tuple[set[str], bool]:
        """Send the news items to core in chunks, oldest revision first.

        Returns:
            The keys of the changes handled for good - published or skipped - and whether
            every chunk was accepted.
        """
        handled = {entry.change.key for entry in collected if entry.item is None}
        items = sorted((entry for entry in collected if entry.item is not None), key=lambda entry: entry.released_at or EPOCH)
        complete = True
        for start in range(0, len(items), self.PUBLISH_CHUNK):
            chunk = items[start : start + self.PUBLISH_CHUNK]
            answer = self.publish([entry.item for entry in chunk])
            if answer == HTTPStatus.OK:
                handled.update(entry.change.key for entry in chunk)
                continue
            complete = False
            if isinstance(answer, tuple) and answer[-1] == HTTPStatus.GATEWAY_TIMEOUT:
                self.source.logger.warning(
                    f"Core did not answer in time for {len(chunk)} news items and may have stored them; they are sent "
                    "again on the next run, and core skips the ones it already has",
                )
            else:
                self.source.logger.warning(f"Core did not accept {len(chunk)} news items; they will be collected again on the next run")
        return handled, complete

    def _remember(
        self,
        listing: Listing,
        listing_state: ListingState,
        result: ListingResult,
        handled: set[str],
        *,
        complete: bool,
        left_out: bool = False,
    ) -> None:
        """Record what this run handled.

        The watermark, baseline and validators only move when core accepted everything, so a
        failed run is repeated; what did succeed is marked seen either way. When the limit left
        changes out, the validators are dropped: the next run has to read the listing again to
        reach them, although the server would answer that it did not change.
        """
        by_key = {change.key: change for change in result.changes}
        if listing.dated:
            for key in handled:
                listing_state.seen[key] = _stamp(by_key[key])
            if complete:
                # A date in the future would hold the watermark ahead of every change listed until
                # then, and skip them all: Microsoft dates some updates by their Patch Tuesday.
                now = datetime.datetime.now(datetime.UTC)
                future = [stamp for change in result.changes if (stamp := _stamp(change)) > now]
                if future:
                    self.source.logger.info(
                        f"{listing.url}: {len(future)} documents dated in the future (up to {max(future).isoformat()}); "
                        "they do not move collection forward",
                    )
                newest = max((stamp for change in result.changes if (stamp := _stamp(change)) <= now), default=None)
                if newest is not None and (listing_state.watermark is None or newest > listing_state.watermark):
                    listing_state.watermark = newest
                listing_state.etag, listing_state.last_modified = (None, None) if left_out else (result.etag, result.last_modified)
            if listing_state.watermark is not None:
                horizon = listing_state.watermark - self.SEEN_RETENTION
                listing_state.seen = {
                    key: stamp for key, stamp in listing_state.seen.items() if isinstance(stamp, datetime.datetime) and stamp >= horizon
                }
        elif complete:
            # Every current SHA becomes the baseline, including documents a limit left out.
            listing_state.seen = {change.key: change.blob_sha for change in result.changes}
            listing_state.initialized = True
            listing_state.etag, listing_state.last_modified = result.etag, result.last_modified
        else:
            for key in handled:
                listing_state.seen[key] = by_key[key].blob_sha
