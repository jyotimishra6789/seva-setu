#!/bin/sh
set -eu

umask 077
env_file=/etc/sewasetu.env
{
    printf 'SEWASETU_DB_PASSWORD=%s\n' "${SEWASETU_DB_PASSWORD:-}"
    printf 'SEWASETU_SECRET_KEY=%s\n' "${SEWASETU_SECRET_KEY:-}"
    printf 'SEWASETU_ADMIN_PASSWORD=%s\n' "${SEWASETU_ADMIN_PASSWORD:-}"
    printf 'SEWASETU_ADMIN_USERNAME=%s\n' "${SEWASETU_ADMIN_USERNAME:-admin}"
} > "$env_file"

echo "Running deemed-approval catch-up before starting cron."
. "$env_file"
/usr/local/bin/python /app/scripts/deemed_approval.py >> /var/log/sewasetu/cron.log 2>&1 ||
    echo "Deemed-approval catch-up failed; hourly cron will retry." >&2

exec cron -f
