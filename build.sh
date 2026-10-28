#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_faqs_and_errors
python manage.py seed_songs
python manage.py sync_to_mongo || true
