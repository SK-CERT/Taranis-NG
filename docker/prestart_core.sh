#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running sse forward in the background..."
/usr/local/bin/forward --sender-port 5000 --client-port 5001 &

echo "Running migrations..."
python db_migration.py
echo "Migrations are done."

echo "Reading API key from file..."
API_KEY=$(cat "/run/secrets/api_key")

if [ "$(python ./manage.py collector --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ]; then
    (
    echo "Creating default collector node..."
    python ./manage.py collector --create --name "Default Docker Collector" --description "A local collector node configured as a part of Taranis NG default installation." --api-url "http://collectors/" --api-key "$API_KEY"
    ) &
else
    echo "Default collector node already exists."
fi

if [ "$(python ./manage.py bot --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ]; then
    (
    echo "Creating default bot node..."
    python ./manage.py bot --create --name "Default Docker Bot" --description "A local bot node configured as a part of Taranis NG default installation." --api-url "http://bots/" --api-key "$API_KEY"
    ) &
else
    echo "Default bot node already exists."
fi

echo "prestart.sh finished."
