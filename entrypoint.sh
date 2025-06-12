#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn --workers=3 --worker-class=gevent --timeout=120 --access-logfile=- --error-logfile=- --bind=0.0.0.0:8000 atmp_project.wsgi:application
