# Tremplin — Plan directeur

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the phase plans task-by-task. Ce document fixe l'architecture et l'ordre des phases. Chaque phase a son plan détaillé dans `docs/superpowers/plans/` ; on ne code jamais une phase sans son plan détaillé.

**Goal:** Construire en local sous Docker la plateforme d'apprentissage et de carrière multi agents décrite dans la spec (19 features, 17 agents, 16 graphes), avec un front et un back strictement séparés et une structure où ajouter une feature ne demande de toucher aucun code existant, hormis une ligne d'enregistrement de chaque côté.

**Architecture:** Deux applications indépendantes qui ne partagent qu'un contrat : le schéma OpenAPI (`contracts/openapi.json`) et le catalogue des événements temps réel. Le back est un monolithe modulaire FastAPI : un dossier par feature (router → service → repository), des registres pour les features, graphes, agents, fournisseurs, tâches planifiées. Le front est une SPA React découpée en features autonomes déclarées par un manifeste, avec un composant par dossier.

**Tech Stack:** Python 3.12, uv, FastAPI, SQLAlchemy 2 async + aiosqlite, Alembic, Pydantic v2, LangChain, LangGraph, langgraph-checkpoint-sqlite, APScheduler, Qdrant, Ollama (`bge-m3`), SearXNG, Gotenberg 8 · React, TypeScript strict, Vite, pnpm, Tailwind CSS, shadcn/ui, React Router, TanStack Query, Zustand, openapi-typescript + openapi-fetch, Excalidraw + `@excalidraw/mermaid-to-excalidraw`, React Flow + elkjs, Recharts · pytest, Vitest, Testing Library, Playwright.

**Spec:** `SPEC.md` à la racine (copie de `Spec plateforme d'apprentissage et de carrière multi agents.md`, faite à la tâche 0.1).

## Global Constraints

Recopiées de la spec. Toute tâche de toute phase les respecte implicitement.

- 300 lignes au maximum par fichier, 50 par fonction. Bloquant en pre commit des deux côtés (12.2).
- Un dossier par feature, des deux côtés, avec les mêmes noms (12.2).
- Back : le routeur reçoit et répond, le service porte la logique, le repository parle à la base. Un routeur n'appelle jamais la base (12.2).
- Tout service externe passe par une interface dans `backend/app/providers/` ; les features ne connaissent que l'interface (12.2).
- Un agent = un prompt `.md` + un nœud `.py`. Un graphe = un fichier (12.2).
- Types TypeScript de l'API générés depuis OpenAPI, jamais écrits à la main (12.2).
- Chaque table : `id` (UUID texte), `user_id`, `created_at`, `updated_at`, dates UTC ISO ; types SQLite uniquement, JSON pour le souple ; schéma modifié uniquement par Alembic (13.1).
- Toute requête de repository filtre par `user_id`, même en local (13.1).
- API sous `/api/v1`, JSON `snake_case`, erreurs `{error: {code, message, details}}` avec message en français, OpenAPI sur `/api/docs` (14.3).
- Aucune requête HTTP n'attend la fin d'un travail d'agent : elle renvoie un `session_id` en moins de 2 s (14.1, 14.3).
- Le WebSocket ne porte que des événements serveur → client ; toute action de l'utilisatrice passe par REST (14.1).
- Aucun agent n'instancie un modèle : `get_chat_model(tier)` uniquement. Niveaux `rapide`, `standard`, `fort`, `vision`, Haiku partout par défaut (11.1, 11.2).
- Identifiants de modèles regroupés dans `model_defaults.py` (`claude-haiku-5-5`, `claude-sonnet-5-5`, à revérifier), prix dans `model_prices.json` (11.2, 11.5).
- Clé API jamais renvoyée au navigateur (4 derniers caractères seulement), jamais journalisée, chiffrée avec `APP_SECRET` (11.3).
- Aucun effet de bord avant `interrupt()` dans un même nœud (9.4).
- Sortie structurée = schéma Pydantic, 2 nouveaux essais puis événement d'erreur lisible ; 120 s max par nœud (9.6).
- Tests : aucun appel LLM réel, faux fournisseur déterministe (18.2).
- Interface en français, textes centralisés dans `frontend/src/shared/i18n/fr.ts` ; thème clair uniquement ; contraste AA ; animations < 300 ms coupées par `prefers-reduced-motion` (1, 15.4).
- Avec une seule clé LLM dans `.env`, `docker compose up` suffit (18.3).
- Ne rien ajouter hors spec. Tout écart ou choix non tranché par la spec est consigné dans `DECISIONS.md` (18.2).

## Review Focus

Modes de défaillance que la spec implique mais qu'aucun critère d'acceptation ne teste directement. Chacun a son test dans la tâche qui possède le code.

1. **Redémarrage du back pendant une session** (en cours ou en attente de réponse) : la session reprend au même point, sans doubler une écriture en base ni un appel payant. → Phase 1, tâche 1.6 (test de reprise après recréation du runner).
2. **Reconnexion WebSocket** avec `after_seq` pendant qu'un agent écrit : aucun événement perdu ni affiché deux fois. → Phase 1, tâches 1.7 (serveur) et 1.10 (client, dédoublonnage par `seq`).
3. **Clé absente ou invalide pour le niveau demandé** (ex. niveau `fort` sur GLM sans clé GLM) : erreur lisible en français, pas de 500, et la session échoue proprement avec `run.failed`. → Phase 0, tâche 0.7 ; Phase 1, tâche 1.6.
4. **`APP_SECRET` régénéré** (volume supprimé) : les clés en base ne se déchiffrent plus ; l'app démarre, affiche « clé à ressaisir » au lieu de planter. → Phase 0, tâche 0.5.
5. **Accès croisé entre utilisateurs** : un repository appelé sans `user_id` ou avec celui d'un autre ne renvoie rien. → Phase 0, tâche 0.4 (repository de base), puis un test par routeur à chaque phase.

---

## 1. Principes d'extensibilité

La demande : front et back séparés, chaque composant du front séparé, et des features ajoutables sans réécrire l'existant. Voici les mécanismes qui le garantissent.

### 1.1 Séparation front / back

- `frontend/` et `backend/` ont chacun leur `Dockerfile`, leurs dépendances, leurs tests, leur lint. Aucun import de l'un vers l'autre.
- Le seul lien est le **contrat** dans `contracts/` à la racine :
  - `contracts/openapi.json` : produit par `backend/scripts/export_openapi.py`, consommé par `pnpm gen:api` qui génère `frontend/src/shared/api/schema.d.ts`.
  - Les événements temps réel (9.5) sont des modèles Pydantic exposés dans l'OpenAPI (modèle `SessionEvent` en union discriminée sur `type`), donc typés côté front par la même génération.
- Un test CI côté back échoue si `contracts/openapi.json` n'est pas à jour (`export_openapi.py --check`).

### 1.2 Back end : monolithe modulaire

**Forme d'une feature** (`backend/app/features/<nom>/`) :

| Fichier | Rôle | Peut importer |
| --- | --- | --- |
| `router.py` | Expose `router: APIRouter`. Valide l'entrée, appelle le service, renvoie un schéma | `service`, `schemas`, `app.core.deps` |
| `service.py` | Logique métier. Seul point d'entrée public de la feature pour les autres features | `repository`, `schemas`, interfaces `app.providers.*.base`, services publics d'autres features |
| `repository.py` | Requêtes SQLAlchemy, toutes filtrées par `user_id` (hérite de `UserScopedRepository`) | `app.db` |
| `schemas.py` | Modèles Pydantic d'entrée et de sortie de l'API | rien de la feature |

Si un fichier approche 300 lignes, il devient un paquet (`service/__init__.py`, `service/planning.py`, …) sans changer ce qu'il exporte.

**Registres** : ajouter un élément = un fichier + une ligne dans le registre, rien d'autre.

| Registre | Fichier | Contenu |
| --- | --- | --- |
| Features | `app/features/registry.py` | `FEATURE_ROUTERS: list[APIRouter]`, monté par `main.py` |
| Fournisseurs LLM | `app/providers/llm/registry.py` | `LLM_PROVIDERS: dict[str, LlmProvider]` |
| Contrôles de santé | `app/bootstrap.py` (`_health_checks`) | `list[HealthCheck]` (interface `app/providers/health.py`), posée sur `Providers.health_checks` et lue par la feature `health` (D28) |
| Agents | `app/agents/registry.py` | `AGENTS: dict[str, AgentSpec]` |
| Graphes | `app/agents/graphs/registry.py` | `GRAPHS: dict[str, GraphSpec]`, lu par `POST /sessions` |
| Tâches planifiées | `app/scheduler/registry.py` | `JOBS: list[JobSpec]` |
| Modèles de tables | `app/db/models/__init__.py` | import des modules de modèles pour Alembic |

**Injection des dépendances** : les fournisseurs sont construits une fois au démarrage (lifespan) dans un objet `Providers` posé sur `app.state.providers`, et servis par des dépendances FastAPI (`app/core/deps.py`). Les tests remplacent n'importe lequel via `app.dependency_overrides`. C'est aussi le point unique à réécrire pour Cloudflare.

**Contrats d'import vérifiés** par `import-linter` (bloquant en pre commit) :

1. Couches dans chaque feature : `router` → `service` → `repository`. Un `router` n'importe jamais `repository` ni `app.db`. Les contrats portent sur `app.features.*` : une nouvelle feature est vérifiée sans être nommée.
2. Une feature n'importe d'une autre feature que son `service` (jamais son `repository` ni son `router`) ; seul `app/features/registry.py` importe les routeurs de toutes les features.
3. `app.features` et `app.agents` n'importent jamais une implémentation concrète de `app.providers` (`anthropic`, `openai`, `glm`, `qdrant`, `ollama`, `searxng`, `brave`, `gotenberg`, `local`), seulement `base` et les fabriques.
4. `app.providers` n'importe jamais `app.features` ni `app.agents`.

### 1.3 Front end : features autonomes et composants séparés

**Forme d'une feature** (`frontend/src/features/<nom>/`) :

```text
<nom>/
  manifest.ts          # id, routes, entrée de navigation
  api.ts               # appels typés (client généré), aucune logique d'affichage
  hooks/               # un hook par fichier, TanStack Query ou Zustand
  pages/               # un dossier par écran : compose hooks et composants
  components/          # un dossier par composant
    WeekCalendar/
      WeekCalendar.tsx
      WeekCalendar.test.tsx
      index.ts
  types.ts             # types locaux dérivés des types générés
```

**Règles, vérifiées par ESLint** (`eslint-plugin-boundaries` + règles natives) :

- Un composant par fichier (`react/no-multi-comp`), un dossier par composant avec son test et son `index.ts`.
- `components/` est présentationnel : props en entrée, callbacks en sortie, n'importe ni `api.ts`, ni `hooks/`, ni le store. Seules les `pages/` branchent les données.
- Une feature n'importe jamais une autre feature. Ce qui sert à plusieurs features vit dans `shared/`.
- `shared/` n'importe jamais `features/` ni `app/`.
- `max-lines: 300`, `max-lines-per-function: 50`.

**Manifeste** : `app/registry.ts` liste les manifestes ; le routeur et la navigation latérale sont construits à partir de cette liste. Ajouter une feature = un dossier + une ligne.

```ts
// frontend/src/shared/lib/feature.ts
export type NavSection =
  | "home" | "learn" | "study" | "skills" | "career" | "applications" | "memory" | "settings";

export interface NavEntry { section: NavSection; labelKey: MessageKey; path: string; order: number }

export interface FeatureManifest {
  id: string;
  routes: RouteObject[];               // react-router
  nav?: NavEntry[];                    // plusieurs écrans par section possibles (SPEC 15.1)
}
```

**Composants de session partagés** : l'écran Conseil sert aussi au Comité (F19) et le tableau sert au Tuteur (F14). Ces composants vivent donc dans `shared/session-ui/` (`AgentBubble`, `DebateFeed`, `InterruptCard`, `SessionStatusBar`, `SessionControls`, `CostBadge`, `Board`, `SourcesPanel`). Le rendu d'un événement passe par un registre `shared/realtime/eventRenderers.ts` (`type` d'événement → composant), extensible sans toucher au fil.

### 1.4 Ajouter une feature demain

1. Back : `app/features/<nom>/` (4 fichiers) + une ligne dans `FEATURE_ROUTERS` + une migration Alembic si nouvelles tables + graphe et agents dans leurs registres si besoin.
2. `cd backend && uv run python -m scripts.export_openapi` (D32) puis `pnpm --dir frontend gen:api` (vérifiés par les hooks `openapi-contract` et `api-types`).
3. Front : `src/features/<nom>/` + une ligne dans `app/registry.ts` + textes dans `fr.ts`.
4. Tests : service, routeur (dont isolation utilisateur), composants.

Aucun fichier existant d'une autre feature n'est modifié.

## 2. Arborescence cible

Celle de la spec (12.3, 12.4, 16.2), avec les ajouts marqués `+` (tous consignés dans `DECISIONS.md`). Le dossier courant devient la racine du dépôt `tremplin`.

```text
./
  frontend/   backend/   docker-compose.yml   docker-compose.dev.yml
  .env.example   README.md   SPEC.md   DECISIONS.md
  .pre-commit-config.yaml                      +
  contracts/openapi.json                       +  contrat front/back
  docs/superpowers/plans/                      +  plans
backend/
  app/
    main.py  config.py
    core/        errors.py, deps.py, security.py (chiffrement), logging.py (filtre de secrets)
    db/          engine.py, base.py, repository.py (+ UserScopedRepository), models/<groupe>.py
    providers/   llm/ search/ embeddings/ vector/ pdf/ storage/ web/   (+ registry.py et fake.py par type)
    agents/      prompts/ nodes/ graphs/ state/ tools/ runtime/  registry.py +
    features/    learning program lessons memory cv applications gap quiz interview projects
                 radar replan study skills kit brief capture committee settings auth
                 + sessions (API 14.1)  + postings (offres, doublons)  + health  + costs
    realtime/    websocket.py, replay.py
    scheduler/   registry.py +, un fichier par tâche
    templates/   lesson, program, report, cv
  scripts/       check_file_length.py, export_openapi.py +
  infra/searxng/settings.yml
  tests/         miroir de app/
frontend/src/
  main.tsx
  app/           router.tsx, registry.ts +, layout/ (Sidebar, Topbar, CommandCapture host), providers.tsx
  shared/
    api/         client.ts, schema.d.ts (généré)
    realtime/    useSessionStream.ts, sessionStore.ts, eventRenderers.ts
    session-ui/  + composants de session réutilisés par Conseil, Comité, Tuteur
    ui/          composants shadcn + états vide / chargement / erreur
    i18n/        fr.ts, t.ts
    lib/         feature.ts, format.ts
  features/      home learning program lessons study quiz memory skills cv applications
                 kit committee interview radar projects capture settings auth
                 + gap  + replan  (mêmes noms que le back) ; home = brief côté back
```

## 3. Contrats transverses

Fixés dans les phases 0 et 1, utilisés partout ensuite. Les signatures exactes sont dans les plans détaillés ; ici, la forme.

| Contrat | Où | Forme |
| --- | --- | --- |
| Niveau de modèle | `app/providers/llm/base.py` | `Tier = Literal["rapide", "standard", "fort", "vision"]` |
| Fournisseur LLM | `app/providers/llm/base.py` | `LlmProvider` : `name`, `build(model, api_key, base_url) -> BaseChatModel`, `list_models(api_key)`, `test_key(api_key)` |
| Fabrique | `app/providers/llm/factory.py` | `LlmFactory.get_chat_model(user_id, tier, agent=None) -> BaseChatModel` |
| Santé | `app/features/health/` | `HealthCheck` : `name`, `async check() -> HealthStatus(ok, detail)` |
| Repository | `app/db/repository.py` | `UserScopedRepository[Model]` : `get`, `list`, `add`, `update`, `delete`, toujours filtrés par `user_id` |
| Agent | `app/agents/registry.py` | `AgentSpec(name, display_name, tier, color)` ; prompt `prompts/<name>.md` |
| Graphe | `app/agents/graphs/registry.py` | `GraphSpec(name, input_model, build)` |
| Événement | `app/agents/runtime/events.py` | enveloppe `id, session_id, seq, ts, type, agent, payload` (9.5) |
| Session | `app/agents/runtime/runner.py` | `SessionRunner.start / resume / post_message / pause / cancel / recover` |
| Manifeste front | `frontend/src/shared/lib/feature.ts` | `FeatureManifest` (1.3) |
| Flux front | `frontend/src/shared/realtime/useSessionStream.ts` | `useSessionStream(sessionId) -> { events, status, pendingInterrupt }` |

## 4. Points de la spec à trancher (→ `DECISIONS.md` à la tâche 0.1)

| # | Point | Décision proposée |
| --- | --- | --- |
| D1 | `POST /postings`, `/sessions`, `/health`, `/costs` n'ont pas de dossier feature dans 12.3 | Ajouter `features/postings`, `features/sessions`, `features/health`, `features/costs` |
| D2 | Front `home` vs back `brief`, et front sans `gap` ni `replan` alors que les noms doivent être identiques | Front : ajouter `gap/` et `replan/`. Garder `home` (c'est un écran d'accueil), qui consomme l'API `brief` ; exception notée |
| D3 | Statuts de session (`running`, `waiting_user`, `completed`, `failed`) sans état pour Pause et Annuler | Ajouter `paused` et `cancelled` |
| D4 | Messages de l'utilisatrice pendant un débat : aucun type d'événement ni table | Nouveau type d'événement `user.message`, enregistré dans `session_events` ; les nœuds lisent les messages non traités au début de chaque tour |
| D5 | Index « dès la première migration » sur des tables créées plus tard | Chaque index est créé dans la migration de la phase qui crée sa table |
| D6 | Niveau de maîtrise stocké à deux endroits (`user_skills` et éléments `acquis` en mémoire) | `user_skills` fait foi ; l'élément `acquis` en est le reflet indexé, resynchronisé à chaque changement de niveau |
| D7 | Le Stratège crée le référentiel de compétences en phase 4, la carte F15 arrive en phase 5 | Tables `skills`, `skill_edges`, `user_skills` créées en phase 4, interface en phase 5 |
| D8 | Clé dans `.env` et clé saisie dans l'interface | La clé saisie dans l'interface est prioritaire ; `.env` sert de repli |
| D9 | Composants de débat utilisés par 3 features | Placés dans `shared/session-ui/` |
| D10 | Contrat front/back | `contracts/openapi.json` versionné, vérifié en CI |
| D11 | Router front | React Router (mode data), routes déclarées par les manifestes |
| D12 | Le schéma d'architecture de la section 12 est absent du document (« embedded content ») | Le texte de 12 et 16.1 suffit ; rien à reconstituer |
| D13 | `infra/searxng/settings.yml` dans `backend/` (16.2) | Respecté tel quel |
| D14 | Champ `type` de la charge d'interruption (9.4) en collision avec le `type` de l'enveloppe d'événement | La charge porte `kind` à la place |
| D15 | Reprise après Pause | `POST /sessions/{id}/resume` avec `interrupt_id: null` |
| D16 | Sorties structurées | JSON validé par Pydantic (2 nouveaux essais), sans `with_structured_output`, pour un comportement identique sur les 3 fournisseurs |
| D17 | Page de démonstration de la phase 1 | Route `/demo` conservée hors navigation |
| D18 | Reprise des sessions au démarrage | `list_sessions_to_recover` est la seule lecture sans filtre `user_id`, réservée au démarrage du back |

## 5. Feuille de route

Les phases suivent 18.1. Chaque phase : plan détaillé écrit juste avant (sauf 0 et 1, déjà écrits), tests, contrôle de fin, commit et tag `phase-N`. Les plans des phases 2 à 9 sont écrits à partir du code réel des phases précédentes et de la documentation vérifiée au moment de coder (18.2).

### Phase 0 — Socle · plan : `2026-11-11-01-phase-0-socle.md`

Dépôt, qualité, Docker Compose (7 services), SQLite + Alembic, utilisateur local, chiffrement, réglages, clés API, fabrique LLM (Anthropic, OpenAI, GLM, faux), santé des services. Front : coquille, navigation construite par manifestes, écran Réglages > Modèles et clés.
**Terminée quand** `docker compose up` donne `/api/v1/health` au vert et le test de clé réussit depuis les Réglages.

### Phase 1 — Moteur d'agents · plan : `2026-11-11-02-phase-1-moteur-agents.md`

Registres d'agents et de graphes, chargeur de prompts, checkpointer SQLite asynchrone, bus d'événements persisté, runner (lancement, interruptions, reprise, messages, pause, annulation, reprise au démarrage), journal `llm_calls` et coûts, plafond de tokens, WebSocket avec rejeu, graphe de démonstration à 2 agents. Front : `useSessionStream`, store de session, `shared/session-ui/`, page de démonstration.
**Terminée quand** le débat de démonstration s'affiche en direct, s'arrête sur une question et reprend après un redémarrage du back.

### Phase 2 — Mémoire (F3) · plan : `2026-11-11-03-phase-2-memoire.md`

- Reliquat de la phase 1 (ouvre la phase) : `fr.ts` découpé par zone avec agrégateur et `sessions.*` fusionné dans `session.*` ; statut final et événement final atomiques (D52 §2) ; `flush` par session (N5) ; relecture REST en attente (N2) ; tests manquants de course et de reconnexion.
- Back : fournisseurs `embeddings/ollama`, `vector/qdrant` derrière `MemoryRepository`, `storage/local`, `pdf/extract` ; tables `documents`, `memory_items`, `memory_chunks`, `memory_writes` ; chaîne d'ingestion (PDF, DOCX, Markdown, texte, URL, YouTube, texte collé ; fragments ~500 tokens, recouvrement 60 ; hash anti doublon ; statuts) ; outils `memory_search`, `memory_write`, `memory_get_skills` ; boîte « À confirmer » pour les `decision` ; agent Archiviste (« déjà appris » → acquis `declare`) ; carte 2D par PCA ; réindexation ; export JSON ; endpoints `/documents`, `/memory/*` (plus `POST /memory/items/{id}/merge` et `POST /documents/{id}/learned`, hors tableau 14.2) ; lecteur web minimal avancé de la phase 3 (`providers/web` : garde SSRF, 15 s, 20 Mo, trafilatura, transcriptions YouTube) ; parcours `learned_document` (17e graphe) pour l'Archiviste.
- Front `memory/` : `MemoryTable`, `MemoryItemDrawer`, `SemanticSearch`, `VectorMap`, `SearchBench`, `MemoryStats`, `DocumentUpload`, `PendingDecisions`.
- **Terminée quand** un PDF importé se retrouve par recherche et une écriture d'agent s'affiche avec son auteur (et sa raison).

### Phase 3 — Recherche web · plan : `2026-11-11-04-phase-3-recherche-web.md`

- Reliquat de la phase 2 (ouvre la phase) : `SessionView.subject_type/subject_id` et reprise du suivi de l'Archiviste après rechargement (« Déjà appris » idempotent) ; extraction PDF en sous-processus avec délai et plafond mémoire (DoS de D63) ; titre d'un doublon encadré dans `memory_tools.py` ; vecteurs orphelins d'un document supprimé pendant son import (M2).
- Back : `search/` (`SearchProvider`, SearXNG, Brave plafonné à 900 requêtes par mois civil, clé Brave dans l'écran des clés, ordre de repli) ; `web/` étendu sans réécrire `SafeHttpFetcher` ni `TrafilaturaWebReader` (D63) : débit 1 requête/s/domaine (3 s pour l'API arXiv), GitHub (README), arXiv (Atom + PDF), repli Gotenberg (URL déjà validée → PDF → texte, liste de refus Chromium), 15 s par page repli compris ; feature `research` : tables `web_cache` (7 jours, 24 h pour une page illisible), `sources`, `web_queries`, `search_usage`, retrait nom/email/téléphone des requêtes, domaines privilégiés et exclus (liste de départ), plafonds 12 requêtes / 30 pages par session réglables, statut `ok`/`unreadable`, `GET /research/usage`, `GET /research/sources` ; port `WebGateway` et `web_tools` ; Éclaireur (`scout`) qui note sur 100 (seuil 60) dans un parcours de banc d'essai `web_research` (18e graphe, réutilisé par le Conseil en phase 4) ; `source.found` complété (statut, verdict, raison).
- Front : `SourcesPanel` et `sourcesFromEvents` dans `shared/session-ui/` ; Réglages > « Recherche web » (langues, domaines, ordre, plafonds, compteur Brave) ; feature `research/` (« Essai de recherche ») ; reprise du suivi de l'Archiviste dans `memory/`.
- **Terminée quand** une requête renvoie des sources notées et lues, et une page illisible est signalée.

### Phase 4 — Conseil et programme (F1, F2) · plan : `2026-11-12-05-phase-4-conseil-programme.md`

- Reliquat de la phase 3 (ouvre la phase) : logger `httpx2` en WARNING ; `judge` qui ne rappelle pas le LLM au rejeu, délai de notation par page ; erreur de base au rendu d'une réservation Brave qui n'empêche plus le repli.
- Moteur : ports regroupés dans `AgentPorts` (un port de plus = un champ + une ligne dans `bootstrap`) ; `SessionLauncher` pour lancer une session depuis un port ou une tâche planifiée ; commandes du débat portées par `user.message` (`command`) ; interruptions à champs (`fields`) ; `board.update` avec `board_id`/`kind`/`title`.
- Agents : Modérateur, Stratège, Praticien, Éclaireur (réutilisé nœud pour nœud, plus les praticiens), Sceptique, Scribe, Rédacteur, Vérificateur. Graphes `learning_council`, `program_builder`, `lesson_factory` ; ports `CouncilStore`, `ProgramStore`, `LessonStore`.
- Back : tables `goals`, `proposals`, `boards`, `programs`, `weeks`, `modules`, `tasks`, `lessons`, `resources`, `plan_versions`, `skills`, `skill_edges`, `user_skills` ; features `learning`, `program`, `lessons`, `skills` (sans routeur) ; règles du débat (9.3) ; 3 points d'arrêt ; règles de planification (85 %, disponibilité, acquis sautés, pratique + quiz chaque semaine) ; leçons Markdown 1 200–2 500 mots, structure fixe ; PDF A4 via Gotenberg `convert/html` (gabarits dans `app/templates/`, contenu nettoyé, Mermaid en SVG par nos scripts figés) ; ressources 3–6 par module ; export PDF et `.ics` ; paquet `app/scheduler/` (registre `JOBS`) et tâche « leçons à J-7 » ; routes hors 14.2 : `GET /goals/{id}`, `GET /goals/{id}/boards`, `POST /boards/{id}/edits`, `GET /programs`, `PATCH /programs/{id}`, `GET /programs/{id}/lessons`, `GET /resources/{id}/file`.
- Front : `Board` Excalidraw (apparition élément par élément 150–300 ms, repli SVG Mermaid) et `MermaidSvg` dans `shared/session-ui/` (réutilisés par le Tuteur) ; `learning/` (Objectifs, page Conseil, `ProposalCards`, commandes du débat), `program/` (`WeekCalendar` glisser déposer, `TaskList`, `PlanDiff`, `ProgressOverview`), `lessons/` (`LessonReader`, Bibliothèque) ; Playwright installé.
- **Terminée quand** un objectif mène à un programme validé avec les leçons PDF de 2 semaines. Parcours de bout en bout n°1 (conseil complet) écrit ici.

### Phase 5 — Étude (F9, F13, F14, F15, F18)

- Agents : Examinateur, Tuteur. Graphes `quiz`, `study_session`, `replan`, `capture`.
- Back : `quizzes`, `quiz_questions`, `quiz_attempts`, `flashcards` (intervalles 1, 3, 7, 16, 35 ; erreur → 1 jour ; file plafonnée à 15 min), `study_sessions`, `skill_snapshots`, `journal_entries` ; passage `valide` à 80 % ; rétrogradation après 2 échecs ; replanification (bilan dimanche 18 h, 30 % de retard deux semaines, versions de plan) ; capture rapide.
- Front : `quiz/`, `study/` (minuteur 50/10, 3 modes, « Je bloque » à 3 indices), `skills/` (React Flow + elkjs, radar, progression, comparaison), `replan/`, `capture/` (`CommandCapture` Ctrl/Cmd K, journal).
- **Terminée quand** une session guidée complète met à jour la carte et le planning.

### Phase 6 — CV (F4, F8)

- Agents : Archiviste (profil maître), Maquettiste, Lecteur ATS, Recruteur, Analyste. Graphes `cv_capture`, `cv_review`, `gap_analysis`.
- Back : `master_profile` versionné, `cv_templates`, `job_postings`, `companies`, `cv_reviews`, `cv_modifications`, `cv_versions` ; extraction PDF avec positions et images de pages ; template HTML/CSS, comparaison et score de ressemblance, 3 passes max, polices ; feature `postings` (normalisation du lien, lecture ou texte collé, refus d'analyser une offre devinée, contrôle doublon 3 niveaux) ; nœud validateur contre le profil maître ; indicateurs avant/après ; nom de fichier `CV_<Nom>_<Entreprise>_<Poste>.pdf` ; nombre de pages conservé ; score de match (2/1, 1/0,6/0,3/0) ; base ATS datée.
- Front : `cv/` (`MasterProfileForm`, `TemplateCompare`, `ReviewDiff`, `CoverageGauge`, `PdfPreview`), `gap/` (tableau d'écarts, top 10 des manques).
- **Terminée quand** une offre collée donne un CV ciblé en PDF dans le design d'origine. Parcours de bout en bout n°2 (revue de CV complète).

### Phase 7 — Candidatures (F5, F10, F16, F19)

- Agents : Assistant de suivi, Intervieweur ; personas Manager et Futur collègue (variantes de prompt du Recruteur). Graphes `application_kit`, `interview`, `hiring_committee`.
- Back : `applications`, `application_events`, `contacts`, `reminders`, `kit_items`, `interviews`, `committee_runs` ; 8 statuts ; création auto, manuelle, en langage naturel ; relances 7/14/21 jours et après entretien ; alerte doublon et information 30 jours ; kit de 7 pièces en parallèle, archive zip, guide de style, jamais de prétentions salariales ; indicateurs.
- Front : `applications/` (Kanban, tableau, tiroir de fiche, `ReminderCard`, `DuplicateAlert`), `kit/`, `interview/`, `committee/` (réutilise `shared/session-ui`).
- **Terminée quand** le cycle complet d'une candidature fonctionne, alerte doublon comprise. Parcours de bout en bout n°3.

### Phase 8 — Quotidien (F11, F12, F17)

- Agents : Praticien (évaluation), Éclaireur et Analyste (radar). Graphes `project_review`, `market_radar`, `daily_brief`.
- Back : `projects`, `radar_runs`, `briefs` ; registre des tâches planifiées complet (brief 7 h, radar hebdomadaire, bilan, relances, leçons J-7, rafraîchissement ATS 30 jours) ; table `jobs` ; fil d'activité.
- Front : `projects/` (Portfolio), `radar/`, `home/` (brief, 4 actions rapides, `ActivityFeed`, notifications de fond).
- **Terminée quand** le brief du jour se génère seul et reprend toutes les rubriques.

### Phase 9 — Finitions (F6 avancé, F7)

- Back : Google OAuth (code + PKCE, `openid email profile`, cookie 30 jours, `ALLOWED_EMAILS`, reprise des données `local`) ; test d'isolation par routeur ; export et suppression totale ; surcharge du modèle par agent ; écran coûts et journal des agents.
- Front : `auth/`, premier lancement en 5 étapes, `settings/` (coûts, journal, disponibilité, style, données), README.
- **Terminée quand** les 3 parcours Playwright passent et tous les critères transverses de 18.3 sont vérifiés.

### Phases 10 à 20 — fonctionnalités ajoutées (demande du 2026-11-14)

Hors de la spec d'origine : une fonctionnalité par phase, dans l'ordre d'importance. Chaque phase commence par une séance de conception (brainstorming) avec l'utilisatrice, puis son propre plan, comme les phases 2 à 9.

| Phase | Fonctionnalité | Idée | S'appuie sur |
| --- | --- | --- | --- |
| 10 | IDE avec professeur en temps réel | Éditeur (Monaco) et terminal (xterm) dans le navigateur ; Python et JS dans un conteneur isolé par utilisateur (`uv`, `npm`, réseau limité aux dépôts de paquets, limites CPU / mémoire / temps) ; agent « professeur » en mode guide (explique les erreurs, indices gradués, ne touche pas au code) ou binôme (annotations en marge, corrections proposées à accepter) ; intervient à l'exécution, à l'erreur ou sur demande. **Plus un serveur MCP** (demande du 2026-11-16) : Claude Code ou Codex pilotent les features de Tremplin (cours, offres, contacts, candidatures…) à la place des agents internes, avec des pouvoirs limités (voir plus bas) | Phases 0 à 5 (Tuteur, carte, fiches, journal) ; phase 9 (connexion, isolation) pour le MCP |
| 11 | Extension navigateur « Capturer l'offre » | Un clic sur une page d'offre (LinkedIn, Indeed, Welcome to the Jungle…) envoie son texte à Tremplin | Phase 6 (offres) |
| 12 | Mode « Explique-moi » (Feynman) | January enseigne un concept à un agent élève naïf qui repère les trous ; bilan de maîtrise | Phase 5 (Tuteur, carte) |
| 13 | Alertes d'offres compatibles | Le radar hebdomadaire cherche des offres, calcule le score de match et l'écart, envoie les 5 meilleures | Phases 6 et 8 |
| 14 | Liaison GitHub | Dépôts et commits lus comme preuves de compétences ; l'évaluation de projets relit un vrai dépôt | Phases 5 et 8 |
| 15 | Profil LinkedIn optimisé | Titre, résumé, compétences proposés depuis le profil maître et les offres visées, passés au validateur d'honnêteté | Phase 6 (profil, validateur) |
| 16 | Entraînement « system design » | Sujet d'architecture sur le tableau Excalidraw, critique par un évaluateur comme en entretien | Phases 3 et 7 |
| 17 | Mode vocal | Oral d'explication et d'entretien : transcription, retours sur la clarté et la structure | Phases 5 et 7 |
| 18 | Google Agenda | Blocs d'étude et entretiens dans l'agenda ; replanification sur les vrais créneaux libres | Phases 4, 5 et 7 |
| 19 | Application mobile (PWA) | Révisions et brief sur le téléphone, notifications, fiches hors ligne | Phases 5 et 8 |
| 20 | Site portfolio généré | Site personnel statique tiré du profil maître et des projets, déployable en un clic | Phases 6 et 8 |

#### Phase 10 — coût des appels au modèle (exigence du 2026-11-14)

Le professeur doit rester peu coûteux en appels API. Ces règles sont fixées dès la conception :

- **Déclencheurs :** le professeur réagit seulement à l'exécution, à une erreur, à une question ou, en option, après 30 s d'arrêt sur une même ligne. Jamais à chaque frappe.
- **Contexte envoyé :** l'énoncé de l'exercice, le fichier en cours (ou seulement la partie modifiée), la sortie d'erreur tronquée et les derniers échanges. Jamais tout le projet ni tout l'historique.
- **Mise en cache :** l'énoncé et les consignes du professeur forment un début de prompt fixe, mis en cache entre les appels d'une séance.
- **Deux niveaux de modèle :** un modèle léger pour les indices et les annotations en marge, le modèle fort seulement pour les vraies explications et les corrections proposées. Les deux sont choisis dans le registre `LLM_PROVIDERS`.
- **Plafond par séance :** un plafond de tokens par séance et un autre par jour, réglables, avec la consommation affichée à l'utilisateur. Une fois le plafond atteint, le professeur passe en mode « sur demande ».
- **Anti-répétition :** une même erreur au même endroit ne déclenche pas une nouvelle explication. Le professeur renvoie à la précédente.
- **Mesure :** chaque appel journalise uniquement son identifiant de séance, le modèle et les tokens. La phase se termine par une séance réelle mesurée, comparée à la cible d'environ 150 000 tokens en entrée et 15 000 en sortie par heure.

#### Phase 10 — serveur MCP, sécurité maximale (exigence du 2026-11-16)

Un serveur MCP donne à Claude Code ou à Codex l'accès aux features de Tremplin (lire et modifier un cours, ajouter une offre, ajouter un contact à une candidature, cocher une tâche, lancer un graphe…). L'agent externe pense, l'application garde les données et les règles. **Il n'a jamais les pleins pouvoirs.** Règles fixées dès la conception :

- **Liste blanche explicite :** chaque feature déclare ses outils MCP dans son manifeste (registre, comme `FEATURE_ROUTERS`). Aucune route n'est exposée automatiquement à partir du contrat OpenAPI.
- **Deux sortes d'outils, toutes deux voulues (réponse du 2026-11-16) :** des outils simples (lecture, ajout, modification) où Claude fait le travail lui-même ; des outils qui lancent les graphes de l'application (revue de CV, kit, comité…), où les agents internes travaillent et Claude suit la session jusqu'au résultat.
- **Quatre niveaux d'outils :**
  1. lecture ;
  2. écriture réversible (ajout, modification, avec historique et annulation) ;
  3. actions qui ne s'annulent pas : suppression, envoi d'un message, écriture au profil maître. Elles sont exposées, mais chaque appel crée seulement une **demande « À confirmer »** dans l'application. Rien ne se fait avant que January la confirme ; elle peut la refuser, et la demande expire sans réponse ;
  4. jamais exposé au MCP : clés d'API et secrets, connexion et `ALLOWED_EMAILS`, réglages des modèles, jeton MCP lui-même.
- **Profil maître :** un outil MCP crée un brouillon, jamais une entrée validée. Le brouillon est contrôlé **dans l'application par ses agents internes** (validateur d'honnêteté contre le profil, comme pour les brouillons des projets), puis January le confirme (niveau 3).
- **Jeton propre au MCP :** créé, limité à certaines features (lecture seule par défaut), avec une date d'expiration, et révocable par January dans les réglages. Il est stocké haché et n'est jamais journalisé. Il est distinct du cookie de session. Un bouton coupe tout l'accès MCP.
- **Mêmes règles que l'interface :** chaque outil appelle le service de la feature (validation, contrôle d'honnêteté, isolation par utilisateur). Aucun SQL brut, aucun accès aux fichiers ni au shell, aucune clé ni secret dans une réponse.
- **Limites :** nombre d'appels et d'écritures par minute et par jour, avec une 429 lisible au-delà.
- **Journal :** chaque appel MCP est journalisé (outil, identifiants, code de résultat, durée, jamais le contenu) et visible dans l'écran « journal des agents ».
- **Données non fiables :** les textes venus du web (offres, pages lues) sont renvoyés marqués comme données, jamais comme consignes (injection de prompt).
- **Réseau :** d'abord en local seulement (127.0.0.1). L'accès à distance viendra plus tard, avec OAuth.
- **Fin de phase :** des tests d'abus (outil hors liste, jeton expiré ou révoqué, feature non autorisée, tentative de validation du profil, injection dans une offre) et un essai réel avec Claude Code sur une pile jetable.

#### Phase 11 — report de la 10b (demande du 2026-11-18)

- **Recette longue des agents joués par MCP :** un programme complet joué par Claude Code (ou
  Codex) sur une pile jetable, Conseil, Constructeur, puis toutes les leçons de tous les modules
  avec le Vérificateur. La 10b ne recette qu'un programme court (2 à 3 modules, leçons d'un ou deux
  modules). Accord de January avant d'engager le quota : compter plusieurs heures et plus de
  1,5 M de jetons du client.
- **Menu par bouton de lancement (D218) :** un petit menu « Qui fait tourner les agents » à côté
  de chaque bouton qui lance un parcours, en plus du menu global, pour choisir au cas par cas.
- **Appairage du relais en un clic :** un bouton dans Réglages donne au relais son jeton MCP,
  sans copier-coller ni `relay.json`. Le jeton couvre toutes les features jouables, sinon le
  relais met la session de côté (`play_forbidden`) : l'interface doit le signaler.
- **Échec de planification renvoyé au Stratège :** une tâche plus longue que la plus longue
  journée ne fait plus échouer `program_builder` (`planning_impossible`, message trompeur sur
  le budget hebdomadaire) ; le Stratège reçoit le motif et refait son brouillon.
- **Replanification « impossible » :** quand le budget hebdomadaire est plein, proposer une
  semaine de plus au lieu de rendre seulement « impossible ».
- **Écart d'une offre :** pouvoir cocher aussi les lignes « Hors périmètre » et choisir le
  programme qui reçoit l'ajout (aujourd'hui : le programme validé le plus récent).
- **Qualité du CV généré pour une offre (retour de January du 2026-11-18, revue jouée par
  Claude Code) :**
  - Le lien du site personnel (`laurent-nizzoli.com`) disparaît du CV généré : tous les liens
    du profil doivent passer dans l'en-tête.
  - Les compétences tombent en une seule colonne, la moitié droite reste vide : les répartir sur
    2 ou 3 colonnes selon la place du modèle.
  - Les expériences perdent leurs informations utiles et l'IA n'apparaît plus : la composition
    raccourcit trop. Elle doit garder les faits forts (IA, agents, résultats chiffrés) et ne
    couper que le moins pertinent pour l'offre.
  - Revoir le rendu d'ensemble (hiérarchie, espacements) face au CV d'origine.
  - Avant de corriger : refaire l'essai avec un CV source à jour, pour séparer ce qui vient de
    la source de ce qui vient de la composition.
- **Tests repris :** l'en-tête `X-Tremplin-Run`, le menu, le relais (`node:test`), le sélecteur
  d'offre des modèles de CV, « Je les maîtrise déjà » (D220 : module de validation, quiz sans
  leçon), puis un essai de bout en bout avec Codex.

#### Phase 11 — professeur dans la leçon, session training, cerveau (demande du 2026-11-20)

Cadrage : `2026-11-20-11-chats-et-cerveau-cadrage.md`. Un seul moteur de conversation (recherche
dans la mémoire, réponse en flux, sources citées, coût plafonné) ouvert à trois endroits :

- **« Demander au professeur » :** sélectionner un passage d'une leçon fait apparaître un bouton ;
  un panneau de chat s'ouvre à droite par-dessus la leçon, sans changer de page ; le fil reste
  rattaché à la leçon.
- **Session training (Étudier) :** séance libre sans choix de leçon ; le Tuteur demande quoi
  travailler (une ou plusieurs leçons, n'importe quel sujet des programmes), conduit selon le
  mode, et le mode se change pendant la séance.
- **Cerveau :** plusieurs dossiers (aujourd'hui des coffres Obsidian) synchronisés
  automatiquement par un synchroniseur intégré au relais (ajouts, modifications et suppressions
  suivis) ; chat sur les documents et les programmes en cours, avec sources.
- **MCP :** les trois portes exposées ; ajouter ou retirer un dossier surveillé n'est jamais
  exposé (niveau 4).
- Qui répond : le modèle de Tremplin par défaut, ou Claude Code / Codex par le relais (menu D218).

#### Phase 11 — qualité des leçons (retour de January du 2026-11-20)

Constat sur le programme LangChain (50 leçons prêtes) : le fond est juste et à jour (LangChain et
LangGraph 1.x, un fil conducteur), mais les leçons ne sont « pas assez structurées » ni assez
profondes. 48 sur 50 ont été écrites par Codex avec `lessons_write_lesson`, qui n'impose aucun
plan : une seule partie puis « Ressources », sans le plan en 11 parties du Rédacteur, sans
Vérificateur. Le code est écrit en français (`Etat`, `normaliser`), « ça pique ».

- **Une seule norme de leçon** pour le Rédacteur de la fabrique **et** pour l'écriture directe
  par MCP : même plan, contrôlé à l'écriture (`lessons_write_lesson` refuse une leçon hors norme
  avec les raisons, comme le Vérificateur), et rendue aux clients MCP (brief, `docs/mcp`).
- **Inspirée des skills `teach` et `writing-beats` de Matt Pocock :**
  - **chaque notion est définie avant d'être utilisée**, même une notion de base (« LLM »,
    « token », « embedding ») : January veut savoir de quoi on parle même quand elle le sait
    déjà. Un glossaire par programme, repris tel quel d'une leçon à l'autre ;
  - l'explication avance **par étapes courtes**, une idée par étape, chacune ne s'appuyant que
    sur des notions déjà posées ;
  - **plus profond** : comment ça marche dessous et pourquoi, pas seulement comment s'en servir ;
  - d'abord le savoir, puis la pratique : questions de rappel au fil de la leçon, rappels des
    leçons précédentes, exercices qui mêlent les notions ;
  - chaque leçon reliée à l'objectif du programme, avec **une source principale** à lire ou
    regarder, et une **fiche de référence** courte (l'essentiel à relire plus tard) ;
  - quiz : réponses de même longueur, bonne réponse placée au hasard.
- **Code en anglais** : identifiants, commentaires et textes dans le code en anglais ; le texte
  de la leçon reste en français.
- **Un programme se lit comme un livre, de zéro à expert (précision de January, 20/11) :**
  « comprendre deeply chaque leçon, chaque programme, comme dans un livre où tout est expliqué,
  pas un truc ciblé comme LoRA ». Quel que soit le domaine, le programme part des fondations du
  domaine, et chaque leçon est un chapitre qui s'appuie sur les précédents jusqu'au niveau
  expert. Rien n'est supposé connu sans avoir été posé, même ce que January sait déjà (« Je les
  maîtrise déjà », D220, reste le moyen de passer un chapitre par un quiz).
- **Réécriture de tous les cours existants après la phase 43**, selon cette norme (D227).
- **Les 4 programmes existants sont reconstruits comme des livres (décision de January, 20/11,
  option A) :** le Conseil et le Constructeur repartent de chaque objectif avec la règle « de
  zéro à expert » (chapitres de fondations en tête, progression jusqu'au niveau expert), et
  toutes les leçons sont écrites selon la nouvelle norme. Ce qui est acquis (compétences
  validées, quiz réussis) est repris quand un chapitre correspond. Les programmes s'allongent :
  à budget hebdomadaire égal, le planning s'étend sur plus de semaines. Écarté : garder les plans
  actuels et seulement réécrire les leçons (fondations éparpillées, pas un livre).

**Garanties de qualité « enseignant expert » (demande de January du 21/11) :** la qualité ne doit
pas dépendre du modèle qui écrit (agents de Tremplin, Codex, Claude ou autre), mais de ce qui lui
est imposé et vérifié. Six exigences :

1. **Toujours la chaîne de la fabrique, jamais l'écriture brute.** Une leçon passe par la
   recherche de sources (Éclaireur), le Rédacteur et le Vérificateur, que ces rôles soient tenus
   par les agents de Tremplin ou joués par Codex / Claude (`agents_play_*`, sans coût d'API pour
   January). `docs/mcp/AGENTS.md` et les instructions du serveur cessent de pousser vers
   `lessons_write_lesson` « pour économiser l'API » ; une leçon écrite directement n'est publiée
   qu'après le Vérificateur (statut « à vérifier » jusque-là).
2. **Une norme écrite une seule fois, servie à tous.** Un seul fichier décrit la leçon d'expert
   (plan du chapitre, notion définie avant usage, étapes courtes, profondeur « comment ça marche
   dessous et pourquoi », code en anglais, schéma, exemple travaillé, exercice et corrigé,
   questions de rappel, fiche de référence, source principale). Le Rédacteur l'inclut dans ses
   consignes et le brief MCP rend le même texte : personne n'écrit « à sa façon ».
3. **Contrôle automatique à l'écriture.** Le serveur refuse, avec les raisons, une leçon à la
   partie manquante, trop courte, sans schéma, ou dont le code a des identifiants en français. Une
   consigne est suivie la plupart du temps ; un contrôle l'est à tous les coups.
4. **Vérificateur exigeant, avec une grille notée.** En plus des sources, il vérifie que chaque
   notion utilisée a été posée avant (chapitre précédent ou glossaire), que l'explication va au
   fond (mécanisme et raison, pas seulement l'usage), que l'exemple et l'exercice éclairent la
   notion, et que la leçon enchaîne avec la précédente sans la répéter. Il rend une note par
   critère ; sous le seuil, la leçon est réécrite avec les raisons.
5. **Le programme est un sommaire de livre.** Le Constructeur produit une table des matières de
   zéro à expert. Chaque chapitre déclare les notions qu'il **requiert** et celles qu'il
   **introduit** (principe de `writing-beats`) ; aucune notion requise sans avoir été introduite
   plus tôt. Le glossaire du programme en découle. Le Rédacteur reçoit le glossaire, le résumé du
   chapitre précédent et le plan du suivant : il enchaîne au lieu de réintroduire.
6. **Un pilote avant la réécriture en masse.** Deux ou trois chapitres du programme LangChain sont
   réécrits selon la norme. À la clôture du projet, January relit le pilote, puis la norme et la
   grille sont ajustées avant de reconstruire les quatre programmes avec son accord sur le coût.

#### Phase 11 — relais (constat du 2026-11-20)

- **Quota MCP épuisé par l'attente :** le relais interroge Tremplin toutes les 10 s (≈ 360 appels
  par heure) avec le jeton « Claude Code », limité à 1000 appels par jour : il est bloqué dès le
  matin jusqu'à la remise à zéro, et le jeton avec lui. Jeton propre au relais (lié à
  l'appairage) dont l'interrogation ne compte pas dans la limite, ou interrogation plus espacée.
- **Lancement de Codex cassé :** `codex exec … --search` sort en code 2 avec codex 0.170
  (`--search` n'est accepté qu'avant `exec`) : `relay/tremplin-relay.mjs` ligne 86.

#### Phases ajoutées après la 11 (demande du 2026-11-21)

Retenues par January le 21/11 parmi les propositions de la séance (« tout sauf l'auto-génération
de CV » : le « chasseur de nuit », qui préparait CV et lettre pour chaque offre, est écarté ; les
offres arrivent dans la pile de lecture). **Chaque feature déclare ses outils MCP** (lecture,
écriture annulable, demandes « À confirmer »), comme le reste de Tremplin. Chacune commence par
une séance de conception, puis son plan.

**Nouvel ordre (décision de January du 21/11) :** la phase 11 est celle décrite plus haut
(reports de la 10b, chats et cerveau, qualité des leçons, relais) ; l'extension « Capturer
l'offre », phase 11 d'origine du tableau ci-dessus, devient la **phase 12** ; les features
ci-dessous sont les **phases 13 à 24**, puis les dix features de la section suivante sont les
**phases 25 à 34** ; les phases 12 à 20 du tableau ci-dessus (« Explique-moi » à portfolio)
viennent ensuite, dans leur ordre, à partir de la **phase 35**.

**Extension Chrome mise de côté (décision de January du 21/11) :** on oublie l'extension
« Capturer l'offre » pour le moment. La phase 12 ne se fait pas : après la phase 11, on passe
directement à la phase 13 (pile de lecture), qui apporte déjà des offres chaque matin.
L'extension garde son numéro et reviendra seulement si January la redemande.

| Ordre | Fonctionnalité | Idée | S'appuie sur |
| --- | --- | --- | --- |
| 13 | Pile de lecture | Chaque matin, des agents déposent ce qu'ils ont trouvé : offres d'emploi, articles, papiers, nouveautés des bibliothèques étudiées, tout sujet surveillé. Un lecteur : liste des nouveautés (non-lues, filtres), mode lecture propre (résumé, texte, « pourquoi c'est pour toi »), et pour chaque élément : lu, garder en mémoire, en faire des fiches, ajouter à un programme, créer une candidature. Sources réglables (sujets, sites, RSS) ; le brief annonce le nombre de nouveautés | Lecture web (research), radar, mémoire, brief |
| 14 | IDE de projets Python | Comme VS Code : arborescence (créer, renommer, supprimer des fichiers), onglets, vrai terminal (xterm) sur le bac à sable, **notebooks Jupyter**, professeur en temps réel qui voit tout le projet. Petits projets Python d'entraînement, quel que soit le sujet (pas seulement LangChain). Pour appeler un LLM depuis le bac sans réseau ni secret : une passerelle modèle de Tremplin, compatible OpenAI, qui ajoute la clé côté serveur avec un plafond par jour, ou le modèle local Ollama | Phase 10 (IDE, bac à sable, professeur) |
| 15 | Simulateur d'astreinte | Un service réaliste tourne dans le bac à sable et casse à un moment imprévu (latence, réponses inventées, quota, file bloquée) ; January reçoit l'alerte, enquête dans les journaux, corrige, écrit le rapport d'incident ; un agent note comme un responsable d'exploitation | 14, carte des compétences |
| 16 | Ton futur toi | Projection du rythme d'étude réel, de la carte des compétences et des offres visées : « crédible pour 60 % des offres AI Engineer le 12 mars ; le 3 février à 8 h par semaine », et les chapitres qui débloquent le plus d'offres | Écart, radar, replanification |
| 17 | Ton livre | Chaque programme compilé en livre PDF et EPUB (couverture, sommaire, glossaire, index), avec notes Obsidian en marge, erreurs fréquentes en encadré, code des exercices en annexe ; mis à jour à chaque chapitre | Phase 11 (programmes-livres, cerveau), Gotenberg |
| 18 | Podcast du matin | Épisode de 10 à 15 min à deux voix sur le chapitre du jour, tiré des leçons, des notes et des erreurs de la veille, suivi d'un quiz de trois questions | Brief, leçons, quiz ; synthèse vocale à ajouter |
| 19 | Contributrice open source | De vraies issues faciles dans les projets étudiés, choisies pour le chapitre en cours ; préparation (code concerné, notions), suivi jusqu'à la pull request ; une contribution acceptée devient une preuve et une ligne de CV | Programmes, carte, CV ; liaison GitHub |
| 20 | Classe virtuelle | Trois camarades IA de niveaux différents suivent le même programme : January explique au plus faible, débat avec le plus fort, questions entre pairs | Tuteur, programmes |
| 21 | Négociation de salaire | Recruteur au budget réel (salaires du radar) qui joue ses contraintes ; bilan : ce qui a été laissé sur la table et pourquoi | Radar, entretien (phase 7) |
| 22 | Chasse aux erreurs | Sur demande, une leçon contient deux erreurs subtiles et plausibles à trouver et expliquer : lecture critique face aux LLM qui inventent | Leçons, Vérificateur |
| 23 | Procès de ton code | Un procureur attaque la conception d'un projet, un avocat la défend, January juge : les compromis d'architecture par la plaidoirie | 14, agents de débat (comité) |
| 24 | Révision par messagerie | Une question de révision par WhatsApp ou Telegram au moment idéal pour la mémoire, par Nod (agent de January branché sur le MCP de Tremplin) | Fiches, MCP |

#### Dix features folles (demande du 2026-11-22)

Demandées par January « dans la P10 » ; la phase 10 étant en clôture (branche `phase-10b`), elles
sont rangées en **phases 25 à 34**. Mêmes règles : séance de conception, plan, outils MCP.

| Ordre | Fonctionnalité | Idée | S'appuie sur |
| --- | --- | --- | --- |
| 25 | Boss de fin de programme | Chaque programme se termine par un défi chronométré dans l'IDE : un vrai petit système à livrer, pendant qu'un agent « client » change les exigences en cours de route ; note détaillée et preuve de compétence | 14 (IDE), programmes, carte |
| 26 | Du papier au code | January donne un article de recherche (arXiv…) : Tremplin en tire un mini-cours de zéro à expert et un notebook qui reproduit le résultat principal à petite échelle | Fabrique de leçons, 14 (notebooks) |
| 27 | Leçons qui se mettent à jour seules | Tremplin suit les versions des bibliothèques étudiées ; quand une API change, il repère les leçons et les exemples devenus faux et propose la correction | 13 (nouveautés des bibliothèques), Vérificateur |
| 28 | Galaxie du savoir | La carte des compétences et la mémoire en 3D navigable : chaque notion est une étoile, ses liens des constellations, les trous brillent ; un clic ouvre le chapitre ou une séance training | Carte, mémoire, 11 (cerveau) |
| 29 | Entretien surprise | Sans prévenir, un recruteur fictif « appelle » (message ou voix, par Nod) avec trois questions techniques à chaud, comme un vrai premier entretien téléphonique ; bilan ensuite | Entretien (phase 7), 24 (messagerie) |
| 30 | Bourse des compétences | Chaque compétence a un « cours » tiré de la demande du marché (radar) ; un portefeuille montre lesquelles montent, lesquelles sont sous-évaluées, et ce qu'« investir » une heure d'étude rapporte | Radar, carte, 16 (futur toi) |
| 31 | Course contre ton fantôme | Refaire un exercice ou un quiz contre l'enregistrement de sa propre tentative passée, comme le fantôme d'un jeu de course : temps, erreurs, progrès visibles | IDE, quiz, journal |
| 32 | Pilote de concentration | Tremplin repère la fatigue (erreurs qui montent, réponses plus lentes) et ajuste la séance : pause, révision plus facile, ou fin conseillée avec un bilan | Étude, quiz, 11 (training) |
| 33 | Débat d'experts sur ta question | Une question posée est débattue par trois experts fictifs (chercheur, praticien, sceptique) ; January lit le débat et tranche, avec les sources de chacun | Agents de débat, 11 (moteur de conversation) |
| 34 | Liseuse augmentée | Dans la pile de lecture, chaque terme technique d'un article ou d'un papier s'explique au survol, d'après le glossaire et les chapitres de January ; un passage se transforme en fiche d'un geste | 13 (pile de lecture), glossaire (11) |

#### Liens entre les phases

Chaque phase branche ses liens par les registres existants (manifeste front, `AGENTS`, `GRAPHS`, ports, tâches planifiées), sans retoucher le code des autres phases. Quand une phase prépare un lien vers une phase qui n'existe pas encore, elle expose seulement le point d'accroche (événement, port ou champ) ; la phase suivante s'y branche.

- **Point d'accroche commun : les preuves de compétence.** Les phases 10, 12, 14 et 16 produisent des **preuves** rangées sur la carte des compétences (phase 5). Elles utilisent le même type de preuve, avec une source (`ide`, `feynman`, `github`, `system_design`) et le même plafond de niveau (`en_cours` par la pratique, `valide` seulement par un quiz ou une évaluation notée).
- **Point d'accroche commun : les erreurs fréquentes.** Les phases 10, 12, 16 et 17 transforment les erreurs repérées en **fiches de révision** (phase 5), par le même service de fiches.
- **Point d'accroche commun : le fil d'activité et le brief.** Toute phase qui produit un événement notable l'écrit dans le fil d'activité (phase 8). Le brief du matin le reprend : exercice IDE réussi, offre capturée, alerte, entretien à venir, bloc d'étude.

| Phase | Reçoit de | Donne à |
| --- | --- | --- |
| 10 IDE + professeur | Leçons et exercices (3, 5), compétences ciblées (5) | Preuves sur la carte (5) ; fiches des erreurs (5) ; journal et série (5) ; exercices de code de l'entretien (7) ; dépôt local envoyable vers GitHub (14) ; base du mode « Explique-moi » sur du code (12) |
| 11 Extension « Capturer l'offre » | Analyse d'offre et doublons (6), connexion (9) | Offre analysée → écart et revue de CV (6) ; candidature créée (7) ; source d'offres pour les alertes (13) |
| 12 Mode « Explique-moi » | Concepts des leçons (3, 5), code de l'IDE (10) | Preuves sur la carte (5) ; fiches des trous repérés (5) ; version orale par le mode vocal (17) |
| 13 Alertes d'offres compatibles | Radar (8), score de match et écart (6), offres capturées (11) | Brief du matin (8) ; notifications mobiles (19) ; « Ajouter au planning » des manques (4, 6) |
| 14 Liaison GitHub | Connexion (9), dépôts poussés depuis l'IDE (10) | Preuves sur la carte (5) ; évaluation de projets sur un vrai dépôt (8) ; projets du profil maître (6) ; contenu du portfolio (20) ; liens du profil LinkedIn (15) |
| 15 Profil LinkedIn optimisé | Profil maître et validateur (6), offres visées (6, 13), projets GitHub (14) | Textes cohérents avec le CV ; contenu réutilisé par le portfolio (20) |
| 16 Entraînement « system design » | Tableau Excalidraw (3), Recruteur et personas d'entretien (7) | Preuves sur la carte (5) ; fiches (5) ; épreuve dans la simulation d'entretien (7) ; version orale (17) |
| 17 Mode vocal | Tuteur (5), Intervieweur (7), « Explique-moi » (12), system design (16) | Retours de clarté et de structure ; fiches (5) ; bilan d'entretien (7) |
| 18 Google Agenda | Connexion Google (9), planning et replanification (4, 5), entretiens et relances (7) | Créneaux réels pour la replanification (5) ; rappels dans l'agenda ; brief (8) |
| 19 Application mobile (PWA) | Fiches (5), brief et fil (8), alertes (13), agenda (18) | Révisions hors ligne et notifications ; capture rapide depuis le téléphone (5, 11) |
| 20 Site portfolio généré | Profil maître (6), projets évalués (8), GitHub (14), textes LinkedIn (15) | Lien du portfolio dans le CV, le profil LinkedIn et le kit de candidature (6, 7, 15) |

Ordre et dépendances : une phase ne dépend que de phases déjà livrées. Les liens vers une phase plus tardive (par exemple 10 → 14, 11 → 13, 12 → 17) sont branchés par la phase tardive, qui ajoute sa ligne dans le registre concerné.

## 6. Stratégie de tests

- **Back** : pytest + pytest-asyncio ; base SQLite en mémoire par test ; `FakeLlmProvider` (réponses scriptées, déterministes) branché via `dependency_overrides` ; faux fournisseurs pour vecteurs, recherche, PDF ; aucun appel réseau. Un test d'API par routeur, dont un test d'isolation entre deux utilisateurs.
- **Front** : Vitest + Testing Library pour chaque composant (dans son dossier) et chaque hook ; MSW pour simuler l'API ; un faux WebSocket pour le flux.
- **Bout en bout** : Playwright, back lancé avec le faux fournisseur LLM ; 3 parcours (18.2).
- **Contrôles** : `ruff`, `mypy --strict`, `import-linter`, `check_file_length.py`, `eslint`, `prettier`, `tsc --noEmit`, `export_openapi.py --check`, tous en pre commit.

## 7. Plans par lots à partir de la phase 11

Développer par lots de dix phases avec un plan par lot. Le premier lot commence avec le plan
détaillé de la phase 11. La phase 12 (extension Chrome) reste de côté. Voir D232.

| Lot | Phases |
| --- | --- |
| 1 | 11, puis 13 à 21 |
| 2 | 22 à 31 |
| 3 | 32 à 41 |
| 4 | 42 et 43 |

Le plan d’un lot décrit les dépendances, les tâches et les vérifications de chaque phase.
Les tâches indépendantes peuvent avancer en parallèle. Chaque phase a des tests ciblés et une
revue. En fin de lot, regrouper les contrôles et les parcours Playwright concernés avec une
ou deux revues d’ensemble.
Les commits intermédiaires sont locaux. Le push suit chaque tranche de vingt phases terminées
et testées. Le premier jalon est la phase 31, à la fin du deuxième lot (D231).

## 8. Reconstruction des programmes après la phase 43

Lorsque toutes les phases de développement et leurs recettes seront terminées, relire le pilote
LangChain conservé dans le [bilan de la phase 11](../bilans/phase-11.md), ajuster la norme si
besoin avec January et chiffrer la reconstruction des quatre
programmes. Après son accord sur le coût, reprendre les objectifs et les acquis correspondants,
produire les sommaires, puis générer et vérifier toutes les leçons avec le fournisseur choisi par
January (Claude sur le PC d'origine). Voir D227.

### 8.1 Un programme suit un ordre logique, jamais aléatoire (demande du 2026-11-22)

Constat : le programme LangChain ouvre sur LCEL (semaine 1, livrable « mini-outil en LCEL »).
Or la documentation officielle de LangChain v1 n'a plus de page LCEL : les anciennes pages
« LCEL » et « Runnables » redirigent vers l'accueil v1, centré sur les modèles, les messages, les
outils et `create_agent`. LCEL reste dans `langchain_core`, mais comme couche du dessous. Le
sommaire suivait donc une façon de faire dépassée, et l'ordre des semaines ne partait pas des
fondations.

Règles pour tout nouveau programme, et pour la reconstruction des quatre programmes :

- **Graphe des notions d'abord.** Le Stratège liste les notions du domaine avec, pour chacune,
  les notions qu'elle suppose. Le sommaire est un ordre de ce graphe : aucune semaine n'utilise
  une notion qui n'a pas été introduite avant. Un contrôle automatique refuse un sommaire qui
  viole cet ordre et le rend au Stratège avec la notion fautive (prolonge le contrôle des
  prérequis de la phase 11).
- **De zéro à expert, comme un livre.** Les premières semaines posent les fondations du domaine
  (ce qu'est l'objet étudié, son vocabulaire, son fonctionnement), puis la pratique courante,
  puis les cas avancés et les limites. Chaque semaine dit ce qu'elle suppose et ce qu'elle
  apporte à la suivante.
- **À jour de la version actuelle.** Pour une bibliothèque, le sommaire suit la structure de sa
  documentation officielle de la version en cours, lue au moment de la génération. Une API
  dépréciée ou devenue secondaire n'ouvre jamais un programme : elle va dans un encadré
  « lire du code ancien » à l'endroit où elle sert.
- **Justification visible.** Le sommaire proposé à January montre, pour chaque semaine, la
  raison de sa place (ce qu'elle débloque) et la source qui fixe l'ordre.

Exemple de sommaire LangChain conforme : (1) modèles de chat, messages, jetons, `invoke`,
`stream`, `batch` ; (2) prompts et sorties structurées ; (3) outils et appel d'outils ;
(4) premier agent avec `create_agent` ; (5) RAG ; (6) LangGraph pour les flux à état, boucles
et validation humaine ; LCEL et Runnables en encadré pour lire et migrer du code existant.

Pilote du 2026-11-22 : le chapitre de la semaine 1 (« Modèles, messages et chaînes LCEL ») a été
réécrit selon la norme sur la pile jetable `check1` (2 285 mots, 5 sources, code en anglais).
Sa seconde moitié porte encore sur LCEL : à revoir avec le nouveau sommaire.

## 9. Après la réorganisation de Codex : tester le code sans quitter la leçon

À faire **après** la réorganisation de l'interface et l'ouverture complète du MCP confiées à
Codex (prompt du 2026-11-22), pas avant.

Depuis une leçon, chaque bloc de code Python a un bouton « Essayer ». Il ouvre l'IDE dans un
panneau latéral ou une modale, **sans quitter la page de la leçon** : le bloc y est chargé, January
le modifie et l'exécute dans le bac à sable, voit la sortie, et peut demander de l'aide au
professeur avec la leçon en contexte. Fermer le panneau ramène exactement au même endroit de la
leçon. Les règles du bac à sable ne changent pas (aucun réseau, aucun secret, aucun montage de
l'hôte) ; un exemple qui appelle un modèle passe par la passerelle modèle prévue pour l'IDE
(phase 14) ou affiche clairement qu'il ne peut pas tourner dans le bac. L'action est exposée par
MCP comme le reste.

## 10. Neuf features retenues le 2026-11-22 (phases 64 à 72)

Proposées le 22/11 ; January garde tout sauf le « diagnostic de ton code réel ». Ordre : **après**
la réorganisation de l'interface par Codex et la reconstruction des programmes (§8), dont elles
dépendent. Mêmes règles que les autres phases : séance de conception, plan, outils MCP pour
chaque feature, et place dans le menu ou le Labo décidée avec January pour ne pas recharger
l'interface.

| Phase | Fonctionnalité | Idée | S'appuie sur |
| --- | --- | --- | --- |
| 64 | Leçons à schéma animé | Pour **chaque** leçon : le schéma reste fixé sur le côté (en haut sur mobile) et se construit pendant que January fait défiler l'explication ; chaque partie qui entre à l'écran fait apparaître ses nœuds et ses flèches, et le schéma se replie quand elle remonte. Le Rédacteur rattache chaque nœud et chaque flèche à une sous-partie de l'Explication ; le Vérificateur contrôle ce rattachement. Avec `prefers-reduced-motion`, le schéma complet s'affiche d'emblée ; tout reste utilisable au clavier et lisible par un lecteur d'écran. | Norme des leçons (§8.1), rendu Mermaid |
| 65 | Test de placement | Au démarrage d'un programme, un court diagnostic repère les notions déjà acquises ; le parcours de zéro à expert les marque comme sues (rappel bref) au lieu de les réexpliquer. | Graphe des notions (§8.1), quiz |
| 66 | Projet fil rouge | Un seul projet qui grandit de semaine en semaine dans l'IDE : chaque leçon y ajoute une brique, et le projet final devient une preuve de compétence. | IDE (phase 14), §9, programmes |
| 67 | Radiographie d'un appel IA | Exécuter une chaîne ou un agent et voir l'intérieur : messages envoyés, appels d'outils, jetons, coût et durée de chaque étape. | IDE, passerelle modèle, coûts |
| 68 | Banc d'essai des modèles | Le même prompt envoyé à plusieurs modèles (Claude, GPT, GLM, local) : réponses, coût et vitesse côte à côte. | Registre de modèles, coûts |
| 69 | Absorber un cours externe | Une vidéo, des notes, un PDF ou un **EPUB de plusieurs centaines de pages** : découpage par la table des matières du livre, traitement en tâche de fond avec progression et reprise après coupure, **coût estimé et accepté avant le lancement**, chaque partie rangée au bon endroit du graphe des notions du programme. Le livre reste local ; les leçons le reformulent, jamais de recopie (contrôle de recopie existant). Test obligatoire sur un EPUB réel de plusieurs centaines de pages. | Mémoire, Cerveau, §8.1 |
| 70 | Katas de code quotidiens | Cinq minutes par jour : un petit exercice de code tiré des leçons, exécuté dans le bac à sable et reprogrammé selon la répétition espacée. | IDE, fiches |
| 71 | Mode examen de certification | Examens blancs chronométrés dans les conditions d'une vraie certification, puis bilan des points faibles relié aux leçons. | Quiz, programmes |
| 72 | Mode 100 % local | Étudier entièrement avec le modèle local (Ollama), sans clé ni coût ; Claude seulement pour ce qui l'exige, sur accord. **Le PC doit rester utilisable** (constat du 22/11 : l'indexation du Cerveau a saturé 8 cœurs) : Tremplin mesure d'abord la mémoire, le processeur et la carte graphique, et propose un petit modèle quantifié adapté (de l'ordre de 4 milliards de paramètres au plus, 4 Go de mémoire au plus sur un PC sans carte graphique) ; un seul modèle chargé à la fois, déchargé après inactivité ; nombre de cœurs plafonné (la moitié par défaut, réglable) ; tâches lourdes (indexation, cours externes) mises en pause sur batterie et quand January utilise le PC, avec reprise ensuite. Le même plafond s'applique à l'indexation existante du Cerveau. | Registre de modèles, Ollama |
