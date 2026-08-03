#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

# This prestart file is shared by several service images; only the presenter
# image contains the migration package.
TEMPLATE_MIGRATION=/app/template_migrations/promote_default_vulnerability.py
if [ -f "$TEMPLATE_MIGRATION" ] && ! python3 "$TEMPLATE_MIGRATION"; then
    echo "WARNING: default vulnerability template migration failed; existing templates were preserved." >&2
fi
