# Lancement des parcours depuis Tremplin · Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**But.** Chaque bouton qui lance des agents propose un menu : Claude Code, Codex, API Claude,
API GLM et API OpenAI, selon ce qui est disponible. Le choix vaut pour tout le parcours, y compris
les attentes, les reprises et les sessions filles.

**Architecture.**
- **Mémorisation du choix.** La session garde déjà `played_by` (client MCP). Elle gagne
  `model_provider` (fournisseur d'API forcé). Les deux sont posés au démarrage par une
  variable de contexte, la même que pour le lancement par MCP. Ils sont relus à chaque
  reprise et recopiés sur les sessions filles.
- **Transmission depuis le front.** Le front envoie le choix dans l'en-tête `X-Tremplin-Run`
  sur les routes de lancement existantes. Aucun schéma de feature ne change.
- **Le relais.** Le back tourne dans Docker et ne peut pas démarrer un programme de Windows.
  Un petit **relais** Node, lancé sur l'hôte, signale les clients présents. Il démarre
  `claude -p` ou `codex exec` sur chaque session jouée qui attend une étape. Le client
  joue alors par MCP, comme en 10b.

**Pile technique.** FastAPI, SQLAlchemy, Alembic, LangGraph (back). React 19, TanStack Query
(front). Node ≥ 22 sans dépendance (relais), `node:test`.

**Références.**
- [Plan 10b](2026-11-18-10b-plan-detaille.md), section 5.
- [Cadrage 10b](2026-11-18-10b-agents-joues-par-mcp.md).
- D214 à D216 dans `DECISIONS.md`.
- [docs/mcp/AGENTS.md](../../mcp/AGENTS.md), section « Jouer un agent ».

## Décisions (demandes de January du 18 novembre)

1. **Relais automatique.** January ne lance rien elle-même.
   - **Installation.** `node relay/install.mjs` est exécuté une seule fois, avec son accord.
     Il inscrit le relais au démarrage de sa session Windows, par une tâche planifiée sans
     fenêtre (`schtasks /create /sc onlogon`).
   - **Veille.** Le relais tourne en permanence. Il reste en veille tant que Tremplin ne
     répond pas.
   - **Détection.** Il redétecte `claude` et `codex` toutes les 5 min.
   - **Appairage.** Au premier contact, le relais demande un appairage. Tremplin affiche
     « Connecter les agents locaux ? » dans Réglages > Modèles. January clique une fois. Le
     jeton du relais lui est remis et il le range dans `%APPDATA%\Tremplin\relay.json`, lisible
     par son seul compte. C'est un geste de niveau 4, jamais exposé au MCP.
   - **Sans relais**, Claude Code et Codex apparaissent « indisponibles », avec la raison.
2. **Choix par défaut dans Réglages > Modèles** (`/reglages/modeles`). Un réglage « Exécution
   des agents » propose :
   - « Clés d'API » : le comportement actuel, un modèle par niveau ;
   - « Claude Code (MCP) » ;
   - « Codex (MCP) ».

   La disponibilité de chaque client y est affichée en direct, et le réglage est enregistré
   dans `UserSettings.run_source`. Le menu de chaque bouton part de ce réglage. Pour un
   lancement, January peut choisir une autre entrée : Claude Code, Codex, API Claude, API
   GLM, API OpenAI ou « Selon mes réglages ».
3. **Emplacement.** Le menu est accolé à chaque bouton de lancement (bouton partagé
   « Lancer ▾ »). Il n'y a pas de sélecteur global dans l'en-tête de l'application.
4. **Limites MCP.** Un parcours joué rend une étape par écriture MCP, avec une limite de 10 par
   minute. Le relais respecte le délai d'un 429 avant de rendre la main au client, et la
   consigne du client le rappelle.

## Contraintes globales

- `AGENTS.md` s'applique en entier :
  - fichiers de 300 lignes au plus, fonctions de 50 lignes au plus ;
  - mypy strict, les 9 contrats import-linter ;
  - contrat OpenAPI puis `schema.d.ts` régénérés ;
  - textes en français dans `shared/i18n/messages` ;
  - un dossier par composant ;
  - TDD et commits par chemins explicites.
- Valeurs de l'en-tête et de la colonne :
  - clients : `claude-code`, `codex` ;
  - fournisseurs : `api:anthropic`, `api:glm`, `api:openai` ;
  - réglages : `settings`, ou en-tête absent (comportement actuel inchangé).
- Le planificateur (brief, radar, replanification hebdomadaire, `ats_refresh`) n'utilise jamais
  un choix de lancement : il suit les réglages.
- Le plafond `LaunchQuota` (30 par jour) s'applique à tout lancement joué, comme en 10b.
- Le relais :
  - ne journalise que des identifiants, des codes et des durées ;
  - ne lit jamais `.env` ;
  - n'écrit jamais le jeton sur disque hors d'un fichier temporaire supprimé en fin de
    lancement ;
  - borne le client aux seuls outils `agents_play_*`, `sessions_get_session` et à la
    recherche web.
- Un lancement par API vers un fournisseur sans clé lisible est refusé **avant** de créer la
  session : 409 `llm_key_missing`, message existant.

## Points d'attention de la revue

- **Clic pendant que le relais est arrêté.** Le choix d'un client est refusé avec 409
  `client_unavailable`, et l'interface le dit. Une session déjà jouée reste en attente : son
  étape expire après 24 h, comme en 10b.
- **Relais relancé en pleine session.** L'étape réservée n'est pas rendue deux fois : la
  réservation de la 10b protège. Le nouveau client reprend le brief courant.
- **Reprise après une décision de January.** La session reprend avec le même `played_by` ou
  `model_provider`. Le relais voit la nouvelle étape et relance le client.
- **Sessions filles hors du contexte d'exécution.** Le parcours garde sa source dans quatre
  cas :
  - `retry_program` depuis `POST /proposals/{id}/choose` ;
  - `projects/regenerate.py` ;
  - leçons après validation ;
  - correction du quiz.

  Les deux premiers n'héritent pas aujourd'hui : ce sont des écarts de la 10b, corrigés à la
  tâche 1.
- **Clé révoquée entre le lancement et une reprise.** La reprise échoue comme aujourd'hui
  (`llm_key_missing`, session `failed`). Elle ne bascule jamais en silence vers un autre
  fournisseur.

---

### Tâche 1 : source du parcours, mémorisée et héritée (back)

**Fichiers :**
- Créer `backend/alembic/versions/0018_session_model_provider.py` : colonne nullable
  `agent_sessions.model_provider` (`anthropic|glm|openai`).
- Modifier les fichiers suivants :
  - `backend/app/core/played.py` : `RunSource`, contexte, héritage ;
  - `backend/app/db/models/agents.py` ;
  - `backend/app/agents/runtime/runner.py:106-118` ;
  - `backend/app/agents/runtime/playback.py:22-28` ;
  - les appelants de `inherit_play` : `lessons/service/production.py:128-133,172`,
    `projects/service/submit.py:186`, `quiz/service/attempts.py:173` ;
  - `learning/service/choice.py:203` ;
  - `projects/regenerate.py:53`.
- Créer `backend/app/agents/runtime/forced_models.py` : un fournisseur forcé pour tous les
  niveaux.
- Tests : `backend/tests/agents/runtime/test_run_source.py` et
  `backend/tests/features/learning/test_choice_inherits_source.py`.

**Interfaces produites :**
- `type RunSource = Literal["claude-code", "codex", "api:anthropic", "api:glm", "api:openai"]`
- `PlayContext` reçoit un champ `provider: Provider | None = None` (`Provider =
  Literal["anthropic","glm","openai"]`). `client` devient `PlayClient | None`.
- `run_source(user_id) -> tuple[PlayClient | None, Provider | None]`, qui remplace
  `played_by()` dans `runner.start`. `played_by()` reste disponible pour le code existant.
- `inherit_source(user_id, client, provider)` remplace `inherit_play`. L'ancien nom reste un
  alias tant qu'un appelant l'utilise.
- `ForcedModels(usual: ChatModelSource, provider: Provider)`. La règle par niveau est la
  suivante :
  - si le choix de la personne pour ce niveau est déjà chez ce fournisseur, il est gardé ;
  - sinon on prend le modèle du préréglage : `haiku_sonnet_strong` pour `anthropic`,
    `all_glm`, `all_openai` (`model_defaults.py:212-217`).

**Étapes :**

- [ ] Écrire les tests rouges :
  - `test_api_source_is_stored_and_forces_provider_on_every_tier` ;
  - `test_resume_after_restart_keeps_model_provider` ;
  - `test_child_session_inherits_client_and_provider` ;
  - `test_choose_retry_program_inherits_played_by` ;
  - `test_regenerate_drafts_inherits_source` ;
  - `test_scheduler_launch_ignores_source`.

  Chaque test s'appuie sur `SessionRunner`, le checkpoint SQLite et un `FakeChatModelSource`
  existant. On vérifie la ligne `agent_sessions`, puis les `llm_calls` : le fournisseur forcé,
  ou 0 $ pour un client.
- [ ] Les lancer et constater l'échec : colonne absente, héritage manquant.
- [ ] Écrire la migration et le modèle, puis `run_source`, `inherit_source` et `ForcedModels`.
  Brancher `models_for` : `played_by` d'abord, puis `model_provider`, sinon la source
  habituelle.
- [ ] Rejouer les tests, plus `tests/agents tests/features/learning tests/features/lessons
  tests/features/projects tests/features/quiz tests/isolation -q`. `alembic upgrade head`
  doit passer sur une base vide.
- [ ] Faire une décision `D217` : la colonne séparée, la règle de forçage et l'héritage
  complété. Committer `feat(10b): source du parcours mémorisée et héritée`.

### Tâche 2 : choix reçu par l'en-tête sur toutes les routes de lancement (back)

**Fichiers :**
- Créer `backend/app/core/run_header.py` : un middleware ASGI pur (pas `BaseHTTPMiddleware`)
  qui lit `X-Tremplin-Run`, en vérifie la forme (sinon 422) et pose la valeur brute dans
  `RUN_REQUEST: ContextVar[RunSource | None]`. Il ne connaît pas l'utilisatrice :
  l'authentification est une dépendance de route.
- Modifier `backend/app/agents/runtime/runner.py` : `start(user_id, …)` convertit
  `RUN_REQUEST` en `played_by` ou `model_provider` pour ce compte, **avant** d'insérer la
  ligne. Il passe par un port `RunSourceGuard` (clé lisible, présence du relais) injecté par
  `bootstrap`.
- Modifier `backend/app/main.py` : enregistrer le middleware.
- Modifier `backend/app/mcp/played.py` : le lancement MCP garde sa voie. L'en-tête est ignoré
  sous une identité MCP.
- Tests : `backend/tests/features/sessions/test_run_header.py`.

**Interfaces :**
- Consomme `run_source` et `PlayContext` (tâche 1).
- Produit les erreurs suivantes, au format `{"error": …}` en français, sans écho de l'en-tête :
  - 422 `invalid_run_source` pour une valeur inconnue ;
  - 409 `llm_key_missing` pour un fournisseur sans clé lisible ;
  - 409 `client_unavailable` pour un client absent de la présence du relais (tâche 3).

**Étapes :**

- [ ] Écrire les tests rouges, paramétrés sur les lancements de `Registry.play_launches`.
  On réutilise la liste de la 10b : une seule source de vérité.
  - `test_header_codex_marks_session_played` : 202, puis `played_by == "codex"` sur la ligne.
  - `test_header_api_glm_sets_model_provider`.
  - `test_unknown_value_is_422_without_echo`.
  - `test_provider_without_key_is_refused_before_any_session` : aucune ligne créée.
  - `test_client_without_relay_is_409`.
  - `test_absent_header_keeps_current_behaviour`.
  - `test_header_ignored_under_mcp_identity`.
- [ ] Les lancer et constater l'échec.
- [ ] Écrire le middleware et `RunSourceGuard`. La présence du relais (tâche 3) et les clés
  arrivent par ce port : ni `app.core` ni `app.agents` n'importent une feature.
- [ ] Rejouer `tests/features/sessions tests/mcp tests/isolation -q`, puis `lint-imports`.
- [ ] Committer `feat(10b): choix du parcours reçu par l'en-tête X-Tremplin-Run`.

### Tâche 3 : options du menu, présence du relais et étapes en attente (back)

**Fichiers :**
- Modifier :
  - `backend/app/features/sessions/play_router.py` (GET `/sessions/run-options`) ;
  - `play_service.py` ;
  - `play_schemas.py` ;
  - `backend/app/features/sessions/mcp.py` (deux outils).
- Créer `backend/app/features/sessions/presence.py` : présence en mémoire par compte, avec
  la date du dernier signal.
- Tests :
  - `backend/tests/features/sessions/test_run_options.py` ;
  - `backend/tests/mcp/test_relay_tools.py` ;
  - un cas d'isolation dans `tests/isolation/test_played_sessions.py`.

**Interfaces produites :**
- `GET /sessions/run-options` renvoie `list[RunOption]`, avec
  `RunOption {id: RunSource | "settings", available: bool, reason: str | None}`.
  - Une API est disponible si `has_key` (`GET /settings/models`) est vrai.
  - Un client est disponible s'il figure dans le dernier signal du relais, émis il y a moins
    de 30 s.
- Outil MCP `agents_play_presence` (niveau 1) : `{clients: ["claude-code" | "codex"]}`. Il
  n'écrit que la présence en mémoire, sans donnée de la personne.
- Outil MCP `agents_play_pending` (niveau 1) : la liste
  `[{session_id, graph, played_by, step_id, expires_at}]` des sessions du compte qui
  attendent un rendu, filtrée par `played_by`.

**Étapes :**

- [ ] Écrire les tests rouges :
  - `test_options_reflect_keys_and_presence` : trois API, une avec clé ; relais avec
    `claude-code` seul ;
  - `test_presence_expires_after_30s` : horloge injectée ;
  - `test_pending_lists_only_waiting_client_steps` ;
  - `test_pending_is_isolated_between_users` ;
  - `test_tools_declared_with_levels` : garde de couverture et `scripts.mcp_levels`.
- [ ] Les lancer et constater l'échec.
- [ ] Écrire le code. Ajouter les deux outils dans `sessions/mcp.py` (niveau 1). Régénérer
  `contracts/openapi.json` et `schema.d.ts`.
- [ ] Rejouer les tests ciblés, `tests/mcp/test_coverage_guard.py` et
  `export_openapi --check`.
- [ ] Committer `feat(10b): options de lancement et présence du relais`.

### Tâche 3b : réglage par défaut et appairage du relais (back et front)

**Fichiers :**
- Back :
  - `features/settings/schemas.py` et `service.py` : `UserSettings.run_source:
    Literal["settings","claude-code","codex"] = "settings"` ;
  - `features/mcp/router.py` : appairage.
- Front :
  - `features/settings/components/RunSourceSetting/` ;
  - la page « Modèles » de `features/settings/pages`.
- Tests :
  - `tests/features/settings/test_run_source_setting.py` ;
  - `tests/features/mcp/test_relay_pairing.py` ;
  - `tests/isolation/` ;
  - Vitest pour la page.

**Interfaces produites :**
- `POST /mcp/relay/pair-requests`, sans authentification et seulement depuis `127.0.0.1`.
  - Le relais y dépose une demande et reçoit `{request_id, poll_secret}`.
  - Une seule demande est ouverte à la fois, et elle expire en 10 min.
- `GET /mcp/relay/pair-requests/current` (cookie) : la demande en attente, pour l'afficher à
  January.
- `POST /mcp/relay/pair-requests/{id}/approve` (cookie, niveau 4) crée un jeton `relay`.
  - Portée : `sessions` en écriture, plus les features jouables.
  - Durée : 90 jours, renouvelé à l'usage.
  - Il est visible et révocable dans Réglages > Accès MCP.
- `GET /mcp/relay/pair-requests/{id}?secret=` : le relais récupère son jeton une seule fois.
- Le lancement sans en-tête suit `run_source`. Le planificateur ne le suit jamais.

**Étapes :**

- [ ] Écrire les tests rouges :
  - `test_default_run_source_applies_to_launch_without_header` ;
  - `test_scheduler_ignores_run_source` ;
  - `test_pairing_needs_january_click` ;
  - `test_pair_token_delivered_once` ;
  - `test_pair_request_refused_from_non_local_host` ;
  - `test_pairing_isolated_between_users` ;
  - côté front, la page affiche les trois choix, la disponibilité en direct et la demande
    d'appairage.
- [ ] Les lancer et constater l'échec. Écrire le code. Régénérer le contrat et les types.
- [ ] Rejouer les tests ciblés et la garde MCP (`test_coverage_guard`). Les routes d'appairage
  sont exclues du MCP avec le motif « niveau 4 ».
- [ ] Committer `feat(10b): réglage d'exécution des agents et appairage du relais`.

### Tâche 4 : le relais local (Node, hôte Windows)

**Fichiers :**
- Créer :
  - `relay/tremplin-relay.mjs` (boucle) ;
  - `relay/clients.mjs` (détection et commandes) ;
  - `relay/mcp.mjs` (appel JSON-RPC) ;
  - `relay/pairing.mjs` : demande d'appairage, attente du clic, rangement du jeton dans
    `%APPDATA%\Tremplin\relay.json` (ACL au seul compte) ;
  - `relay/install.mjs` et `uninstall.mjs` : tâche planifiée `Tremplin relais` à l'ouverture de
    session, lancée sans fenêtre par `node` ;
  - `relay/prompt.md` (consigne donnée au client) ;
  - `relay/README.md`.
- L'installation est le seul geste sur Windows, fait une fois avec l'accord de January. Si
  Smart App Control bloque la tâche, s'arrêter et le dire.
- Tests :
  - `relay/test/*.test.mjs` (`node --test relay/test`) ;
  - un faux serveur MCP et deux faux clients (`relay/test/fake-claude.mjs`,
    `fake-codex.mjs`).

**Interfaces :**
- Consomme `agents_play_presence`, `agents_play_pending` (tâche 3) et le jeu de la 10b.
- Boucle, toutes les 5 s :
  1. Détecter les clients (`claude --version`, `codex --version`, une fois au démarrage puis
     toutes les 5 min).
  2. Envoyer la présence.
  3. Lire les étapes en attente.
  4. Pour chaque session sans client en cours, démarrer un client. Au plus un client à la
     fois par session, deux en tout.
- Commande Claude Code :

  ```
  claude -p <prompt> --mcp-config <fichier temporaire> --strict-mcp-config
    --allowedTools <outils agents_play_*, sessions_get_session, WebSearch, WebFetch>
    --permission-mode dontAsk --output-format json
  ```

- Commande Codex :

  ```
  codex exec --search --sandbox read-only --skip-git-repo-check --ephemeral
    -c mcp_servers.tremplin.url=… -c mcp_servers.tremplin.bearer_token_env_var=TREMPLIN_MCP_TOKEN
    <prompt>
  ```

- La consigne (`prompt.md`) demande au client de jouer la session `<id>` par
  `agents_play_brief` et `agents_play_submit`. Il s'arrête dès que `step_id` est nul ou que la
  session n'est plus en cours. Il ne répond jamais à une question destinée à January.
- Délai maximal de 20 min par lancement. Le processus est tué au-delà : l'étape reste
  réservée et la 10b la fait expirer.

**Étapes :**

- [ ] Vérifier les drapeaux ci-dessus contre la doc officielle de Claude Code et de Codex (les
  versions installées sont 2.1.327 et 0.170.0). Corriger le plan si un nom diffère.
- [ ] Écrire les tests rouges :
  - `starts_one_client_per_pending_session` ;
  - `never_starts_twice_for_same_session` ;
  - `kills_after_timeout` ;
  - `temp_mcp_config_is_deleted` ;
  - `logs_contain_no_token_nor_text` ;
  - `missing_token_env_exits_with_french_message` ;
  - `unknown_client_is_not_announced`.
- [ ] Les lancer et constater l'échec. Écrire le relais.
- [ ] Faire passer `node --test relay/test`. Ajouter `relay/` aux contrôles ESLint, ou à une
  règle dédiée, si la config s'y prête. Sinon, noter l'exclusion en D218.
- [ ] Décision `D218` : le relais sur l'hôte, les outils permis au client, la limite de
  concurrence et le délai. Committer `feat(10b): relais local pour Claude Code et Codex`.

### Tâche 5 : le menu partagé et la chaîne du programme (front)

**Fichiers :**
- Créer :
  - `frontend/src/shared/session-ui/RunSourceMenu/` (`RunSourceMenu.tsx`, `.test.tsx`,
    `index.ts`) : composant présentationnel qui reçoit `options`, `value`, `onChange`,
    `onLaunch` et `pending` ;
  - `frontend/src/shared/session-ui/useRunOptions.ts` : requête `GET /sessions/run-options`
    et dernier choix par fonctionnalité en `localStorage`, protégé par try/catch.
- Modifier `frontend/src/shared/api/` : `runHeaders(source)` renvoie
  `{ "X-Tremplin-Run": source }`, ou rien pour `settings`.
- Modifier `frontend/src/shared/i18n/messages/` : libellés des six entrées, raisons
  d'indisponibilité, erreurs `client_unavailable` et `invalid_run_source`.
- Brancher le menu dans :
  - `learning` : `CouncilIndexPage`, `GoalsPage` (création d'objectif), `CouncilFailure`
    (nouvelle tentative) ;
  - `program` : `useValidationFlow`, pour la validation qui lance les leçons.

**Étapes :**

- [ ] Écrire les tests rouges :
  - `RunSourceMenu` liste les options et désactive celles qui sont indisponibles, avec la
    raison lisible ;
  - tout se fait au clavier, le focus est rendu au bouton après la fermeture ;
  - `useCreateGoal` envoie l'en-tête ;
  - l'erreur 409 `client_unavailable` est affichée en français.
- [ ] Les lancer (`node node_modules/vitest/vitest.mjs run src/shared/session-ui
  src/features/learning src/features/program`) et constater l'échec.
- [ ] Écrire le composant, le hook et le branchement des quatre points.
- [ ] Rejouer les tests, puis `node frontend/scripts/run-tool.mjs lint` et `typecheck`.
- [ ] Committer `feat(10b): menu de lancement sur la chaîne du programme`.

### Tâche 6 : le menu sur les autres fonctionnalités (front)

Même motif que la tâche 5, un commit par groupe :
- (a) `applications` : prise en charge, kit, entretiens, comité ;
- (b) `cv` et `capture` ;
- (c) `gap`, `postings` et `radar` ;
- (d) `quiz`, `study`, `replan` et `projects` ;
- (e) `ide`, `memory` (`markLearned`), `research` et la démo.

Ajouter un garde : un test Vitest échoue si un hook de lancement (fonction d'`api.ts` qui rend
un `session_id`) n'accepte pas `runHeaders`. On le repère par son type de retour dans
`schema.d.ts`.

- [ ] Pour chaque groupe : tests rouges, branchement, tests verts, commit.
- [ ] Ajouter le garde. Lancer la suite front complète une fois à la fin.

### Tâche 7 : recette de bout en bout et documentation

- [ ] Monter une pile jetable `learning_career_platform-check12-*` sans clé d'API, avec le
  relais lancé sur l'hôte et un jeton de test d'un jour.
- [ ] Choisir Claude Code dans le menu, créer un objectif court et répondre au cadrage dans
  l'interface. Vérifier que le relais démarre le client à chaque étape, que le Conseil
  aboutit, que le choix de la proposition puis la validation se font dans Tremplin, et que
  les leçons sont jouées. Le suivi doit afficher « joué par Claude » sur chaque rôle et les
  coûts doivent rester à 0 $.
- [ ] Rejouer un lancement avec « API GLM » sur un seul parcours court, avec l'accord de
  January pour le quota.
- [ ] Mettre à jour la documentation :
  - `docs/mcp/AGENTS.md`, section « Lancer depuis Tremplin » : relais, jeton, sécurité ;
  - `backend/app/mcp/instructions.py`, si la règle change ;
  - le bilan `phase-10b.md` ;
  - cocher la section 5 du plan 10b.
- [ ] Lancer une fois la suite back complète. Retirer la pile jetable.
