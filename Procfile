web: gunicorn --workers 3 --worker-class gevent --timeout 30 --max-requests 10000 --max-requests-jitter 100 --log-file - --access-logfile - pmg:app
worker: python app.py start_scheduler