# Default vulnerability template migration

**Audience:** presenter operators and developers.

**Status:** supported migration for the official vulnerability template only;
it is not the installer for the complete distribution preset/template bundle.

This package promotes the redesigned Taranis NG vulnerability PDF on existing
presenter installations without treating `/app/templates` as disposable.
Fresh images already ship the redesigned template as `pdf_template.html` and
the former template byte-for-byte as `pdf_template_legacy.html`.

At presenter startup, `promote_default_vulnerability.py` applies this table:

| Installed `pdf_template.html` | Result |
| --- | --- |
| Missing | Install the versioned payload |
| Known official legacy SHA-256 | Install companions, then replace the entry |
| Current payload SHA-256 | No-op, or restore missing exact companions |
| Any other content | Preserve everything and log the unknown hash |
| Symlink or non-regular file | Preserve everything and log the conflict |

Companion paths are preflighted before any write. Existing companion content
must either match the payload exactly or the entire migration is skipped. Each
write is atomic, and `pdf_template.html` is replaced last so an interruption
cannot expose a template whose macro or asset is absent.

The migration never reads, writes, or traverses `user_templates`; custom
presenters remain operator-managed. It makes no database, product-type,
Compose, or volume changes.

Operators can inspect the decision without writing:

```sh
python3 /app/template_migrations/promote_default_vulnerability.py --dry-run
```

Set `TARANIS_SKIP_DEFAULT_TEMPLATE_MIGRATION=1` to opt out. The prestart hook
logs a warning and continues if the migration itself fails, preserving service
availability. Migration payloads are versioned under `v2/payload`; adding a
future official legacy hash requires an explicit reviewed code change.
