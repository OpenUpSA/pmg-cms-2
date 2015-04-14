#!/usr/bin/env bash
set -e

source env/bin/activate
source production-env.sh

/var/www/pmg-cms/env/bin/newrelic-admin run-program /var/www/pmg-cms/env/bin/gunicorn -w 8 pmg:app --bind 127.0.0.1:5006 --timeout 30 --max-requests 1500 --max-requests-jitter 100 --pid gunicorn.pid --log-file - --access-logfile -
