#! /bin/sh

# script for local development of GUI

DEFAULT_DOMAIN="demo.taranis.ng"
PORT=4433

read -p "Domain testgui.[$DEFAULT_DOMAIN]:" DOMAIN
if [ "$DOMAIN" = "" ]; then
    DOMAIN="$DEFAULT_DOMAIN"
fi

export VIRTUAL_HOST="testgui.$DOMAIN"
export VUE_APP_TARANIS_NG_URL="https://$VIRTUAL_HOST/"
export VUE_APP_TARANIS_NG_CORE_API="https://$DOMAIN/api/v1"
export VUE_APP_TARANIS_NG_CORE_SSE="https://$DOMAIN/api/sse"
export VUE_APP_TARANIS_NG_LOCALE="en"
export TZ="Europe/Bratislava"

if egrep -q "^127.0.0.1 +${VIRTUAL_HOST}$" /etc/hosts ; then
    echo "/etc/hosts already points to 127.0.0.1 for $VIRTUAL_HOST"
else
    echo "!!! FIXING /etc/hosts TO CONTAIN 127.0.0.1 $VIRTUAL_HOST !!!"
    sudo sh -c "echo \"127.0.0.1 ${VIRTUAL_HOST}\" >> /etc/hosts"
fi

npm install
./node_modules/.bin/vue-cli-service serve --host "${VIRTUAL_HOST}" --https --port "${PORT}"
