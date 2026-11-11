# Tremplin

Plateforme locale d'apprentissage et de carrière, pilotée par plusieurs agents IA. Elle tourne
entièrement sous Docker sur votre machine : backend FastAPI, frontend React, base vectorielle,
modèles locaux optionnels.

Documents de référence : [SPEC.md](SPEC.md) (la spec), [DECISIONS.md](DECISIONS.md) (les choix et
écarts), `docs/superpowers/plans/` (les plans d'implémentation).

## Prérequis

- Docker et Docker Compose **2.24 ou plus récent** (`env_file` avec `required: false`) :
  `docker compose version` pour vérifier.
- [uv](https://docs.astral.sh/uv/) (Python 3.12 géré par uv), pour développer le back.
- Node.js 22 ou plus et pnpm (`corepack enable`), pour développer le front.

## Démarrage

```bash
cp .env.example .env     # y coller au moins une clé LLM (ou la saisir plus tard dans l'interface)
docker compose up -d
# ouvrir http://localhost:5173
```

- Le premier démarrage construit les images et télécharge le modèle d'embeddings `bge-m3`
  (environ 1,2 Go) : `docker compose logs -f ollama-init` montre la progression, le service
  s'arrête une fois le modèle en place. L'application répond pendant ce temps.
- État des services : `curl -s http://localhost:8000/api/v1/health` (ou le voyant en haut de
  l'interface). `"status": "ok"` quand la base, les 4 services et au moins une clé LLM sont là ;
  `"degraded"` détaille ce qui manque.
- Les clés API se saisissent aussi dans **Réglages > Modèles et clés** : elles sont chiffrées dans
  le volume `app_data`, seuls leurs 4 derniers caractères sont affichés, et une clé saisie dans
  l'interface prime sur celle du `.env`.
- Arrêt : `docker compose down` (les volumes `app_data`, `qdrant_data`, `ollama_data` sont
  conservés ; `docker compose down -v` efface toutes les données).

### Ports déjà pris

Les ports publiés (sur `127.0.0.1` seulement) sont 5173 (interface), 8000 (API) et 6333
(Qdrant). Si l'un est déjà utilisé par un autre projet, le choisir dans `.env` :

```bash
FRONTEND_PORT=5174
BACKEND_PORT=8001
QDRANT_PORT=6335
```

puis `docker compose up -d --build` (l'adresse de l'API est intégrée à l'interface à la
construction). L'origine autorisée par le back (`CORS_ORIGIN`) suit `FRONTEND_PORT`, et
l'interface est alors sur `http://localhost:<FRONTEND_PORT>` (ou `http://127.0.0.1:<FRONTEND_PORT>` :
les deux formes d'une origine locale sont acceptées). Pour autoriser d'autres origines (un front
lancé hors Docker, par exemple), donner dans `.env` la liste complète, séparée par des virgules :
`CORS_ORIGIN=http://localhost:5174,http://localhost:4173`.

### macOS et Ollama installé sur la machine

Docker n'a pas accès au GPU sous macOS. Pour utiliser l'Ollama de la machine, décommenter
`OLLAMA_BASE_URL=http://host.docker.internal:11434` dans `.env`, puis télécharger le modèle sur
la machine, car `ollama-init` le télécharge dans le conteneur et non dans votre Ollama :

```bash
ollama pull bge-m3
```

### Windows

Si `docker compose build` échoue avec « additional privileges requested », définir
`BUILDX_BAKE_ENTITLEMENTS_FS=0` (Git Bash : `export BUILDX_BAKE_ENTITLEMENTS_FS=0`).

## Ce qui sort de la machine

| Donnée | Destination |
| --- | --- |
| Prompts, qui peuvent contenir le CV et le profil | Le fournisseur LLM choisi |
| Requêtes de recherche | Les moteurs interrogés par SearXNG |
| Tout le reste (base, vecteurs, fichiers, embeddings) | Reste en local |

Le bouton **Tester** d'une clé et la liste des modèles appellent le fournisseur concerné avec
cette clé. Aucune autre donnée ne quitte la machine.

## Services

- Les 7 services : `frontend` (5173), `backend` (8000), `qdrant` (6333), `ollama`, `ollama-init`
  (télécharge `bge-m3` une fois, puis s'arrête), `searxng`, `gotenberg`. Volumes nommés :
  `app_data`, `qdrant_data`, `ollama_data`.
- Le back démarre dès que les 4 services sont sains, sans attendre `bge-m3`.
- Les versions des images sont figées dans `docker-compose.yml` (voir DECISIONS.md, D30).

## Développement

Rechargement à chaud du back et du front dans Docker :

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Développement du back

```bash
cd backend
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python -m mypy app
uv run lint-imports                          # contrats d'import (pyproject.toml)
uv run python -m scripts.export_openapi      # régénère contracts/openapi.json
```

Lancement hors Docker (données dans `backend/data/`, ignoré par git) :

```bash
mkdir -p data && export DATA_DIR=./data
uv run alembic upgrade head
uv run uvicorn --factory app.main:create_app --reload
```

## Développement du front

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173, API attendue sur http://localhost:8000
pnpm test && pnpm lint && pnpm typecheck && pnpm build
pnpm gen:api      # types TypeScript depuis contracts/openapi.json
```

## Contrôles de qualité

Installation des hooks (une fois, depuis la racine du dépôt) :

```bash
uv run --project backend python -m pre_commit install
```

Exécution manuelle sur tout le dépôt :

```bash
uv run --project backend python -m pre_commit run --all-files
```

Règles de taille : 300 lignes par fichier et 50 par fonction, vérifiées par
`backend/scripts/check_file_length.py`. Les frontières d'architecture sont vérifiées par
import-linter (back) et `eslint-plugin-boundaries` (front). Sous Windows, certains exécutables
(`mypy.exe`, `pre-commit.exe`) peuvent être bloqués : les appeler en module (`python -m ...`).
