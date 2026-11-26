"""The SSE forwarder listens on loopback only.

Core's own workers publish to it and subscribe to it on localhost. Bound to every address, any
container on the compose network - a collector rendering untrusted pages, the internet-facing
public web - could read every event or inject its own into every GUI session.
"""

from __future__ import annotations

import re
from pathlib import Path

FORWARD_C = Path(__file__).resolve().parents[1] / "sse" / "forward.c"


def test_the_forwarder_binds_to_loopback() -> None:
    source = FORWARD_C.read_text()

    assert re.search(r"sin_addr\.s_addr\s*=\s*htonl\(INADDR_LOOPBACK\)", source)
    assert "INADDR_ANY" not in source
