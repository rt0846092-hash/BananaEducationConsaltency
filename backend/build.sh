#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Owner account from OWNER_USERNAME / OWNER_PASSWORD, only if it doesn't exist.
python manage.py ensure_owner

# Sample countries, universities, classes and students for a demo. Does
# nothing if content already exists. Leave SEED_DEMO unset for a real client.
if [ "${SEED_DEMO:-False}" = "True" ]; then
  python manage.py seed_demo
fi
