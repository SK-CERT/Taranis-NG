"""The colour-mode script and the hash core's preview policy allows it by."""

import base64
import hashlib

from shared import public_web_script


def test_the_hash_is_the_script_s() -> None:
    digest = base64.b64encode(hashlib.sha256(public_web_script.SCRIPT.encode("utf-8")).digest()).decode("ascii")

    assert f"'sha256-{digest}'" == public_web_script.SCRIPT_HASH


def test_the_script_can_be_inlined() -> None:
    # Inside <script>...</script> a closing tag in the text would end it early.
    assert "</" not in public_web_script.SCRIPT
