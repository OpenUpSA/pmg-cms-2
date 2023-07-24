#web: gunicorn --workers $GUNICORN_WORKERS --worker-class gevent --timeout $GUNICORN_TIMEOUT --max-requests $GUNICORN_MAX_REQUESTS --max-requests-jitter 100 --log-file - --access-logfile - pmg:app
web: gunicorn --workers 5 --worker-class gevent --timeout 30 --max-requests 10000 --max-requests-jitter 100 --log-file - --access-logfile - pmg:app
worker: python app.py start_scheduler