#!/usr/bin/env bash

TRY_LOOP="20"


# Wait for Postresql
if [ "$1" = "webserver" ] || [ "$1" = "worker" ] || [ "$1" = "scheduler" ] ; then
  i=0
  while ! nc -z $POSTGRES_HOST $POSTGRES_PORT >/dev/null 2>&1 < /dev/null; do
    i=$((i+1))
    if [ "$1" = "webserver" ]; then
      echo "$(date) - Waiting for database @ ${POSTGRES_HOST}:${POSTGRES_PORT}... $i/$TRY_LOOP"
      if [ $i -ge $TRY_LOOP ]; then
        echo "$(date) - ${POSTGRES_HOST}:${POSTGRES_PORT} could not reached, giving up"
        exit 1
      fi
    fi
    sleep 10
  done
fi

echo "Initialize database..."
airflow initdb
exec airflow webserver &
exec airflow scheduler
