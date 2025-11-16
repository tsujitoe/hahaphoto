#!/bin/sh
set -e

# Run migrations and collectstatic at container start (safe defaults)
echo "Starting entrypoint: collectstatic and launching gunicorn"

# Apply DB migrations (ignore failures to avoid blocking deploys when DB not ready)
python manage.py migrate --noinput || echo "migrate failed or DB not ready"

# Collect static files
python manage.py collectstatic --noinput || echo "collectstatic failed"

# Start gunicorn
exec gunicorn photoalbum.wsgi:application --bind 0.0.0.0:8080 --workers 2
