#!/bin/sh
set -e

# -----------------------------------------------------------------------
# 1. Resolve DATABASE_URL
# -----------------------------------------------------------------------
if [ -z "$DATABASE_URL" ] && [ -n "$DATABASE_PUBLIC_URL" ]; then
  export DATABASE_URL="$DATABASE_PUBLIC_URL"
  echo "DATABASE_URL was not set — using DATABASE_PUBLIC_URL instead."
fi

# -----------------------------------------------------------------------
# 2. If PGHOST is not already set but DATABASE_URL is, extract individual
#    PG* vars from the URL using Python.  This avoids all URL-parsing bugs
#    in dj_database_url by letting Django connect with explicit credentials.
# -----------------------------------------------------------------------
if [ -z "$PGHOST" ] && [ -n "$DATABASE_URL" ]; then
  echo "PGHOST not set — extracting PG* vars from DATABASE_URL..."
  eval "$(python <<'PYEOF'
import os, sys
from urllib.parse import urlparse, unquote

url = os.environ.get("DATABASE_URL", "")
try:
    p = urlparse(url)
    host = p.hostname or ""
    port = str(p.port) if p.port else "5432"
    name = p.path.lstrip("/") if p.path else ""
    user = unquote(p.username) if p.username else ""
    pw   = unquote(p.password) if p.password else ""
    # Shell-safe export using Python repr for quoting
    print(f"export PGHOST={repr(host)}")
    print(f"export PGPORT={repr(port)}")
    print(f"export PGDATABASE={repr(name)}")
    print(f"export PGUSER={repr(user)}")
    print(f"export PGPASSWORD={repr(pw)}")
except Exception as exc:
    print(f'echo "ERROR parsing DATABASE_URL: {exc}"', file=sys.stderr)
    sys.exit(1)
PYEOF
)"
  echo "  Extracted: PGHOST=$PGHOST  PGDATABASE=$PGDATABASE  PGUSER=$PGUSER"
fi

# -----------------------------------------------------------------------
# 3. Diagnostics
# -----------------------------------------------------------------------
if [ -z "$PGHOST" ] && [ -z "$DATABASE_URL" ]; then
  echo "WARNING: No database configuration found."
  echo "  Set DATABASE_URL or the individual PG* variables."
fi

echo "DB config:"
echo "  PGHOST     = ${PGHOST:-<not set>}"
echo "  PGPORT     = ${PGPORT:-<not set>}"
echo "  PGDATABASE = ${PGDATABASE:-<not set>}"
echo "  PGUSER     = ${PGUSER:-<not set>}"
if [ -n "$PGPASSWORD" ]; then
  echo "  PGPASSWORD = set (${#PGPASSWORD} chars)"
else
  echo "  PGPASSWORD = <not set>"
fi

# -----------------------------------------------------------------------
# 4. Wait for the database
# -----------------------------------------------------------------------
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-financial_accounting.settings}"

echo "Waiting for database..."
attempts=0
max_attempts=30
until python -c 'import django; django.setup(); from django.db import connection; connection.ensure_connection()' 2>/tmp/db_check_err.log; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge "$max_attempts" ]; then
    echo "ERROR: Could not connect after $max_attempts attempts. Last error:"
    cat /tmp/db_check_err.log
    exit 1
  fi
  if [ "$attempts" -eq 1 ] || [ $((attempts % 5)) -eq 0 ]; then
    echo "--- Last error (attempt $attempts) ---"
    cat /tmp/db_check_err.log
    echo "--------------------------------------"
  fi
  echo "Database unavailable - retrying in 2s... (attempt $attempts)"
  sleep 2
done
echo "Database is ready."

# -----------------------------------------------------------------------
# 5. Migrate & seed (if empty) & serve
# -----------------------------------------------------------------------
python manage.py migrate --noinput

# Seed demo data if the database has no entities (first deploy / fresh DB)
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_accounting.settings')
django.setup()
from api.models import Entity
if Entity.objects.count() == 0:
    print('DATABASE_EMPTY: seeding demo data...')
    from django.core.management import call_command
    call_command('seed_data')
    print('Seed complete.')
else:
    print(f'Database already has {Entity.objects.count()} entities — skipping seed.')
"

exec gunicorn financial_accounting.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
