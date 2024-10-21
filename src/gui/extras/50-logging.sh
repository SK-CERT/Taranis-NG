#!/bin/sh

# Default to error logging if LOG_LEVEL is not set
NGINX_LOG_LEVEL=${NGINX_LOG_LEVEL:-error}
NGINX_ACCESS_LOG=${NGINX_ACCESS_LOG:-off}

# Modify nginx.conf with the specified log level
sed -i "s/error_log .*/error_log \/var\/log\/nginx\/error.log $NGINX_LOG_LEVEL;/" /etc/nginx/nginx.conf


# Read the NGINX_ACCESS_LOG environment variable
ACCESS_LOG=${NGINX_ACCESS_LOG:-"on"}  # Default to "on" if not set

if [ "$ACCESS_LOG" = "off" ]; then
    # Disable access logs
    sed -i "s|access_log .*|access_log off;|" /etc/nginx/nginx.conf
else
    # Enable access logs
    sed -i "s|access_log .*|access_log /var/log/nginx/access.log main;|" /etc/nginx/nginx.conf
fi
