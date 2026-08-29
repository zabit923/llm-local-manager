#!/bin/sh
set -e

echo "Starting SSL certificate renewal: $(date '+%Y-%m-%d %H:%M:%S')"

certbot renew \
  --webroot \
  --webroot-path=/var/www/certbot \
  --non-interactive \
  --quiet \
  --deploy-hook "echo 'Certificates renewed at $(date)'"

RENEW_EXIT_CODE=$?

if [ $RENEW_EXIT_CODE -eq 0 ]; then
  echo "✓ Certificate renewal completed"
  certbot certificates
  exit 0
else
  echo "✗ Certificate renewal failed (exit code: $RENEW_EXIT_CODE)"
  certbot certificates
  exit 1
fi
