# Official vulnerability template management

**Audience:** presenter operators and developers.

**Scope:** the official vulnerability template only. This is not an installer
for the complete distribution preset/template bundle.

The presenter image supplies the official vulnerability PDF as
`pdf_template.html` and its compatibility payload as
`pdf_template_legacy.html`. Startup management preserves operator-owned
templates and never treats `/app/templates` as disposable.

At presenter startup, `promote_default_vulnerability.py` applies this table:

| Installed `pdf_template.html`             | Result                                       |
| ----------------------------------------- | -------------------------------------------- |
| Missing                                   | Install the versioned payload                |
| Recognized official compatibility SHA-256 | Install companions, then replace the entry   |
| Current payload SHA-256                   | No-op, or restore missing exact companions   |
| Any other content                         | Preserve everything and log the unknown hash |
| Symlink or non-regular file               | Preserve everything and log the conflict     |

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
logs a warning and continues if template management fails, preserving service
availability. Payloads are versioned under `v2/payload`; accepting another
official source hash requires an explicit reviewed code change.
