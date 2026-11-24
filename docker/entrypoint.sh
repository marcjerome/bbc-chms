#!/usr/bin/env bash
set -e

# Wait for Postgres when DATABASE_URL points at it.
if [[ "${DATABASE_URL:-}" == postgres* ]]; then
    python - <<'PY'
import os, time
import psycopg
for attempt in range(30):
    try:
        psycopg.connect(os.environ["DATABASE_URL"]).close()
        break
    except psycopg.OperationalError:
        print("Waiting for database...", flush=True)
        time.sleep(2)
else:
    raise SystemExit("Database never became available")
PY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py setup_roles

if [[ "${SEED_DEMO:-false}" == "true" ]]; then
    python manage.py seed_demo
fi

if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
    python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists."
fi

exec "$@"
