#!/usr/bin/env bash
set -e
#python app.py start_scheduler &
gunicorn --workers $GUNICORN_WORKERS \
    --worker-class gevent \
    --timeout $GUNICORN_TIMEOUT \
    --max-requests $GUNICORN_MAX_REQUESTS \
    --max-requests-jitter 100 \
    --log-file - \
    --access-logfile - pmg:app \
    --bind 0.0.0.0:8000 &
wait -n