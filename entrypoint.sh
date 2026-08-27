#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
