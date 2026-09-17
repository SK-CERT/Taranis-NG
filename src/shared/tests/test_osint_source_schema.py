"""What an OSINT source looks like on the wire.

The run-state fields are the awkward ones. They are filled from a Redis cache rather than from
columns, so their Python types are whatever the cache hands back, and the schema has to agree with
that - a mismatch here is not a wrong value but a 500 for the whole sources page.
"""

from typing import ClassVar

from shared.schema.osint_source import OSINTSourceSchema


def make_source(**overrides: object) -> object:
    """A minimal object shaped like the model the schema dumps."""

    class Source:
        id = "source-1"
        name = "A source"
        description = ""
        collector_id = "collector-1"
        parameter_values: ClassVar[list] = []
        word_lists: ClassVar[list] = []
        last_attempted = None
        last_collected = None
        last_error_message = None
        enabled = True
        collecting = False
        next_run = None
        status = "green"

    source = Source()
    for key, value in overrides.items():
        setattr(source, key, value)
    return source


def test_next_run_is_dumped_as_the_iso_string_the_cache_holds() -> None:
    # The cache stores what the collector reported, an ISO 8601 string. Declaring this field as a
    # DateTime made marshmallow call strftime on it, which 500s the whole sources listing.
    dumped = OSINTSourceSchema().dump(make_source(next_run="2026-09-04T14:30:00+00:00"))

    assert dumped["next_run"] == "2026-09-04T14:30:00+00:00"


def test_a_source_with_no_schedule_dumps_a_null_next_run() -> None:
    dumped = OSINTSourceSchema().dump(make_source(next_run=None))

    assert dumped["next_run"] is None


def test_the_run_state_fields_are_dumped_for_the_gui() -> None:
    dumped = OSINTSourceSchema().dump(make_source(collecting=True, enabled=False))

    assert dumped["collecting"] is True
    assert dumped["enabled"] is False


def test_the_derived_fields_are_never_loaded_back() -> None:
    # collecting and next_run describe a running node; a node must not be able to send them back.
    loaded = OSINTSourceSchema().load(
        {
            "id": "source-1",
            "name": "A source",
            "description": "",
            "collector_id": "collector-1",
            "parameter_values": [],
            "word_lists": [],
            "last_attempted": None,
            "last_collected": None,
            "collecting": True,
            "next_run": "2026-09-04T14:30:00+00:00",
        },
    )

    assert not hasattr(loaded, "collecting")
    assert not hasattr(loaded, "next_run")
    # enabled is different: the node needs it, so it loads, defaulting to True for an older core.
    assert loaded.enabled is True
