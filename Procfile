web: gunicorn --workers 3 --worker-class gevent --timeout 600 --max-requests 3000 --max-requests-jitter 100 --log-file - --access-logfile - pmg:app
worker: python app.py start_scheduler
