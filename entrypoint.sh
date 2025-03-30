#!/usr/bin/env bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Optionally collect static files if needed (uncomment if required)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 