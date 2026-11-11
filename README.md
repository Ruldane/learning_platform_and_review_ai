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

```bash
cp .env.example .env     # y coller au moins une clé LLM (ou la saisir dans l'interface)
docker compose up -d
# ouvrir http://localhost:5173
```

- Les 7 services : `frontend` (5173), `backend` (8000), `qdrant` (6333), `ollama`, `ollama-init`
  (télécharge `bge-m3` une fois, puis s'arrête), `searxng`, `gotenberg`. Volumes nommés :
  `app_data`, `qdrant_data`, `ollama_data`. `docker compose down` les conserve.
- Le back répond dès que les 4 services sont sains, pendant le téléchargement de `bge-m3` :
  `GET http://localhost:8000/api/v1/health` détaille l'état de chacun.
- macOS (pas de GPU dans Docker) : décommenter `OLLAMA_BASE_URL=http://host.docker.internal:11434`
  dans `.env` pour utiliser l'Ollama installé sur la machine.
- Rechargement à chaud : `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.
- Sous Windows, si `docker compose build` échoue avec « additional privileges requested »,
  définir `BUILDX_BAKE_ENTITLEMENTS_FS=0`.
- Les versions des images sont figées dans `docker-compose.yml` (voir DECISIONS.md, D30).
