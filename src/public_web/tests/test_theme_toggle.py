"""Every page has a colour-mode button: automatic (as the browser is set, the default), light, dark.

One button goes through the three; the script every page carries inline in its head
(``shared.public_web_script``) applies the mode and shows its icon and label on the button,
which the page gives in its language.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from shared import public_web_script

if TYPE_CHECKING:
    from types import SimpleNamespace

TOGGLE = re.compile(r"<button[^>]*data-theme-toggle[^>]*>.*?</button>", re.DOTALL)


@pytest.mark.parametrize(
    ("path", "name", "labels"),
    [
        ("/", "Color mode", ["Automatic (as the browser is set)", "Light", "Dark"]),
        ("/reports/101", "Color mode", ["Automatic (as the browser is set)", "Light", "Dark"]),
        ("/reports/101?lang=cs", "Barevný režim", ["Automaticky (podle nastavení prohlížeče)", "Světlý", "Tmavý"]),
    ],
)
def test_one_button_offers_auto_light_and_dark(site_client: SimpleNamespace, path: str, name: str, labels: list[str]) -> None:
    page = site_client.client.get(path, headers={"Host": "localhost"}).text

    (toggle,) = TOGGLE.findall(page)
    for mode, label in zip(("auto", "light", "dark"), labels, strict=True):
        assert f'data-label-{mode}="{name}: {label}"' in toggle
    # Following the browser until the visitor picks: its label and icon, the others hidden.
    assert f'title="{name}: {labels[0]}"' in toggle
    assert f'aria-label="{name}: {labels[0]}"' in toggle
    icons = re.findall(r'<span class="([^"]*)" data-theme-icon="(\w+)"', toggle)
    assert [(mode, "d-none" in classes.split()) for classes, mode in icons] == [("auto", False), ("light", True), ("dark", True)]


def test_the_page_runs_the_shared_page_script(site_client: SimpleNamespace) -> None:
    # The very text core allows by its hash in the template preview, so the button works there too.
    page = site_client.client.get("/", headers={"Host": "localhost"}).text

    head = page[: page.index("</head>")]
    assert f"<script>{public_web_script.SCRIPT}</script>" in head
