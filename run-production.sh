#!/usr/bin/env bash
set -e

source env/bin/activate
source production-env.sh

/var/www/pmg-cms/env/bin/newrelic-admin run-program /var/www/pmg-cms/env/bin/gunicorn -w 6 pmg:app --bind 127.0.0.1:5006 --timeout 30 --max-requests 2000 --max-requests-jitter 100 --pid gunicorn.pid --log-file -
