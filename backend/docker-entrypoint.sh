#!/bin/sh
set -eu

# Le schéma n'est jamais créé par l'application : seules les migrations Alembic le modifient.
alembic upgrade head

exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000
