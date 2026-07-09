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

# The public-web feed is optional (compose profile "public-web"), so unlike the
# collector and bot nodes its default node is only seeded when the service is
# actually part of this deployment. Seeding it regardless would put a node in
# Configuration -> Public Web that nothing backs: it can never be reached, and
# core would keep dialling a host that does not resolve.
PUBLIC_WEB_PROFILES=$(echo "${COMPOSE_PROFILES:-}" | tr -d ' ')
case ",${PUBLIC_WEB_PROFILES}," in
    *,public-web,*)
        (
            if [ "$(python ./manage.py public-web --list | grep 'Total:' | cut -d ' ' -f2)" == 0 ]; then
                echo "Creating default public-web node..."
                python ./manage.py public-web --create --name "Default Public Web" --description "A local public-web feed node configured as a part of Taranis NG default installation." --api-url "http://public-web" --api-key "$API_KEY"
            fi
            # Ensure the default node has a web so the running feed is represented in
            # the GUI. It is created without a hostname: a node can serve several
            # webs on several hostnames, so that belongs in Configuration ->
            # Public Web, next to the rest of the web's settings.
            echo "Ensuring default public-web web..."
            python ./manage.py public-web --ensure-web --name "Default Public Web" --web-name "Default Web" --api-url "http://public-web"
        ) &
        ;;
    *)
        echo "Public-web feed is not enabled (COMPOSE_PROFILES=\"${COMPOSE_PROFILES:-}\"); skipping its default node."
        ;;
esac

echo "Starting scheduler..."
python ./scheduler.py &

echo "prestart.sh finished."
