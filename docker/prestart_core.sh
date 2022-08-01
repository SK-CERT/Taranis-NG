#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running migrations..."
/app/db_migration.py db upgrade head
echo "Done."
