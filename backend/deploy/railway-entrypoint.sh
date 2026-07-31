#!/bin/sh
set -eu

export PORT="${PORT:-8000}"
storage_root="${STORAGE_ROOT:-/data/storage}"

# Railway mounts a new volume as root. Prepare only PDFFlow's own directory,
# then run all network-facing processes as the unprivileged application user.
install -d -o pdfflow -g pdfflow -m 700 \
  "$storage_root" "$storage_root/uploads" "$storage_root/processed"

exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
