#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
# ⚠️ Ligne temporaire pour contourner le conflit d'index
python manage.py migrate payments 0006_kibawallet_fields --fake

# Migration normale pour le reste
python manage.py migrate
