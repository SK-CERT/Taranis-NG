#! /usr/bin/env sh

echo "Running inside /app/prestart.sh..."

echo "Running sse forward in the background..."
/usr/local/bin/forward --sender-port 5000 --client-port 5001 &

echo "Running migrations..."
python db_migration.py
echo "Migrations are done."

echo "Starting scheduler..."
python ./scheduler.py &

echo "prestart.sh finished."
