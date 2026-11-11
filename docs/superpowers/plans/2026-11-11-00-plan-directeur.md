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

### Phase 2 — Mémoire (F3)

- Back : fournisseurs `embeddings/ollama`, `vector/qdrant` derrière `MemoryRepository`, `storage/local`, `pdf/extract` ; tables `documents`, `memory_items`, `memory_chunks`, `memory_writes` ; chaîne d'ingestion (PDF, DOCX, Markdown, texte, URL, YouTube, texte collé ; fragments ~500 tokens, recouvrement 60 ; hash anti doublon ; statuts) ; outils `memory_search`, `memory_write`, `memory_get_skills` ; boîte « À confirmer » pour les `decision` ; agent Archiviste (« déjà appris » → acquis `declare`) ; carte 2D par PCA ; réindexation ; export JSON ; endpoints `/documents`, `/memory/*`.
- Front `memory/` : `MemoryTable`, `MemoryItemDrawer`, `SemanticSearch`, `VectorMap`, `SearchBench`, `MemoryStats`, `DocumentUpload`, `PendingDecisions`.
- **Terminée quand** un PDF importé se retrouve par recherche et une écriture d'agent s'affiche avec son auteur.

### Phase 3 — Recherche web

- Back : `search/` (`SearchProvider`, SearXNG, Brave plafonné à 900 requêtes par mois, ordre de repli) ; `web/` (`web_read` : httpx + trafilatura, repli Gotenberg, PDF, YouTube, GitHub, arXiv ; statut `ok`/`unreadable`) ; garde SSRF (adresses privées, protocoles), 15 s par page, 1 requête/s/domaine, cache `web_cache` 7 jours ; retrait nom/email/téléphone des requêtes ; notation des sources sur 100 (seuil 60) ; plafonds 12 requêtes / 30 pages par session ; table `sources` ; domaines privilégiés et exclus dans les réglages ; `web_tools`.
- Front : réglages de recherche (langues, domaines).
- **Terminée quand** une requête renvoie des sources notées et lues, et une page illisible est signalée.

### Phase 4 — Conseil et programme (F1, F2)

- Agents : Modérateur, Stratège, Praticien, Éclaireur, Sceptique, Scribe, Rédacteur, Vérificateur. Graphes `learning_council`, `program_builder`, `lesson_factory`.
- Back : tables `goals`, `proposals`, `boards`, `programs`, `weeks`, `modules`, `tasks`, `lessons`, `resources`, `plan_versions`, `skills`, `skill_edges`, `user_skills` ; règles du débat (9.3) ; 3 points d'arrêt ; règles de planification (85 %, disponibilité, acquis sautés, pratique + quiz chaque semaine) ; leçons Markdown 1 200–2 500 mots, structure fixe ; PDF A4 via Gotenberg ; ressources 3–6 par module ; export PDF et `.ics` ; tâche planifiée « leçons à J-7 ».
- Front : `learning/` (Objectifs, page Conseil sur `shared/session-ui`, `Board` Excalidraw avec apparition élément par élément 150–300 ms et repli SVG Mermaid, `ProposalCards`), `program/` (`WeekCalendar` glisser déposer, `TaskList`, `PlanDiff`, `ProgressOverview`), `lessons/` (`LessonReader`, Bibliothèque).
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

## 6. Stratégie de tests

- **Back** : pytest + pytest-asyncio ; base SQLite en mémoire par test ; `FakeLlmProvider` (réponses scriptées, déterministes) branché via `dependency_overrides` ; faux fournisseurs pour vecteurs, recherche, PDF ; aucun appel réseau. Un test d'API par routeur, dont un test d'isolation entre deux utilisateurs.
- **Front** : Vitest + Testing Library pour chaque composant (dans son dossier) et chaque hook ; MSW pour simuler l'API ; un faux WebSocket pour le flux.
- **Bout en bout** : Playwright, back lancé avec le faux fournisseur LLM ; 3 parcours (18.2).
- **Contrôles** : `ruff`, `mypy --strict`, `import-linter`, `check_file_length.py`, `eslint`, `prettier`, `tsc --noEmit`, `export_openapi.py --check`, tous en pre commit.

## 7. Prochaine étape

Exécuter le plan de la phase 0, puis celui de la phase 1. Avant la phase 2, écrire son plan détaillé à partir du code obtenu.
