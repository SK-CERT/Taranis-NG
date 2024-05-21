#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running sse forward in the background..."
/usr/local/bin/forward --sender-port 5000 --client-port 5001 &

echo "Running migrations..."
python /app/db_migration.py db upgrade head

if [ "$(python ./manage.py collector --list | wc -l)" == 0 ] && [ x"$SKIP_DEFAULT_COLLECTOR" != "xtrue" ]; then
    (
    echo "Adding default collector"
    if [ -z "$API_KEY_FILE" ]; then
        echo "API_KEY_FILE variable is not set, will use API_KEY..."
    else
        echo "Reading API key from file..."
        API_KEY=$(cat "$API_KEY_FILE")
    fi
    python ./manage.py collector --create --name "Default Docker Collector" --description "A local collector node configured as a part of Taranis NG default installation." --api-url "http://collectors/" --api-key "$API_KEY"
    ) &
fi

echo "Done."
