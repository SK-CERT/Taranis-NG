"""Where CSAF documents come from, and which of them changed.

CSAF defines two ways to distribute documents: a directory with a `changes.csv`, and ROLIE
feeds, both found through a provider's `provider-metadata.json` (2.0 and 2.1). Several
publishers use neither - Oracle an RSS feed, NVIDIA, Intel and the OPC Foundation a GitHub
repository - so those are listings here too. Every listing yields the same `Change` records,
and everything after that (download, integrity, parsing) is shared.

A file name is never the identity of a document: it only says where to download it. Whether
a download is a new revision of something already collected is decided from the document's
contents, in `csaf_document`.
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus

import feedparser
import requests
from dateutil.parser import parse as date_parse

TIMEOUT = 30
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
# NCSC-NL's changes.csv alone is 25 MB.
MAX_LISTING_BYTES = 256 * 1024 * 1024
MAX_SMALL_FILE_BYTES = 1024 * 1024
# Folders above a feed or directory searched for its provider's metadata.
MAX_METADATA_LEVELS = 4

GITHUB_HOSTS = {"github.com", "www.github.com"}
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}
# Commits examined to find what changed while the collector was down. Each one costs an API
# call, and unauthenticated clients get 60 an hour.
MAX_RESTART_COMMITS = 30

# Outcomes of reading a listing.
OK = "ok"
NOT_MODIFIED = "not_modified"
RESTRICTED = "restricted"
RATE_LIMITED = "rate_limited"
FAILED = "failed"


@dataclass
class Response:
    """What a GET returned. `status` is 0 when no HTTP response arrived at all."""

    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    url: str = ""
    error: str = ""
    too_large: bool = False

    @property
    def ok(self) -> bool:
        """A successful response whose body was read in full."""
        return HTTPStatus.OK <= self.status < HTTPStatus.MULTIPLE_CHOICES and not self.too_large


class Fetcher:
    """HTTP GET through the source's proxy, with its User-Agent.

    Built on a requests session: one host usually serves a document, its hash and its
    signature, so the connection is reused, and large listings come compressed. Only http and
    https are fetched.
    """

    def __init__(self, user_agent: str | None = None, proxies: dict[str, str] | None = None, session: requests.Session | None = None) -> None:
        """Set up the session.

        Args:
            user_agent (str | None): Sent when set. Left out, requests sends its own, which
                every provider tried accepts - unlike urllib's (SUSE), unknown values (Cisco)
                or browser-like ones (Schneider Electric).
            proxies (dict | None): requests proxy mapping, from the source's proxy setting.
            session (requests.Session | None): A session to use instead of a new one.
        """
        self.session = session or requests.Session()
        if user_agent:
            self.session.headers["User-Agent"] = user_agent
        if proxies:
            self.session.proxies.update(proxies)

    def get(self, url: str, *, headers: dict[str, str] | None = None, max_bytes: int = MAX_DOCUMENT_BYTES) -> Response:
        """Fetch a URL.

        Args:
            url (str): The URL.
            headers (dict | None): Extra request headers, e.g. for a conditional GET.
            max_bytes (int): Larger bodies are not kept; the response says `too_large`.

        Returns:
            Response: Never raises; failures are in `status` and `error`.
        """
        if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
            return Response(0, url=url, error="only http and https URLs are fetched")
        try:
            with self.session.get(url, headers=headers or {}, timeout=TIMEOUT, stream=True) as response:
                response_headers = {name.lower(): value for name, value in response.headers.items()}
                if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
                    return Response(response.status_code, b"", response_headers, response.url, error=response.reason or "")
                body = bytearray()
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    body += chunk
                    if len(body) > max_bytes:
                        return Response(response.status_code, b"", response_headers, response.url, too_large=True)
                return Response(response.status_code, bytes(body), response_headers, response.url)
        except requests.RequestException as error:
            return Response(0, url=url, error=str(error) or type(error).__name__)


def parse_datetime(value: object) -> datetime | None:
    """Read a timestamp from a listing or a document, as an aware datetime.

    Args:
        value (object): An ISO 8601 or RFC 2822 string.

    Returns:
        The time, in UTC when it named no zone, or None when it cannot be read.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = date_parse(text)
        except (ValueError, OverflowError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass
class Change:
    """A document a listing says exists, and what it knows about it.

    Attributes:
        url: Where to download the document.
        key: Identity of the entry within its listing: the URL, or the repository path.
        changed_at: When it last changed, for dated listings.
        hash_urls: Hash files the listing names, best algorithm first.
        signature_url: The signature file the listing names.
        probe: Try the standard `.sha512`, `.sha256` and `.asc` next to the document for
            whatever the listing does not name. False where the listing is complete.
        category: The document category, when the listing states it (ROLIE).
        blob_sha: The git blob SHA, for GitHub listings.
        page_url: A page showing the document to people, where the download URL is a raw file.
    """

    url: str
    key: str = ""
    changed_at: datetime | None = None
    hash_urls: list[str] = field(default_factory=list)
    signature_url: str | None = None
    probe: bool = True
    category: str | None = None
    blob_sha: str | None = None
    page_url: str | None = None

    def __post_init__(self) -> None:
        """Default the key to the URL."""
        self.key = self.key or self.url


@dataclass
class ListingResult:
    """The outcome of reading a listing: its changes, and the validators for the next request."""

    status: str
    changes: list[Change] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    message: str = ""


def directory_url(url: str) -> str:
    """Normalize a directory URL to end in "/", so relative paths resolve inside it.

    Without the slash, urljoin(".../csaf/advisories", "2024/x.json") drops "advisories".
    """
    parts = urllib.parse.urlsplit(url.strip())
    path = parts.path
    for listing_file in ("changes.csv", "index.txt"):
        if path.endswith("/" + listing_file):
            path = path[: -len(listing_file)]
    if not path.endswith("/"):
        path += "/"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _conditional_headers(validators: tuple[str | None, str | None]) -> dict[str, str]:
    etag, last_modified = validators
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def _rate_limit_message(response: Response) -> str | None:
    """Describe a GitHub rate-limit answer, or None when the response is not one."""
    if response.status not in {HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS} or response.headers.get("x-ratelimit-remaining") != "0":
        return None
    reset = response.headers.get("x-ratelimit-reset", "")
    when = datetime.fromtimestamp(int(reset), UTC).isoformat() if reset.isdigit() else "later"
    return f"GitHub API rate limit reached; it resets at {when}"


def fetch_listing_file(
    fetcher: Fetcher,
    url: str,
    validators: tuple[str | None, str | None],
    headers: dict[str, str] | None = None,
) -> tuple[ListingResult | None, Response]:
    """GET a listing file conditionally, and map the answers that end the read early.

    Returns:
        A result when the read ends here (not modified, restricted, rate limited, failed),
        otherwise None, and the response.
    """
    response = fetcher.get(url, headers={**_conditional_headers(validators), **(headers or {})}, max_bytes=MAX_LISTING_BYTES)
    if response.status == HTTPStatus.NOT_MODIFIED:
        return ListingResult(NOT_MODIFIED), response
    if (message := _rate_limit_message(response)) is not None:
        return ListingResult(RATE_LIMITED, message=message), response
    if response.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
        return ListingResult(RESTRICTED, message=f"HTTP {response.status} for {url}"), response
    if response.too_large:
        return ListingResult(FAILED, message=f"{url} is larger than {MAX_LISTING_BYTES} bytes"), response
    if not response.ok:
        return ListingResult(FAILED, message=f"HTTP {response.status or response.error} for {url}"), response
    return None, response


class Listing:
    """A place that lists CSAF documents. Subclasses read one kind of list."""

    kind = ""
    # Whether the listing dates its entries. Undated listings (GitHub) are tracked by content.
    dated = True

    def __init__(self, url: str, tlp: str | None = None) -> None:
        """Remember the listing's URL, and its TLP label when provider metadata states one."""
        self.url = url
        self.tlp = (tlp or "").upper()

    @property
    def access_controlled(self) -> bool:
        """Whether the provider marks the listing as not public (TLP GREEN, AMBER or RED)."""
        return self.tlp not in {"", "WHITE", "CLEAR"}

    @property
    def named_category(self) -> str | None:
        """The document category the listing's name says it holds, or None.

        Provider metadata does not say what a distribution holds. Providers that publish VEX
        apart from their advisories name its distribution after it - SUSE `csaf-vex/`, Red Hat
        and Microsoft `vex/` - and the name is all there is to know it by before downloading.
        """
        segment = next((part for part in reversed(urllib.parse.urlsplit(self.url).path.split("/")) if part), "")
        return "csaf_vex" if "vex" in re.split(r"[^a-z0-9]+", segment.lower()) else None

    @property
    def key(self) -> str:
        """Identity of the listing in the collector's per-source state."""
        return f"{self.kind}:{self.url}"

    def list_changes(self, fetcher: Fetcher, validators: tuple[str | None, str | None]) -> ListingResult:
        """Read the listing.

        Args:
            fetcher (Fetcher): Where to fetch from.
            validators (tuple): ETag and Last-Modified of the previous successful read.

        Returns:
            ListingResult
        """
        raise NotImplementedError

    def _fetch(self, fetcher: Fetcher, url: str, validators: tuple) -> tuple[ListingResult | None, Response]:
        result, response = fetch_listing_file(fetcher, url, validators)
        # A non-public listing often answers 404 to anyone without access (BSI's TLP:GREEN feeds).
        if result is not None and result.status == FAILED and self.access_controlled and response.status == HTTPStatus.NOT_FOUND:
            result = ListingResult(RESTRICTED, message=f"TLP:{self.tlp} listing not accessible (HTTP {response.status})")
        return result, response

    @staticmethod
    def _result(response: Response, changes: list[Change]) -> ListingResult:
        return ListingResult(OK, changes, response.headers.get("etag"), response.headers.get("last-modified"))


class DirectoryListing(Listing):
    """A directory-based distribution: `changes.csv` lists every document and when it last changed."""

    kind = "directory"

    def __init__(self, url: str, tlp: str | None = None) -> None:
        """Remember the directory, normalized to end in "/"."""
        super().__init__(directory_url(url), tlp)

    def list_changes(self, fetcher: Fetcher, validators: tuple[str | None, str | None]) -> ListingResult:
        """Read `changes.csv`: one `"path","timestamp"` row per document."""
        result, response = self._fetch(fetcher, urllib.parse.urljoin(self.url, "changes.csv"), validators)
        if result is not None:
            return result
        changes = []
        # 204 or an empty file: nothing published (yet).
        for row in csv.reader(io.StringIO(response.body.decode("utf-8-sig", errors="replace"))):
            if len(row) < 2 or not row[0].strip():  # noqa: PLR2004 - path and timestamp
                continue
            changes.append(Change(url=urllib.parse.urljoin(self.url, row[0].strip()), changed_at=parse_datetime(row[1])))
        return self._result(response, changes)


class RolieListing(Listing):
    """A ROLIE feed: a JSON Atom feed whose entries link the document, its hashes and its signature."""

    kind = "rolie"

    def list_changes(self, fetcher: Fetcher, validators: tuple[str | None, str | None]) -> ListingResult:
        """Read the feed's entries."""
        result, response = self._fetch(fetcher, self.url, validators)
        if result is not None:
            return result
        try:
            feed = json.loads(response.body).get("feed") or {}
        except (ValueError, AttributeError) as error:
            return ListingResult(FAILED, message=f"{self.url} is not a ROLIE feed: {error}")
        changes = [change for entry in feed.get("entry") or [] if (change := self._change(entry)) is not None]
        return self._result(response, changes)

    def _change(self, entry: object) -> Change | None:
        if not isinstance(entry, dict):
            return None
        links = entry.get("link") or []
        links = [link for link in (links if isinstance(links, list) else [links]) if isinstance(link, dict) and link.get("href")]
        content = entry.get("content") if isinstance(entry.get("content"), dict) else {}
        url = content.get("src") or next((link["href"] for link in links if link.get("rel") == "self"), None)
        if not url:
            return None
        # SHA-512 first when the entry names both.
        hashes = sorted((link["href"] for link in links if link.get("rel") == "hash"), key=lambda href: not href.lower().endswith(".sha512"))
        signature = next((link["href"] for link in links if link.get("rel") == "signature"), None)
        categories = entry.get("category") or []
        category = next(
            (c.get("term") for c in categories if isinstance(c, dict) and "document_category" in str(c.get("scheme", ""))),
            None,
        )
        return Change(
            url=url,
            changed_at=parse_datetime(entry.get("updated") or entry.get("published")),
            hash_urls=hashes,
            signature_url=signature,
            category=category,
        )


class FeedListing(Listing):
    """An RSS or Atom feed whose items link CSAF documents. Not a CSAF distribution method, but Oracle's."""

    kind = "feed"

    def list_changes(self, fetcher: Fetcher, validators: tuple[str | None, str | None]) -> ListingResult:
        """Read the feed's items that link a JSON document."""
        result, response = self._fetch(fetcher, self.url, validators)
        if result is not None:
            return result
        changes = []
        for entry in feedparser.parse(response.body).entries:
            url = self._document_link(entry)
            if url is None:
                continue
            # Read without feedparser's deprecated updated->published fallback.
            stamp = dict.get(entry, "updated_parsed") or dict.get(entry, "published_parsed")
            changes.append(Change(url=url, changed_at=datetime(*stamp[:6], tzinfo=UTC) if stamp else None))
        return self._result(response, changes)

    @staticmethod
    def _document_link(entry: dict) -> str | None:
        # Oracle pads the <link> text with whitespace and newlines.
        candidates = [entry.get("link")] + [link.get("href") for link in entry.get("links") or [] if isinstance(link, dict)]
        for candidate in candidates:
            url = (candidate or "").strip()
            if url and urllib.parse.urlsplit(url).path.lower().endswith(".json"):
                return url
        return None


@dataclass
class GitHubRepo:
    """A folder in a GitHub repository. `ref` "HEAD" is the default branch."""

    owner: str
    repo: str
    ref: str = "HEAD"
    path: str = ""

    def raw_url(self, path: str) -> str:
        """The download URL of a file; not subject to the API rate limit."""
        return f"{GITHUB_RAW}/{self.owner}/{self.repo}/{self.ref}/{urllib.parse.quote(path)}"

    def page_url(self, path: str) -> str:
        """The GitHub page showing a file."""
        return f"https://github.com/{self.owner}/{self.repo}/blob/{self.ref}/{urllib.parse.quote(path)}"

    def api_url(self, suffix: str) -> str:
        """A REST API URL for this repository."""
        return f"{GITHUB_API}/repos/{self.owner}/{self.repo}{suffix}"

    def in_scope(self, path: str) -> bool:
        """Whether a repository path is inside the configured folder."""
        return not self.path or path == self.path or path.startswith(self.path + "/")

    def fetch_tree(
        self,
        fetcher: Fetcher,
        validators: tuple[str | None, str | None],
    ) -> tuple[ListingResult | None, dict[str, str], Response]:
        """Read every file in the repository with one API call.

        Returns:
            An early result (not modified, rate limited, failed) or None, the blobs as
            {path: sha}, and the response.
        """
        url = self.api_url(f"/git/trees/{urllib.parse.quote(self.ref)}?recursive=1")
        result, response = fetch_listing_file(fetcher, url, validators, GITHUB_HEADERS)
        if result is not None:
            return result, {}, response
        try:
            tree = json.loads(response.body)
        except ValueError as error:
            return ListingResult(FAILED, message=f"{url}: {error}"), {}, response
        if tree.get("truncated"):
            return ListingResult(FAILED, message=f"{url}: the repository is too large to list in one call"), {}, response
        blobs = {entry["path"]: entry.get("sha", "") for entry in tree.get("tree") or [] if entry.get("type") == "blob" and entry.get("path")}
        return None, blobs, response


# CVE records (NVIDIA publishes them next to its CSAF files) and provider or aggregator
# metadata are JSON too, but not advisories. Anything else that turns out not to be CSAF is
# recognised after download.
_NOT_A_DOCUMENT = re.compile(r"^(CVE-\d{4}-\d+|aggregator)|provider-metadata", re.IGNORECASE)


class GitHubListing(Listing):
    """CSAF documents kept in a GitHub repository without a `changes.csv`.

    Nothing dates the files, so changes are detected by content: the git blob SHA of a file
    changes whenever the file does.
    """

    kind = "github"
    dated = False

    def __init__(self, repo: GitHubRepo) -> None:
        """Remember the repository folder."""
        super().__init__(f"https://github.com/{repo.owner}/{repo.repo}/tree/{repo.ref}/{repo.path}".rstrip("/"))
        self.repo = repo

    def list_changes(self, fetcher: Fetcher, validators: tuple[str | None, str | None]) -> ListingResult:
        """List every CSAF document in the folder, with its blob SHA and integrity files."""
        result, blobs, response = self.repo.fetch_tree(fetcher, validators)
        if result is not None:
            return result
        by_lower_path = {path.lower(): path for path in blobs}
        changes = []
        for path, sha in blobs.items():
            name = path.rsplit("/", 1)[-1]
            if not self.repo.in_scope(path) or not name.lower().endswith(".json") or _NOT_A_DOCUMENT.search(name):
                continue
            lower = path.lower()
            # Standard `<file>.sha512`, and Intel's `<stem>-JSON.sha256`.
            hash_names = [f"{lower}.sha512", f"{lower}.sha256", f"{lower[:-5]}-json.sha512", f"{lower[:-5]}-json.sha256"]
            hashes = [self.repo.raw_url(by_lower_path[candidate]) for candidate in hash_names if candidate in by_lower_path]
            signature = by_lower_path.get(f"{lower}.asc")
            # NVIDIA publishes each bulletin as Markdown too, which GitHub renders.
            page = by_lower_path.get(f"{lower[:-5]}.md", path)
            changes.append(
                Change(
                    url=self.repo.raw_url(path),
                    key=path,
                    hash_urls=hashes,
                    signature_url=self.repo.raw_url(signature) if signature else None,
                    probe=False,
                    blob_sha=sha,
                    page_url=self.repo.page_url(page),
                ),
            )
        return self._result(response, changes)

    def paths_changed_since(self, fetcher: Fetcher, since: datetime) -> set[str] | None:
        """The paths changed by commits since a time, from the commits API.

        Used after a restart, when the blob SHAs of the previous run are gone.

        Returns:
            The paths, or None when there were too many commits or the API failed.
        """
        query = {"since": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "per_page": "100"}
        if self.repo.path:
            query["path"] = self.repo.path
        if self.repo.ref != "HEAD":
            query["sha"] = self.repo.ref
        response = fetcher.get(
            self.repo.api_url(f"/commits?{urllib.parse.urlencode(query)}"),
            headers=GITHUB_HEADERS,
            max_bytes=MAX_LISTING_BYTES,
        )
        if not response.ok:
            return None
        commits = json.loads(response.body)
        if not isinstance(commits, list) or len(commits) > MAX_RESTART_COMMITS:
            return None
        paths = set()
        for commit in commits:
            detail = fetcher.get(self.repo.api_url(f"/commits/{commit.get('sha', '')}"), headers=GITHUB_HEADERS, max_bytes=MAX_LISTING_BYTES)
            if not detail.ok:
                return None
            paths.update(
                f["filename"] for f in json.loads(detail.body).get("files") or [] if f.get("status") != "removed" and f.get("filename")
            )
        return paths


def parse_github_url(url: str) -> GitHubRepo | str | None:
    """Read a github.com URL.

    Returns:
        A GitHubRepo for a repository or a `/tree/<ref>/<folder>` URL; the raw download URL
        for a `/blob/<ref>/<file>` URL (a page, not the file); None for anything else.
    """
    parts = urllib.parse.urlsplit(url.strip())
    if parts.netloc.lower() not in GITHUB_HOSTS:
        return None
    segments = [urllib.parse.unquote(segment) for segment in parts.path.split("/") if segment]
    if len(segments) < 2:  # noqa: PLR2004 - owner and repository
        return None
    owner, repo = segments[0], segments[1].removesuffix(".git")
    if len(segments) >= 4 and segments[2] == "blob":  # noqa: PLR2004 - blob, ref, file
        return f"{GITHUB_RAW}/{owner}/{repo}/{segments[3]}/{urllib.parse.quote('/'.join(segments[4:]))}"
    if len(segments) >= 4 and segments[2] == "tree":  # noqa: PLR2004 - tree, ref
        return GitHubRepo(owner, repo, segments[3], "/".join(segments[4:]))
    if len(segments) == 2:  # noqa: PLR2004
        return GitHubRepo(owner, repo)
    return None


def rewrite_github_blob(url: str) -> str:
    """Turn a github.com `blob` page URL into the file's download URL; leave others alone.

    OPC's provider metadata points at such pages for its directory and key.
    """
    parsed = parse_github_url(url)
    return parsed if isinstance(parsed, str) else url


@dataclass
class Resolution:
    """What a CSAF URL resolved to: the listings to read and the keys to verify with."""

    listings: list[Listing]
    key_urls: list[tuple[str, str | None]] = field(default_factory=list)
    origin: str = ""


def _json(body: bytes) -> object:
    try:
        return json.loads(body)
    except ValueError:
        return None


def _is_provider_metadata(data: object) -> bool:
    return isinstance(data, dict) and isinstance(data.get("distributions"), list)


def _metadata_resolution(data: dict, origin: str) -> Resolution:
    """Read provider metadata, CSAF 2.0 (`directory_url`) or 2.1 (`directory.url`)."""
    listings: list[Listing] = []
    for distribution in data.get("distributions") or []:
        if not isinstance(distribution, dict):
            continue
        directory = distribution.get("directory") if isinstance(distribution.get("directory"), dict) else {}
        directory_url_ = distribution.get("directory_url") or directory.get("url")
        if directory_url_:
            listings.append(DirectoryListing(rewrite_github_blob(directory_url_), directory.get("tlp_label")))
        listings.extend(
            RolieListing(rewrite_github_blob(feed["url"]), feed.get("tlp_label"))
            for feed in (distribution.get("rolie") or {}).get("feeds") or []
            if isinstance(feed, dict) and feed.get("url")
        )
    return Resolution(listings, _metadata_keys(data), origin)


def _metadata_keys(data: object) -> list[tuple[str, str | None]]:
    if not isinstance(data, dict):
        return []
    return [
        (rewrite_github_blob(key["url"]), key.get("fingerprint"))
        for key in data.get("public_openpgp_keys") or []
        if isinstance(key, dict) and key.get("url")
    ]


def _looks_like_feed(response: Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    start = response.body.lstrip()[:200].lower()
    return "rss" in content_type or "atom" in content_type or start.startswith((b"<?xml", b"<rss", b"<feed", b"<rdf"))


class Resolver:
    """Turns a source's CSAF URL into listings and key URLs."""

    def __init__(self, fetcher: Fetcher) -> None:
        """Use the source's fetcher."""
        self.fetcher = fetcher

    def resolve(self, csaf_url: str) -> Resolution | None:
        """Resolve a CSAF URL.

        Args:
            csaf_url (str): A domain, provider metadata, ROLIE or RSS/Atom feed, directory, or
                GitHub repository URL.

        Returns:
            The resolution, or None when nothing usable was found there.
        """
        url = csaf_url.strip()
        if not url:
            return None
        if "://" not in url:
            host, _, rest = url.partition("/")
            if not rest.strip("/"):
                return self.discover(host)
            url = f"https://{url}"
        parts = urllib.parse.urlsplit(url)
        if parts.path in {"", "/"} and not parts.query:
            return self.discover(parts.netloc)
        github = parse_github_url(url)
        if isinstance(github, GitHubRepo):
            return self.resolve_github(github)
        if isinstance(github, str):
            url = github
        return self.resolve_url(url)

    def discover(self, domain: str) -> Resolution | None:
        """Find a provider's metadata the ways CSAF defines: well-known URL, security.txt, DNS name."""
        metadata = self._metadata(f"https://{domain}/.well-known/csaf/provider-metadata.json")
        if metadata is not None:
            return metadata
        for security_txt in (f"https://{domain}/.well-known/security.txt", f"https://{domain}/security.txt"):
            response = self.fetcher.get(security_txt, max_bytes=MAX_SMALL_FILE_BYTES)
            if not response.ok:
                continue
            for line in response.body.decode("utf-8", errors="replace").splitlines():
                name, _, value = line.partition(":")
                if name.strip().lower() == "csaf" and (metadata := self._metadata(value.strip())) is not None:
                    return metadata
        return self._metadata(f"https://csaf.data.security.{domain}/")

    def _metadata(self, url: str) -> Resolution | None:
        response = self.fetcher.get(url, max_bytes=MAX_SMALL_FILE_BYTES)
        data = _json(response.body) if response.ok else None
        return _metadata_resolution(data, url) if _is_provider_metadata(data) else None

    def resolve_url(self, url: str) -> Resolution | None:
        """Tell what a URL points at from what it returns."""
        response = self.fetcher.get(url, max_bytes=MAX_LISTING_BYTES)
        if response.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
            return None
        data = _json(response.body) if response.ok else None
        if _is_provider_metadata(data):
            return _metadata_resolution(data, url)
        host_keys = self._host_keys(url)
        if isinstance(data, dict) and isinstance(data.get("feed"), dict):
            return Resolution([RolieListing(url)], host_keys, url)
        if response.ok and _looks_like_feed(response):
            return Resolution([FeedListing(url)], host_keys, url)
        # Anything else is a directory: its URL often answers with an HTML index, or nothing.
        return Resolution([DirectoryListing(url)], host_keys, url)

    def _host_keys(self, url: str) -> list[tuple[str, str | None]]:
        """The keys of the provider that publishes a feed or directory.

        Provider metadata usually sits just above its distributions (Red Hat's in
        /data/csaf/v2/, Siemens' in /productcert/csaf/), so the folders above the URL are
        tried first, nearest first, then the host's discovery (well-known URL, security.txt).
        """
        parts = urllib.parse.urlsplit(url)
        segments = [segment for segment in parts.path.split("/") if segment]
        deepest = len(segments) if parts.path.endswith("/") else len(segments) - 1
        for depth in range(deepest, max(deepest - MAX_METADATA_LEVELS, 0), -1):
            folder = "/" + "/".join(segments[:depth]) + "/"
            response = self.fetcher.get(f"{parts.scheme}://{parts.netloc}{folder}provider-metadata.json", max_bytes=MAX_SMALL_FILE_BYTES)
            data = _json(response.body) if response.ok else None
            if _is_provider_metadata(data):
                return _metadata_keys(data)
        discovered = self.discover(parts.netloc)
        return discovered.key_urls if discovered is not None else []

    def resolve_github(self, repo: GitHubRepo) -> Resolution | None:
        """Resolve a GitHub repository folder.

        Folders holding a `changes.csv` are standard directories (CISA keeps three) and are
        read as such, from the raw files. A repository without one is listed by content.
        Provider metadata kept in the repository supplies the keys (OPC Foundation).
        """
        result, blobs, _response = repo.fetch_tree(self.fetcher, (None, None))
        if result is not None:
            return None
        in_scope = [path for path in blobs if repo.in_scope(path)]
        directories = sorted({path.rpartition("/")[0] for path in in_scope if path.rsplit("/", 1)[-1] == "changes.csv"})
        listings: list[Listing] = [DirectoryListing(repo.raw_url(f"{directory}/" if directory else "")) for directory in directories]
        if not listings:
            listings = [GitHubListing(repo)]
        key_urls: list[tuple[str, str | None]] = []
        for path in blobs:
            name = path.rsplit("/", 1)[-1].lower()
            if "provider-metadata" in name and name.endswith(".json") and ("/" not in path or repo.in_scope(path)):
                response = self.fetcher.get(repo.raw_url(path), max_bytes=MAX_SMALL_FILE_BYTES)
                if response.ok:
                    key_urls.extend(_metadata_keys(_json(response.body)))
        return Resolution(listings, key_urls, f"https://github.com/{repo.owner}/{repo.repo}")
