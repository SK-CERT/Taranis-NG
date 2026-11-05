# Remote sharing API versions

Remote sharing supports the existing v1 protocol and an explicit UTC v2 protocol.
Authentication remains `Authorization: ApiKey <key>`, and SSE event names, event
IDs and the configured events URL are unchanged.

| Operation | Method | Legacy route | UTC route |
| --- | --- | --- | --- |
| Connect | GET | `/api/v1/remote/connect` | `/api/v2/remote/connect` |
| Disconnect | GET | `/api/v1/remote/disconnect` | `/api/v2/remote/disconnect` |
| Read news | GET | `/api/v1/remote/sync-news-items` | `/api/v2/remote/sync-news-items` |
| Confirm news | PUT | `/api/v1/remote/sync-news-items` | `/api/v2/remote/sync-news-items` |
| Read reports | GET | `/api/v1/remote/sync-report-items` | `/api/v2/remote/sync-report-items` |
| Confirm reports | PUT | `/api/v1/remote/sync-report-items` | `/api/v2/remote/sync-report-items` |

## Version negotiation and failure handling

Updated nodes try the v2 connect endpoint first. A 404 or 405 response means that
endpoint is unavailable, so the client tries v1. Authentication failures, network
errors, malformed successful responses, and server errors do not trigger a
downgrade. Each connection retains its selected version for synchronization,
confirmation, and disconnection. Reconnecting attempts v2 again. Core logs the
negotiated version after a successful connection. If a manual disconnect has no
retained connection state (for example after restart or in another worker), it
tries v2 and falls back to v1 only on 404/405 without first connecting.

A failed peer connection does not prevent core from starting or other peers from
connecting. Invalid batches are rejected before import, and import failures are
not acknowledged. Failed acknowledgments are logged rather than reported as a
successful synchronization. Synchronization can replay an unacknowledged batch;
existing identity handling merges repeated items.

## Timestamp contracts

V1 retains its original response shapes. Connection and synchronization cursors
use `YYYY-MM-DD HH:MM:SS.ffffff`, always with six fractional digits and no offset,
so unmodified old clients can parse them. News `collected` values use
`DD.MM.YYYY - HH:MM`, retaining v1's minute precision. These wall clocks are
formatted and parsed at the configured legacy timezone boundary. Explicit offsets
received from a v1 peer are honored; acknowledgments to old providers are encoded
without an offset for their strict parser.

V2 uses ISO 8601 UTC timestamps ending in `Z`, retaining seconds and microseconds.
Cursor acknowledgments and collected timestamps must include a timezone offset;
timezone-free timestamps are rejected. Offset-bearing inputs are normalized to UTC.
Acknowledgments contain `{"last_sync_time": "<returned cursor>"}` in both versions.
The report payload keeps its existing UUID, title, state and attribute structure;
only its synchronization cursor is versioned.

Publication dates and report/news attribute values are source-owned text rather
than uniformly typed timestamps. Known offset-bearing publication dates are
normalized to UTC for v2 and formatted in the legacy timezone for v1. Unknown text
and date-only publications remain unchanged. Old RSS publications used UTC wall
clocks while other old collectors could use local time, and the old remote
payload does not identify which collector produced a publication. An imported
legacy publication without an offset therefore remains opaque text, including
when it is shared onward or displayed. Its timezone cannot safely be inferred
from the peer's timezone alone. Report attribute values are not recursively
rewritten based on names or timestamp-looking content.

## Legacy timezone configuration

Both **Remote nodes** and **Remote access** have a `legacy_timezone` setting,
validated as an IANA name such as `Europe/Bratislava` or `America/New_York`:

- On a Remote node, it is the timezone used by the old provider's timezone-free
  timestamps. Set it to that provider's historical `TZ`.
- On Remote access, it controls the wall clocks emitted by v1 for the older
  receiving peer. For correct local display on that peer, use the receiver's
  timezone. The previous installation timezone is the compatibility default.

V2 timestamp handling ignores this setting. Reconnect after changing connection
settings so the active client uses the updated timezone.

Migration `d8f7a401c952` initializes existing connections from the original timezone
saved by the UTC migration, falling back to `TARANIS_NG_LEGACY_TZ`, then `TZ`, then
UTC. It preserves existing per-peer timezone columns if a database was already
created with the updated models. Newly submitted configurations that omit the
setting use the preserved environment default; omitted fields on updates retain
the existing per-peer setting. The GUI leaves a blank new setting to the backend
default. SQL inserts without application defaults use UTC.

Check peers with differing timezones individually; one installation-wide default
cannot describe every remote node. V1 retains its limitations: minute precision
for collected dates and ambiguous wall clocks during daylight-saving overlaps.
V2 avoids those ambiguities through explicit offsets.

## Compatibility tests

The Remote Compatibility Tests CI workflow exercises the unmodified v1-only release `26.10.1`
against the current checkout in both provider/consumer directions, plus current peers
using v2. The mixed-version lanes cover UTC and Europe/Bratislava legacy nodes. See
[Remote synchronization compatibility](testing.md#remote-synchronization-compatibility)
for the pinned historical commit, coverage, prerequisites, and local commands.
