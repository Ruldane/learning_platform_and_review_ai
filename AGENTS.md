# Tremplin

Plateforme locale d'apprentissage et de carrière pilotée par des agents IA, pour une utilisatrice (et quelques comptes en mode Google). Elle tourne sous Docker : back FastAPI + SQLAlchemy async + SQLite + Alembic + LangGraph + Qdrant, front React 19 + TanStack Query + MSW + Vitest.
Back et front sont deux applications qui ne partagent que `contracts/openapi.json`. La spec est `SPEC.md` ; les choix et écarts sont dans `DECISIONS.md`.
Ce fichier guide les agents qui **développent** le dépôt. Un agent qui **pilote** Tremplin par son serveur MCP (Claude Code, Codex) lit `docs/mcp/AGENTS.md` : branchement, jeton, niveaux, limites et règles de conduite.

## Carte du dépôt

- `backend/app/features/<f>/` : `router.py` → `service.py` → `repository.py`, `schemas.py`, et `mcp.py` (déclaration MCP). `features/registry.py` tient `FEATURE_ROUTERS` et `MCP_FEATURES`.
- `backend/app/agents/` (agents `.md` + nœud `.py`, graphes dans `agents/graphs/registry.py` : `GRAPHS`), `providers/` (ports `base` + implémentations), `mcp/` (moteur MCP), `scheduler/` (`JOBS`), `realtime/`, `db/`, `alembic/`, `scripts/`, `tests/`.
- `frontend/src/features/<f>/` (mêmes noms que le back), `src/shared/` (api, i18n, realtime, session-ui, ui, lib), `src/app/registry.ts` (liste des manifestes de features), `e2e/` (Playwright).
- `contracts/openapi.json` ; `sandbox/` (image et lanceur du bac à sable de l'IDE) ; `docs/superpowers/{plans,bilans,recette}` ; `DECISIONS.md`.
- Un plan par phase dans `docs/superpowers/plans/` : ne pas coder une phase sans son plan ; `…-00-plan-directeur.md` §1 fixe l'architecture.

## Architecture

- **Un dossier par feature des deux côtés, mêmes noms.** Ajouter une feature = un dossier + une ligne dans chaque registre (`FEATURE_ROUTERS`, `MCP_FEATURES`, `GRAPHS`, `JOBS`, `app/registry.ts`) ; ne retoucher aucune autre feature.
- Le router reçoit et répond, le service porte la logique, le repository parle à la base. Une feature n'importe d'une autre que son `service`.
- Les contrats import-linter de `backend/pyproject.toml` sont bloquants : les features et agents n'importent jamais une implémentation concrète de `app.providers` ; seul `app.main` importe `app.bootstrap*` ; `app.mcp` n'importe aucune feature ; `app.features` n'importe pas `app.scheduler`.
- Un modèle de langage s'obtient par `get_chat_model(tier)` seulement. Un service externe passe par un port de `providers/`.
- Front : un dossier par composant (`X/X.tsx`, `X.test.tsx`, `index.ts`) ; `components/` est présentationnel (props et callbacks, ni `api.ts`, ni hooks, ni store) ; seules les `pages/` branchent les données ; une feature n'importe jamais une autre feature ; `shared/` n'importe ni `features/` ni `app/`. Contrôlé par ESLint.
- Fichiers ≤ 300 lignes, fonctions ≤ 50 (back : `scripts/check_file_length.py`, front : ESLint). Un fichier qui grossit devient un paquet sans changer ce qu'il exporte.
- **Contrat d'abord.** Une route ou un schéma change : régénérer `contracts/openapi.json`, puis `frontend/src/shared/api/schema.d.ts`, jamais à la main. Les types de l'API ne s'écrivent pas côté front.
- Toute table : `id` UUID texte, `user_id`, `created_at`, `updated_at` ; schéma modifié par Alembic seulement ; toute requête de repository filtre par `user_id`. Une nouvelle route a un test d'isolation entre deux utilisateurs (`backend/tests/isolation/`).
- **MCP** : une nouvelle route est déclarée dans `features/<f>/mcp.py` (action, niveau 1 à 3) ou exclue avec un motif ; le garde `backend/tests/mcp/test_coverage_guard.py` échoue sinon. `python -m scripts.mcp_levels` imprime la table des niveaux. Niveau 4 (clés, auth, réglages de modèles, jeton MCP) : jamais exposé.
- Textes de l'interface en français, centralisés dans `frontend/src/shared/i18n/messages/*.ts` (assemblés par `fr.ts`), jamais en dur dans un composant.

## Sécurité et données

- Ne jamais lire, afficher, copier ni committer `.env`.
- Une clé d'API n'est jamais renvoyée (4 derniers caractères) ni journalisée.
- Erreurs : `{"error": {"code", "message", "details"}}`, message en français. Une 422 ne renvoie jamais l'entrée reçue.
- Les journaux ne portent que des identifiants, nombres, codes et durées : jamais un texte de l'utilisatrice, un e-mail, un lien ni un contenu d'appel MCP.
- Aucun appel réel à un modèle ou au réseau dans les tests : faux fournisseurs et modèles scriptés. Une requête HTTP n'attend jamais un travail d'agent (elle rend un `session_id`).
- Le bac à sable de l'IDE ne reçoit jamais de socket Docker, de réseau, de montage de l'hôte ni de secret. Un agent ou Claude ne modifie jamais le code de l'utilisatrice sans qu'elle accepte (la correction est une proposition).

## Commandes

Back, depuis `backend/` :

```bash
uv sync
uv run pytest tests/<dossier> -q          # la suite complète dure ~40 min : cibler les dossiers touchés
uv run ruff check . && uv run ruff format --check .
uv run python -m mypy app                 # strict
uv run lint-imports
uv run python -m scripts.export_openapi          # régénère ../contracts/openapi.json (--check : vérifie seulement)
uv run python scripts/check_file_length.py <fichiers.py>
uv run alembic upgrade head
uv run python -m scripts.mcp_levels       # table des niveaux MCP
```

Front, depuis `frontend/` (`pnpm <script>` ; sans pnpm, voir « Particularités ») :

```bash
pnpm test                       # vitest run ; un fichier : pnpm test src/features/ide/toView.test.ts
pnpm lint
pnpm typecheck
pnpm gen:api                    # schema.d.ts depuis ../contracts/openapi.json
pnpm gen:api:check              # échoue si schema.d.ts est en retard
pnpm build
pnpm e2e                        # Playwright, parcours n° 1 à 4 ; playwright.auth.config.ts : n° 5
pnpm e2e:docker                 # mêmes parcours, back lancé dans l'image du back
```

Docker, depuis la racine :

```bash
docker build -t learning_career_platform-backend:latest backend       # idem frontend, et sandbox (tag learning_career_platform-sandbox:latest)
docker compose up -d --no-build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up    # rechargement à chaud
```

Les hooks pre-commit (`.pre-commit-config.yaml`) rejouent ruff, longueur, mypy, import-linter, `export_openapi --check`, `gen:api:check`, eslint et tsc. Les tests marqués `live` ou `sandbox_live` sont exclus par défaut ; `sandbox_live` rejoue les tests d'évasion contre le vrai conteneur.

## Façon de travailler

- TDD : un test rouge d'abord, puis le code qui le passe.
- Tout choix non tranché par la spec ou tout écart est une décision `Dnnn` en fin de `DECISIONS.md` (Date, Sujet, Décision numérotée, Raison).
- Commits par chemins explicites (`git add <chemins>`, jamais `-A`), hooks jamais sautés, un hook qui échoue se corrige à la source.
- Interface accessible : contraste AA, tout au clavier, focus visible et jamais sur `body` après une action, animations coupées par `prefers-reduced-motion`.
- Un essai réel (vrai modèle, vrai conteneur) se fait sur une pile jetable nommée `learning_career_platform-check<N>-*`, retirée ensuite ; ne jamais toucher aux volumes ni conteneurs réels, ni à ceux d'autres projets.

## Particularités de ce poste (Windows)

- Smart App Control bloque `pnpm.exe`, le Chromium de Playwright et le `python.exe` du venv. Les outils du front se lancent par `node` : `node frontend/scripts/run-tool.mjs lint|typecheck`, `node frontend/scripts/check-api-types.mjs`, `node node_modules/vitest/vitest.mjs run <chemins>` (depuis `frontend/`).
- Les parcours Playwright tournent sur Edge, par une config temporaire non versionnée, retirée après usage.
- Les hooks pre-commit passent par le Python signé d'uv ; `pre-commit install` écrase ce réglage.
- `docker compose build` demande une autorisation de lecture : construire par `docker build` direct.
- Si un exécutable est bloqué, le dire à l'utilisatrice et attendre ; ne jamais toucher aux réglages de sécurité de Windows.
