#!/usr/bin/env bash
# Запускать на swarm manager от admin_remote (с правами docker)
# После выполнения — удалить скрипт

set -euo pipefail

# ─── Секреты через ввод (не попадают в history) ───────────────────────────────

create_secret_interactive() {
  local name=$1
  if docker secret inspect "$name" &>/dev/null; then
    echo "SKIP: $name уже существует"
    return
  fi
  printf "Enter value for [%s]: " "$name"
  read -rs value
  echo
  if [[ -z "$value" ]]; then
    echo "ERROR: пустое значение для $name — пропущено"
    return 1
  fi
  printf '%s' "$value" | docker secret create "$name" -
  echo "OK: $name создан"
}

# ─── Секреты из файла (для PEM/multiline) ─────────────────────────────────────

create_secret_from_file() {
  local name=$1
  local file=$2
  if docker secret inspect "$name" &>/dev/null; then
    echo "SKIP: $name уже существует"
    return
  fi
  if [[ ! -f "$file" ]]; then
    echo "ERROR: файл $file не найден — пропущено"
    return 1
  fi
  docker secret create "$name" "$file"
  echo "OK: $name создан из $file"
}

# ─── Интерактивные секреты ────────────────────────────────────────────────────

create_secret_interactive postgres_user
create_secret_interactive postgres_password
create_secret_interactive redis_password
create_secret_interactive signing_secret_key
create_secret_interactive invoice_field_encryption_key
create_secret_interactive jwt_secret_key

# ─── PEM-ключи из файлов ──────────────────────────────────────────────────────
# Положи файлы рядом со скриптом перед запуском

create_secret_from_file bank131_private_key ./bank131_private.key
create_secret_from_file bank131_public_key ./bank131_public.key

# ─── Итог ─────────────────────────────────────────────────────────────────────

echo ""
echo "Созданные секреты:"
docker secret ls
