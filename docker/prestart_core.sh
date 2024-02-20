#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running migrations..."
/app/db_migration.py db upgrade head

if [ "$(./manage.py collector --list | wc -l)" -eq 0 ] && [ x"$SKIP_DEFAULT_COLLECTOR" != "xtrue" ]; then
    (
    echo "Adding default collector"
    if [ -z "$API_KEY" ]; then
        echo "API_KEY variable is not set, trying to read from file..."
        API_KEY=$(cat "$API_KEY_FILE")
    fi
    ./manage.py collector --create --name "Default Docker Collector" --description "A local collector node configured as a part of Taranis NG default installation." --api-url "http://collectors/" --api-key "$API_KEY"
    ) &
fi

echo "Done."
