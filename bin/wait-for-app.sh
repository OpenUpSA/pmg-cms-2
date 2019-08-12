#!/bin/sh

set -e

cmd="$@"

until curl http://pmg.test:5000; do
  >&2 echo "http://pmg.test:5000 is unavailable - sleeping"
  sleep 1
done

>&2 echo "required services are up"
