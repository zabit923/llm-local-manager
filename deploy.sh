#!/bin/bash
set -a
source "$(dirname "$0")/.env"
set +a
docker stack deploy -c "$(dirname "$0")/docker-compose.stack.haproxy.yml" pay_stack
