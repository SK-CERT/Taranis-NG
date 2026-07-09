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
fi

if [ "$(python ./manage.py bot --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ]; then
    (
    echo "Creating default bot node..."
    python ./manage.py bot --create --name "Default Docker Bot" --description "A local bot node configured as a part of Taranis NG default installation." --api-url "http://bots/" --api-key "$API_KEY"
    ) &
fi

(
    if [ "$(python ./manage.py public-web --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ]; then
        echo "Creating default public-web node..."
        python ./manage.py public-web --create --name "Default Public Web" --description "A local public-web feed node configured as a part of Taranis NG default installation." --api-url "http://public-web" --api-key "$API_KEY"
    fi
    # Ensure the default node has a web so the running feed is represented in the GUI.
    echo "Ensuring default public-web web..."
    python ./manage.py public-web --ensure-web --name "Default Public Web" --web-name "Default Web" --hostname "${PUBLIC_WEB_HOSTNAME:-}" --api-url "http://public-web"
) &

echo "Starting scheduler..."
python ./scheduler.py &

echo "prestart.sh finished."
