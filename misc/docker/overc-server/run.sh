#! /usr/bin/env bash
set -eu

# Variables
export OVERC_DB_NAME=${OVERC_DB_NAME:-"overc"}
export OVERC_DB_USER=${OVERC_DB_USER:-"overc"}
export OVERC_DB_PASS=${OVERC_DB_PASS:-"overc"}
export OVERC_DB_HOST=${OVERC_DB_HOST:-"localhost"}
export OVERC_DB_PORT=${OVERC_DB_PORT:-"3306"}
if [ ! -z "$OVERC_DB_LINK" ] ; then
    eval export OVERC_DB_HOST=\$${OVERC_DB_LINK}_TCP_ADDR
    eval export OVERC_DB_PORT=\$${OVERC_DB_LINK}_TCP_PORT
fi

export OVERC_API_AUTH=${OVERC_API_AUTH:-""}
export OVERC_UI_AUTH=${OVERC_UI_AUTH:-""}



# Template
j2 /root/conf/nginx-site.conf > /etc/nginx/sites-enabled/overc.conf

# Passwords
htpasswd -cbd /etc/nginx/htpasswd-api ${OVERC_API_AUTH/:/ }
htpasswd -cbd /etc/nginx/htpasswd-ui ${OVERC_UI_AUTH/:/ }

# Logging
rm -f /var/run/nginx.pid
LOGFILES=$(echo /var/log/{nginx/error,nginx/http.error,nginx/http.access,supervisord,uwsgi}.log)
( umask 0 && truncate -s0 $LOGFILES ) && tail --pid $$ -n0 -F $LOGFILES &



# Launch
export OVERC_CONFIG=/etc/overc/server.ini
export OVERC_DATABASE=mysql://$OVERC_DB_USER:$OVERC_DB_PASS@$OVERC_DB_HOST:$OVERC_DB_PORT/$OVERC_DB_NAME
exec /usr/bin/supervisord -n >/dev/null 2>&1 # it's logging to a file anyway
