#!/bin/sh
set -e

echo "Waiting for database..."
until python -c 'import django; django.setup(); from django.db import connection; connection.ensure_connection()' 2>/dev/null; do
  echo "Database unavailable - retrying in 2s..."
  sleep 2
done
echo "Database is ready."

python manage.py migrate --noinput

exec gunicorn financial_accounting.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
