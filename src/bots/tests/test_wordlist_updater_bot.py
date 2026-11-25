"""The word list updater reads only public URLs and its own word list directory.

Its DATA_URL used to go to ``requests.get`` when it contained "http" anywhere and to
``Path(...).open()`` otherwise, so a bot preset could make the node fetch the cloud metadata
endpoint or read its own Docker secrets, and push the result into a word list. It also never
got as far as that: ``CoreApi.get_categories`` returns ``(body, status)`` and the bot iterated
the tuple.
"""

from __future__ import annotations

import collections
import io
import socket
import types
from http import HTTPStatus

import pytest
from bots.wordlist_updater_bot import WordlistUpdaterBot

from bots import wordlist_updater_bot
from shared import url_guard

ADDRESSES = {"lists.example.org": "93.184.216.34", "core": "172.18.0.5"}


@pytest.fixture(autouse=True)
def _dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(host: str, port: int, *_args: object, **_kwargs: object) -> list[tuple]:
        if host not in ADDRESSES:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ADDRESSES[host], port))]

    monkeypatch.setattr(url_guard.socket, "getaddrinfo", getaddrinfo)


@pytest.fixture
def wordlist_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    directory = tmp_path / "wordlists"
    directory.mkdir()
    (directory / "stop.txt").write_text("alpha\nbeta  \n")
    (tmp_path / "secret.txt").write_text("node-api-key\n")
    monkeypatch.setattr(wordlist_updater_bot, "WORDLIST_DIR", directory)
    return directory


@pytest.fixture
def fetched(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Answer guarded fetches with a fixed body and remember the URLs asked for."""
    urls: list[str] = []

    class Opener:
        def open(self, request: object, *_args: object, **_kwargs: object) -> io.BytesIO:
            urls.append(request.full_url)
            return io.BytesIO(b"gamma\ndelta\n")

    monkeypatch.setattr(url_guard.urllib.request, "build_opener", lambda *_handlers: Opener())
    return urls


def test_reads_a_file_in_the_word_list_directory(wordlist_dir: object) -> None:  # noqa: ARG001
    assert WordlistUpdaterBot.load_words("stop.txt", "txt") == ["alpha", "beta"]


@pytest.mark.parametrize("source", ["../secret.txt", "/run/secrets/api_key", "/etc/passwd", "missing.txt", "."])
def test_refuses_any_other_file(wordlist_dir: object, source: str) -> None:  # noqa: ARG001
    with pytest.raises(ValueError, match="must be a file in"):
        WordlistUpdaterBot.load_words(source, "txt")


def test_downloads_a_public_url(fetched: list[str]) -> None:
    assert WordlistUpdaterBot.load_words("https://lists.example.org/stop.txt", "txt") == ["gamma", "delta"]
    assert fetched == ["https://lists.example.org/stop.txt"]


@pytest.mark.parametrize(
    "source",
    ["http://169.254.169.254/latest/meta-data/", "http://core/api/v1/isalive", "http://127.0.0.1:5000/", "file:///run/secrets/api_key"],
)
def test_refuses_internal_and_non_http_urls(fetched: list[str], source: str) -> None:
    with pytest.raises(url_guard.BlockedUrlError):
        WordlistUpdaterBot.load_words(source, "txt")
    assert fetched == []


def test_a_path_with_http_in_it_is_still_a_path(wordlist_dir: object) -> None:  # noqa: ARG001
    # The old check was `"http" in source`: this was handed to requests.
    with pytest.raises(ValueError, match="must be a file in"):
        WordlistUpdaterBot.load_words("../http-secrets.txt", "txt")


def test_only_txt_is_supported(wordlist_dir: object) -> None:  # noqa: ARG001
    with pytest.raises(ValueError, match="only txt"):
        WordlistUpdaterBot.load_words("stop.txt", "csv")


def test_execute_reads_the_categories_out_of_the_core_answer(wordlist_dir: object, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    calls: list[tuple] = []
    core = wordlist_updater_bot.CoreApi
    monkeypatch.setattr(core, "get_categories", classmethod(lambda _cls, _list_id: ([{"name": "Stop words"}], HTTPStatus.OK)))
    monkeypatch.setattr(core, "add_word_list_category", classmethod(lambda _cls, *args: calls.append(("add", *args))))
    monkeypatch.setattr(core, "delete_word_list_category_entries", classmethod(lambda _cls, *args: calls.append(("delete", *args))))
    monkeypatch.setattr(core, "update_word_list_category_entries", classmethod(lambda _cls, *args: calls.append(("update", *args))))

    bot = WordlistUpdaterBot()
    bot.preset = types.SimpleNamespace(
        param_key_values=collections.defaultdict(
            str,
            {"DATA_URL": "stop.txt", "FORMAT": "txt", "WORD_LIST_ID": "3", "WORD_LIST_CATEGORY": "Stop words", "DELETE": "yes"},
        ),
        logger=types.SimpleNamespace(error=pytest.fail, exception=pytest.fail),
    )
    bot.execute()

    assert [call[0] for call in calls] == ["delete", "update"]
    assert [entry["value"] for entry in calls[1][3]] == ["alpha", "beta"]
