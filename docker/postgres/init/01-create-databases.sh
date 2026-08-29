#!/bin/bash
# Создаёт обе app-БД при первом старте Postgres-контейнера.
# Выполняется только когда pgdata volume пустой.
# Идемпотентно: при существовании БД — no-op.

set -e

DB_TEST="${POSTGRES_DB_TEST:-postgres_test_01}"
DB_PROD="${POSTGRES_DB_PROD:-postgres_prod_01}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    SELECT 'CREATE DATABASE "$DB_TEST"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_TEST')\gexec

    SELECT 'CREATE DATABASE "$DB_PROD"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_PROD')\gexec
EOSQL
