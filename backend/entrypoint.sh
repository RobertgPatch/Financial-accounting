#!/bin/sh
set -e

# Railway exposes DATABASE_URL (private network) and DATABASE_PUBLIC_URL (public proxy).
# If DATABASE_URL is not set, fall back to DATABASE_PUBLIC_URL so the connection succeeds
# regardless of which variable the user configured or Railway linked.
if [ -z "$DATABASE_URL" ] && [ -n "$DATABASE_PUBLIC_URL" ]; then
  export DATABASE_URL="$DATABASE_PUBLIC_URL"
  echo "DATABASE_URL was not set — using DATABASE_PUBLIC_URL instead."
fi

if [ -z "$DATABASE_URL" ]; then
  echo "WARNING: Neither DATABASE_URL nor DATABASE_PUBLIC_URL is set."
  echo "The app will fall back to SQLite. Set DATABASE_URL to your PostgreSQL connection string."
fi

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-financial_accounting.settings}"

echo "Waiting for database..."
echo "  Hint: ensure DATABASE_URL (or DATABASE_PUBLIC_URL) is set and the database is reachable."
attempts=0
until python -c 'import django; django.setup(); from django.db import connection; connection.ensure_connection()' 2>/tmp/db_check_err.log; do
  attempts=$((attempts + 1))
  if [ $((attempts % 5)) -eq 1 ]; then
    echo "--- Last error output ---"
    cat /tmp/db_check_err.log
    echo "-------------------------"
  fi
  echo "Database unavailable - retrying in 2s... (attempt $attempts)"
  sleep 2
done
echo "Database is ready."

python manage.py migrate --noinput

exec gunicorn financial_accounting.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
