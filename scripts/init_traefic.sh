#!/usr/bin/env bash
set -euo pipefail

#SETUP_WHITELIST_IP=YOUR IP bash docker/init_traefik.sh

if [[ -f ./docker/traefik_dynamic.yml ]]; then
  echo "SKIP: traefik_dynamic.yml уже существует"
  exit 0
fi

if [[ -z "${SETUP_WHITELIST_IP:-}" ]]; then
  echo "ERROR: SETUP_WHITELIST_IP не задан"
  exit 1
fi

envsubst '${SETUP_WHITELIST_IP}' \
  <./docker/traefik_dynamic.yml.template \
  >./docker/traefik_dynamic.yml

echo "OK: traefik_dynamic.yml создан (IP: ${SETUP_WHITELIST_IP})"
