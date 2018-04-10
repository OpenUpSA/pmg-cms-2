web: newrelic-admin run-program gunicorn --workers 2 --worker-class gevent --timeout 600 --max-requests 3000 --max-requests-jitter 100 --log-file - --access-logfile - pmg:app
