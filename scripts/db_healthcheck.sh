#!/bin/sh
export PGPASSWORD=$(cat /run/secrets/postgres_password)
pg_isready -U "$(cat /run/secrets/postgres_user)" -d "$POSTGRES_DB" -h 127.0.0.1
