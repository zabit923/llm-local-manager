#!/bin/sh
redis-cli -a "$(cat /run/secrets/redis_password)" ping | grep -q PONG
