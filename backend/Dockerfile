FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || echo "collectstatic skipped (no static files or DB unavailable)"

EXPOSE 8000

CMD ["sh", "-c", "until python -c 'import django; django.setup(); from django.db import connection; connection.ensure_connection()' 2>/dev/null; do echo 'Waiting for database...'; sleep 2; done && python manage.py migrate --noinput && gunicorn financial_accounting.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
