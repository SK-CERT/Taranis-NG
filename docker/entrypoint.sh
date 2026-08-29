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

# Drop to an unprivileged user (CESNET pentest, SK-CERT#723: every service used
# to run its whole Python stack as uid 0, so an RCE started as root).
#
# The drop happens here rather than via a Dockerfile `USER` line because the
# volumes must still be re-owned as root on the way past: named volumes
# (/data, /app/templates, /app/storage) take their ownership from the image
# directory the FIRST time they are mounted, so existing deployments already
# have root-owned contents and a `USER` line alone would leave every upgraded
# install unable to write to its own data.
#
# TARANIS_DROP_PRIVILEGES=false keeps the old behaviour for anyone who needs it.
if [ "$(id -u)" = "0" ] && [ "${TARANIS_DROP_PRIVILEGES:-true}" = "true" ] && id -u "${TARANIS_USER:-taranis}" >/dev/null 2>&1; then
    TARANIS_USER="${TARANIS_USER:-taranis}"

    # /app itself plus whatever this service declares as writable at runtime.
    for path in /app ${TARANIS_WRITABLE_PATHS:-}; do
        [ -e "$path" ] || continue
        # -h so a symlinked mount point is not followed out of the container.
        chown -RhH "$TARANIS_USER" "$path" 2>/dev/null || \
            echo "entrypoint: could not chown $path; continuing as $TARANIS_USER anyway" >&2
    done

    # Secrets are bind-mounted read-only, so they cannot be chowned. The files
    # docker/secrets/ ships are 0644 inside a 0700 directory, which the runtime
    # user can read - but an operator who tightens them to 0600 would otherwise
    # get a confusing "Secret file not found" from deep inside config.py at
    # import time. Check here instead and say exactly what to do.
    if [ -d /run/secrets ]; then
        unreadable=""
        for secret in /run/secrets/*; do
            [ -f "$secret" ] || continue
            su-exec "$TARANIS_USER" test -r "$secret" || unreadable="$unreadable $secret"
        done
        if [ -n "$unreadable" ]; then
            echo "entrypoint: ERROR: these secrets are not readable by $TARANIS_USER:$unreadable" >&2
            echo "entrypoint: the service now runs unprivileged (SK-CERT#723). Make the files on the" >&2
            echo "entrypoint: host group/world readable - 'chmod 644 docker/secrets/*.txt'. The" >&2
            echo "entrypoint: docker/secrets directory itself stays 0700, so they remain protected." >&2
            exit 1
        fi
    fi

    echo "entrypoint: dropping privileges to $TARANIS_USER" >&2
    exec su-exec "$TARANIS_USER" "$@"
fi

exec "$@"
