#!/usr/bin/env sh
set -e

if [ -f /app/app/main.py ]; then
    DEFAULT_MODULE_NAME=app.main
elif [ -f /app/main.py ]; then
    DEFAULT_MODULE_NAME=main
fi
MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE="${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}"

if [ -f /app/gunicorn_conf.py ]; then
    DEFAULT_GUNICORN_CONF=/app/gunicorn_conf.py
elif [ -f /app/app/gunicorn_conf.py ]; then
    DEFAULT_GUNICORN_CONF=/app/app/gunicorn_conf.py
else
    DEFAULT_GUNICORN_CONF=/gunicorn_conf.py
fi
export GUNICORN_CONF="${GUNICORN_CONF:-$DEFAULT_GUNICORN_CONF}"

if [ "$(id -u)" = "0" ] && [ "${TARANIS_DROP_PRIVILEGES:-true}" = "true" ] && id -u "${TARANIS_USER:-taranis}" >/dev/null 2>&1; then
    TARANIS_USER="${TARANIS_USER:-taranis}"

    for path in ${TARANIS_WRITABLE_PATHS:-}; do
        [ -e "$path" ] || continue
        find "$path" ! -user "$TARANIS_USER" -exec chown -h "$TARANIS_USER" {} + 2>/dev/null || \
            echo "entrypoint: could not chown $path; continuing as $TARANIS_USER anyway" >&2
    done

    # Read-only bind mounts, so they cannot be chowned. Checked here because the
    # alternative is a confusing "Secret file not found" from inside config.py.
    if [ -d /run/secrets ]; then
        unreadable=""
        for secret in /run/secrets/*; do
            [ -f "$secret" ] || continue
            su-exec "$TARANIS_USER" test -r "$secret" || unreadable="$unreadable $secret"
        done
        if [ -n "$unreadable" ]; then
            echo "entrypoint: ERROR: these secrets are not readable by $TARANIS_USER:$unreadable" >&2
            echo "entrypoint: the service now runs unprivileged. Make the files on the" >&2
            echo "entrypoint: host group/world readable - 'chmod 644 docker/secrets/*.txt'. The" >&2
            echo "entrypoint: docker/secrets directory itself stays 0700, so they remain protected." >&2
            exit 1
        fi
    fi

    echo "entrypoint: dropping privileges to $TARANIS_USER" >&2
    exec su-exec "$TARANIS_USER" "$@"
fi

exec "$@"
