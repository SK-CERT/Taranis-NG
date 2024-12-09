#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running sse forward in the background..."
/usr/local/bin/forward --sender-port 5000 --client-port 5001 &

echo "Running migrations..."
python db_migration.py
echo "Migrations are done."

if [ "$(python ./manage.py collector --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ] && [ x"$SKIP_DEFAULT_COLLECTOR" != "true" ]; then
    (
    echo "Creating default collector..."
    echo "Reading API key from file..."
    API_KEY=$(cat "/run/secrets/api_key")
    python ./manage.py collector --create --name "Default Docker Collector" --description "A local collector node configured as a part of Taranis NG default installation." --api-url "http://collectors/" --api-key "$API_KEY"
    )
else
    echo "Default collector already exists or SKIP_DEFAULT_COLLECTOR is set to true."
fi

echo "prestart.sh finished."
