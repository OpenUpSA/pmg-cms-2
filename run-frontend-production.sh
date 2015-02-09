#!/usr/bin/env bash
set -e

source env/bin/activate
source production-env.sh

# catch SIGHUP and send to children, this tells gunicorn to restart gracefully
trap sighup 1

sighup() {
  kill -HUP $child
}

/var/www/pmg-cms/env/bin/newrelic-admin run-program /var/www/pmg-cms/env/bin/gunicorn -w 4 frontend:app --bind 127.0.0.1:5006 --timeout 30 --log-file -
child=$!

while true; do
  wait $child
done
