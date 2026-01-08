#!/bin/sh
set -e

# Wait for DB to be available
if [ -n "${DB_HOST}" ]; then
  echo "Waiting for database ${DB_HOST}:${DB_PORT:-3306}..."
  until nc -z ${DB_HOST} ${DB_PORT:-3306}; do
    sleep 1
  done
fi

# Apply migrations and collect static files
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Start application
exec "$@"
