"""Notifications are written in the user's language, from catalogs that all say the same things.

Every catalog must have every text of the English one with the same placeholders, or a
translation silently loses the passkey's name or the administrator's. The language follows the
user's UI language as the GUI stores it (``cs``, ``pt-BR``, ``zh-CN``). A user-supplied value
fills the body only: subjects are fixed texts, safe in a mail header.
"""

from __future__ import annotations

import json
import re
import string

import pytest
from managers.notifications import catalog

GUI_LOCALES = {
    "ar",
    "cs",
    "de",
    "en",
    "es",
    "fr",
    "hi",
    "it",
    "ja",
    "kk",
    "ko",
    "nl",
    "pl",
    "pt-BR",
    "ru",
    "sk",
    "th",
    "tlh",
    "tr",
    "uk",
    "vi",
    "zh-CN",
}


def _strings(node: object, path: str = "") -> dict[str, str]:
    if isinstance(node, dict):
        out: dict[str, str] = {}
        for key, value in node.items():
            out.update(_strings(value, f"{path}.{key}" if path else key))
        return out
    return {path: node}


def _placeholders(text: str) -> set[str]:
    return {name for _literal, name, _spec, _conversion in string.Formatter().parse(text) if name}


ENGLISH = _strings(json.loads((catalog.CATALOG_DIR / "en.json").read_text(encoding="utf-8")))


def test_there_is_a_catalog_for_every_language_of_the_gui() -> None:
    assert set(catalog.available_locales()) == GUI_LOCALES


@pytest.mark.parametrize("locale", sorted(GUI_LOCALES - {"en"}))
def test_every_catalog_says_everything_english_says_with_the_same_placeholders(locale: str) -> None:
    texts = _strings(json.loads((catalog.CATALOG_DIR / f"{locale}.json").read_text(encoding="utf-8")))

    assert set(texts) == set(ENGLISH)
    for key, english in ENGLISH.items():
        assert texts[key].strip(), f"{locale}: {key} is empty"
        assert _placeholders(texts[key]) == _placeholders(english), f"{locale}: {key}"


@pytest.mark.parametrize(
    ("ui_language", "locale"),
    [
        ("cs", "cs"),
        ("pt-BR", "pt-BR"),
        ("PT_br", "pt-BR"),
        ("de-AT", "de"),
        ("pt", "pt-BR"),
        ("zh", "zh-CN"),
        ("xx", "en"),
        ("", "en"),
        (None, "en"),
    ],
)
def test_the_user_interface_language_picks_the_catalog(ui_language: str | None, locale: str) -> None:
    assert catalog.resolve_locale(ui_language) == locale


def test_a_change_is_described_with_who_made_it_when_and_from_where() -> None:
    subject, body = catalog.render(
        "en",
        "passkey_removed",
        {
            "name": "Alice",
            "username": "alice",
            "time": "2026-10-15 10:00 CEST",
            "actor": "self",
            "ip": "192.0.2.10",
            "passkey_name": "Work key",
            "authenticator": "YubiKey 5 Series",
            "instance_url": "https://taranis.example.test",
        },
    )

    assert subject == "[Taranis NG] Passkey removed"
    assert body.startswith("Hello Alice,\n\nA passkey was removed from your Taranis NG account.\n")
    for line in (
        "Account: alice",
        "Time: 2026-10-15 10:00 CEST",
        "Changed by: You",
        "IP address: 192.0.2.10",
        "Passkey: Work key",
        "Authenticator: YubiKey 5 Series",
        "If you did not make this change, contact your administrator immediately.",
        "This is an automated message from Taranis NG (https://taranis.example.test).",
    ):
        assert line in body.splitlines()


def test_an_administrators_reset_names_the_administrator_and_what_was_reset() -> None:
    _subject, body = catalog.render("cs", "mfa_reset", {"name": "Alice", "actor": "Bob Admin", "factors": ["totp", "passkeys"]})

    assert "Změnil(a): Administrátor Bob Admin" in body
    assert "Resetováno: Aplikace authenticator (TOTP), Všechny passkeys" in body


def test_details_that_are_not_known_are_left_out() -> None:
    _subject, body = catalog.render("en", "totp_enabled", {"name": "Alice", "username": "alice"})

    assert "IP address" not in body
    assert "Passkey" not in body
    assert body.rstrip().endswith("This is an automated message from Taranis NG.")


def test_the_test_message_asks_nobody_to_contact_an_administrator() -> None:
    subject, body = catalog.render("de", "test", {"name": "Alice"})

    assert subject == "[Taranis NG] Test-E-Mail"
    assert "Administrator" not in body


def test_user_supplied_values_never_reach_the_subject() -> None:
    subject, _body = catalog.render("en", "passkey_added", {"name": "Eve", "passkey_name": "x\r\nBcc: victim@example.test"})

    assert not re.search(r"[\r\n]", subject)
    assert "Bcc" not in subject


def test_an_unknown_or_malformed_placeholder_keeps_the_message_whole() -> None:
    assert catalog.fill("Hello {name} {missing}", {"name": "Alice"}) == "Hello Alice {missing}"
    assert catalog.fill("Hello {name", {"name": "Alice"}) == "Hello {name"
