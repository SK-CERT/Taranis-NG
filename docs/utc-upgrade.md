# Upgrading to UTC timestamps

Core and all satellite services now exchange timestamps as ISO 8601 UTC strings,
for example `2026-07-15T10:00:00Z`. The GUI formats these in the browser's local
timezone. Numeric Unix timestamps and calendar-only values such as `2026-07-15`
retain their existing meaning. External API clients must accept the new response
format. Legacy timestamp input formats remain temporarily accepted and are
interpreted as UTC when they contain no offset.

Backend schedules, date boundaries, documents, and exports use UTC. Review daily
and weekly scheduled jobs: an existing `09:00` schedule now runs at 09:00 UTC.
The browser timezone affects display and form entry, not backend scheduling.

## Preserve the original timezone

Do not replace the existing `TZ` in `docker/.env` before this upgrade. Compose
now sets container `TZ` and database `PGTZ` to UTC independently, and forwards
the old `.env` value to the migration as `TARANIS_NG_LEGACY_TZ`. If the original
installation used `TZ=Europe/Bratislava`, leave that value in place. An explicit
`TARANIS_NG_LEGACY_TZ` overrides it. With neither setting present, the migration
assumes UTC. Invalid timezone names stop the migration before data changes.

For a non-Compose deployment, explicitly provide `TARANIS_NG_LEGACY_TZ` to the
migration process before switching the application and database sessions to UTC.
New installations can use `TZ=UTC`.

The migration treats every historical timezone-free timestamp as a wall clock
in that original timezone. Explicit offsets in text values are honored. It
converts timestamp columns to PostgreSQL `timestamp with time zone`, normalizes
recognized publication timestamps (including archived news versions) and `DATE_TIME`
attribute values/defaults, and preserves date-only fields, unknown source text, and
nulls. Existing timezone-aware notification timestamps keep their original instants. It stores migration
metadata and original changed text in `_utc_migration_state` for downgrade;
retain this internal table.

### Historical RSS publication dates

The follow-up revision `b7e4d192a630` corrects legacy RSS publication strings.
The old RSS collector formatted feedparser's UTC tuples as `DD.MM.YYYY - HH:MM`,
without retaining the offset or seconds. Those publication strings must be
interpreted as UTC, while collected timestamps and other local wall clocks still
use the installation's original timezone.

For installations that have already applied the UTC migration, deploy the updated
core image and let startup run the follow-up revision with writers stopped as
above. New installations/upgrades apply both revisions in sequence. The repair
uses `_utc_migration_state` originals and the item's RSS collector association,
including archived versions. It changes only values that still match the first
migration's output; new articles, later edits, non-RSS sources, dates without a
time, and timestamps with explicit offsets remain unchanged. Items whose source
association is missing cannot be reliably identified and remain unchanged.
Identification assumes the source has not been reassigned to a different collector
since ingestion; the backup does not contain historical collector ownership.

For example, the feed time `2026-11-03T10:00:07Z`, formerly stored as
`03.11.2026 - 10:00`, becomes `2026-11-03T10:00:00Z` and displays as 11:00 in
Bratislava. The old collector discarded seconds, so this repair cannot recover
`:07` without retrieving the original feed entry.

Historical daylight-saving overlaps and gaps use PostgreSQL's standard-time
interpretation. For example, Bratislava's repeated `2026-10-25 02:30` becomes
`2026-10-25T01:30:00Z`. A nonexistent `2026-03-29 02:30` also uses the standard
offset and becomes `2026-03-29T01:30:00Z` (03:30 on the real local clock).
Timezone-free values cannot reveal which occurrence of a repeated hour was
originally intended, or whether an installation previously changed timezone.

## Upgrade with writers stopped

Use the new release's images and Compose files. From `docker/`, while the old
stack is still available, back up the database:

```sh
docker compose exec -T postgres pg_dump -U taranis-ng -d taranis-ng -Fc > taranis-ng-before-utc.dump
```

Preserve the backup, the old application release, and the original `.env`. Stop
remote workers on every worker host, then stop the main stack and migrate:

```sh
docker compose stop
docker compose up -d postgres redis
docker compose run --rm --no-deps core python db_migration.py
```

The one-off command runs all pending migrations without starting the API or
scheduler. Do not start writers until it succeeds. Timestamp-column conversion
locks the affected tables and may take time on large databases. The migration
runs transactionally and Alembic records the revision so normal startup does not
convert the values again. Core startup also stops on a migration failure.

Start the updated GUI and services together, then start updated remote workers:

```sh
docker compose up -d
```

Check core startup logs, node heartbeats, collection, report updates, and displayed
times. Compare an API timestamp ending in `Z` with its locally formatted GUI
value. PostgreSQL connection sessions and service containers should report UTC.

## Rollback

Keep all writers stopped during rollback. The safest complete rollback restores
`taranis-ng-before-utc.dump` to an empty replacement database and starts the old
application release with its original timezone configuration; follow the normal
PostgreSQL restore procedure (`pg_restore`) and retain the upgraded database
until rollback is verified. A backup restore discards writes made after the
backup.

When both UTC revisions are applied and the RSS repair is the current Alembic
head, undo the RSS repair first, then the original UTC migration, using the
**new** core image:

```sh
docker compose run --rm --no-deps core python db_migration.py downgrade
docker compose run --rm --no-deps core python db_migration.py downgrade
```

Downgrade uses the timezone saved during upgrade, regardless of current environment
settings. It restores timestamp columns to local wall clocks and restores original
publication/attribute text when that normalized value has not subsequently been
edited. Real instants in a historical DST gap return as their corresponding real
wall time, rather than the nonexistent original time. New or edited text values
remain as written after upgrade. Use the backup restore for an exact restoration
of the previous data. After downgrade, deploy the old release and its original
`TZ`/`PGTZ` settings together before restarting any services.

## Migration integration tests

The migration tests use a separate schema in a disposable PostgreSQL database:

```sh
TARANIS_TEST_POSTGRES_URL=postgresql+psycopg://user:password@localhost/test_db \
    python -m pytest --noconftest --confcutdir=src/core/tests src/core/tests/test_utc_migration.py
```

Without that environment variable, only the database integration cases skip.
Tests cover UTC and Bratislava installations, winter/summer offsets, DST gaps and
overlaps, nulls, explicit offsets, unchanged calendar dates/source text, typed
report attributes, and downgrade preservation of subsequent edits.
