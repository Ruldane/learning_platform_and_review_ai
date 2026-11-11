# Tremplin

Plateforme locale d'apprentissage et de carrière, pilotée par plusieurs agents IA. Elle tourne
entièrement sous Docker sur votre machine : backend FastAPI, frontend React, base vectorielle,
modèles locaux optionnels.

Documents de référence : [SPEC.md](SPEC.md) (la spec), [DECISIONS.md](DECISIONS.md) (les choix et
écarts), `docs/superpowers/plans/` (les plans d'implémentation).

## Prérequis

- Docker et Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12 géré par uv)
- Node.js et pnpm (pour le front, à partir de la tâche 0.11)

## Développement du back

```bash
cd backend
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Contrôles de qualité

Installation des hooks (une fois) :

```bash
uv run --directory backend python -m pre_commit install
```

Exécution manuelle sur tout le dépôt :

```bash
uv run --directory backend python -m pre_commit run --all-files
```

Règles de taille : 300 lignes par fichier et 50 par fonction, vérifiées par
`backend/scripts/check_file_length.py`.

## Lancement avec Docker

À compléter par la tâche qui crée `docker-compose.yml`.
