#!/bin/sh

# Default values
: "${GUNICORN_WORKERS:=1}"
: "${GUNICORN_TIMEOUT:=300}"

# Run Gunicorn with the environment variables
exec gunicorn --bind 0.0.0.0:3000 --workers "$GUNICORN_WORKERS" --timeout "$GUNICORN_TIMEOUT" app:app
