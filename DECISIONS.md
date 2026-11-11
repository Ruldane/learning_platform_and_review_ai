# Décisions

> Tout écart entre la spec et une bibliothèque, ou tout choix que la spec ne tranche pas, est ajouté ici.

Chaque entrée : date, sujet, décision, raison.

## D1

- **Date** : 2026-11-11
- **Sujet** : `POST /postings`, `/sessions`, `/health`, `/costs` n'ont pas de dossier feature dans 12.3
- **Décision** : Ajouter `features/postings`, `features/sessions`, `features/health`, `features/costs`
- **Raison** : les endpoints de la section 14 doivent avoir une feature qui les porte, sans quoi la règle « une feature = un dossier » est cassée.

## D2

- **Date** : 2026-11-11
- **Sujet** : Front `home` vs back `brief`, et front sans `gap` ni `replan` alors que les noms doivent être identiques
- **Décision** : Front : ajouter `gap/` et `replan/`. Garder `home` (c'est un écran d'accueil), qui consomme l'API `brief` ; exception notée
- **Raison** : la règle des noms identiques front/back doit rester vraie ; `home` est un écran d'accueil, pas une ressource, d'où l'exception documentée.

## D3

- **Date** : 2026-11-11
- **Sujet** : Statuts de session (`running`, `waiting_user`, `completed`, `failed`) sans état pour Pause et Annuler
- **Décision** : Ajouter `paused` et `cancelled`
- **Raison** : les boutons Pause et Annuler de la spec exigent un état persistant, sinon la reprise et l'affichage sont ambigus.

## D4

- **Date** : 2026-11-11
- **Sujet** : Messages de l'utilisatrice pendant un débat : aucun type d'événement ni table
- **Décision** : Nouveau type d'événement `user.message`, enregistré dans `session_events` ; les nœuds lisent les messages non traités au début de chaque tour
- **Raison** : la spec ne dit pas comment un message de l'utilisatrice entre dans un débat ; un événement rejouable garde le journal complet et le replay cohérents.

## D5

- **Date** : 2026-11-11
- **Sujet** : Index « dès la première migration » sur des tables créées plus tard
- **Décision** : Chaque index est créé dans la migration de la phase qui crée sa table
- **Raison** : une migration ne peut pas indexer une table qui n'existe pas encore ; Alembic reste la seule source du schéma.

## D6

- **Date** : 2026-11-11
- **Sujet** : Niveau de maîtrise stocké à deux endroits (`user_skills` et éléments `acquis` en mémoire)
- **Décision** : `user_skills` fait foi ; l'élément `acquis` en est le reflet indexé, resynchronisé à chaque changement de niveau
- **Raison** : une seule source de vérité évite les divergences ; l'élément mémoire reste utile pour la recherche sémantique.

## D7

- **Date** : 2026-11-11
- **Sujet** : Le Stratège crée le référentiel de compétences en phase 4, la carte F15 arrive en phase 5
- **Décision** : Tables `skills`, `skill_edges`, `user_skills` créées en phase 4, interface en phase 5
- **Raison** : le Stratège a besoin du référentiel dès la phase 4 ; l'interface de la carte peut venir plus tard sans changer le schéma.

## D8

- **Date** : 2026-11-11
- **Sujet** : Clé dans `.env` et clé saisie dans l'interface
- **Décision** : La clé saisie dans l'interface est prioritaire ; `.env` sert de repli
- **Raison** : l'utilisatrice doit pouvoir changer de clé sans toucher aux fichiers ; `.env` reste un point de départ pratique.

## D9

- **Date** : 2026-11-11
- **Sujet** : Composants de débat utilisés par 3 features
- **Décision** : Placés dans `shared/session-ui/`
- **Raison** : trois features (Conseil, Comité, Tuteur) utilisent ces composants ; une feature n'importe jamais une autre, donc ils vivent dans `shared`.

## D10

- **Date** : 2026-11-11
- **Sujet** : Contrat front/back
- **Décision** : `contracts/openapi.json` versionné, vérifié en CI
- **Raison** : un contrat versionné permet de générer les types du front et de détecter toute dérive de l'API en CI.

## D11

- **Date** : 2026-11-11
- **Sujet** : Router front
- **Décision** : React Router (mode data), routes déclarées par les manifestes
- **Raison** : routeur standard, avec chargeurs de données ; les manifestes de feature déclarent leurs routes sans toucher à un fichier central.

## D12

- **Date** : 2026-11-11
- **Sujet** : Le schéma d'architecture de la section 12 est absent du document (« embedded content »)
- **Décision** : Le texte de 12 et 16.1 suffit ; rien à reconstituer
- **Raison** : le schéma est absent (contenu embarqué) mais le texte des sections 12 et 16.1 décrit déjà l'architecture complète.

## D13

- **Date** : 2026-11-11
- **Sujet** : `infra/searxng/settings.yml` dans `backend/` (16.2)
- **Décision** : Respecté tel quel
- **Raison** : la spec est explicite ; aucun écart à consigner.

## D14

- **Date** : 2026-11-11
- **Sujet** : Champ `type` de la charge d'interruption (9.4) en collision avec le `type` de l'enveloppe d'événement
- **Décision** : La charge porte `kind` à la place
- **Raison** : évite l'ambiguïté entre le `type` de l'enveloppe d'événement et celui de la charge.

## D15

- **Date** : 2026-11-11
- **Sujet** : Reprise après Pause
- **Décision** : `POST /sessions/{id}/resume` avec `interrupt_id: null`
- **Raison** : réutilise l'endpoint de reprise existant au lieu d'en créer un second.

## D16

- **Date** : 2026-11-11
- **Sujet** : Sorties structurées
- **Décision** : JSON validé par Pydantic (2 nouveaux essais), sans `with_structured_output`, pour un comportement identique sur les 3 fournisseurs
- **Raison** : un comportement identique sur Anthropic, OpenAI et Ollama, sans dépendre des capacités propres à chaque fournisseur.

## D17

- **Date** : 2026-11-11
- **Sujet** : Page de démonstration de la phase 1
- **Décision** : Route `/demo` conservée hors navigation
- **Raison** : la phase 1 a besoin d'une page pour vérifier de bout en bout les composants de session, avant les vraies features.

## D18

- **Date** : 2026-11-11
- **Sujet** : Reprise des sessions au démarrage
- **Décision** : `list_sessions_to_recover` est la seule lecture sans filtre `user_id`, réservée au démarrage du back
- **Raison** : le démarrage du back doit reprendre les sessions de tous les utilisateurs ; c'est l'unique exception à la règle du filtre `user_id`, bornée et documentée.

## D19

- **Date** : 2026-11-11
- **Sujet** : Python du projet back
- **Décision** : le back est épinglé à Python 3.12 (`.python-version`, `requires-python = ">=3.12,<3.13"`), sans paquet installable (`[tool.uv] package = false`, code dans `backend/app/`, scripts dans `backend/scripts/`).
- **Raison** : le poste de développement a Python 3.14 alors que l'image Docker est `python:3.12-slim` ; l'épinglage garde les deux identiques. `uv init --package` aurait créé une disposition `src/` qui contredit l'arborescence cible.

## D20

- **Date** : 2026-11-11
- **Sujet** : Branche de travail et outils de qualité sous Windows
- **Décision** : le travail se fait sur la branche `dev` (le brief disait `main`). Les hooks pre-commit sont des hooks `local` en `language: system` qui passent par `uv run` ; pre-commit s'invoque via `uv run python -m pre_commit` car Windows bloque les exécutables `pre-commit.exe` et `mypy.exe` (stratégie de contrôle d'application). Le hook de longueur utilise `--project` au lieu de `--directory`, pour que les chemins transmis par pre-commit restent relatifs à la racine du dépôt. `asgi-lifespan` est ajouté aux dépendances de développement pour les clients de test des tâches suivantes.
- **Raison** : fiabilité des hooks dans l'environnement Windows + Git Bash réel de l'utilisatrice.

## D21

- **Date** : 2026-11-11
- **Sujet** : Règles ruff du back
- **Décision** : ruff avec `select = ["E", "F", "I", "UP", "B", "SIM"]` et `line-length = 100` (pycodestyle, pyflakes, tri des imports, pyupgrade, bugbear, simplifications).
- **Raison** : un jeu restreint et sans bruit qui attrape les vrais défauts (imports inutilisés, bugs probables, syntaxe obsolète) sans imposer de règles de style discutables ; à étendre seulement si un défaut récurrent le justifie.

## D22

- **Date** : 2026-11-11
- **Sujet** : Socle de données (tâche 0.3)
- **Décision** : (1) `created_at` / `updated_at` utilisent un `TypeDecorator` `UTCDateTime` (colonne `DateTime(timezone=True)`) qui restitue des datetimes UTC avec fuseau, car SQLite perd le fuseau à la lecture ; la migration 0001 écrit `sa.DateTime(timezone=True)` pour rester indépendante du code applicatif. (2) Les fixtures de test utilisent un vrai fichier `tmp_path/app.db` (schéma créé par `Base.metadata.create_all` avant le démarrage de l'app) plutôt qu'une base mémoire et un `get_db` surchargé : `client` et `db_session` voient les mêmes données. (3) `Settings.database_url` est une `str` (vide = calculée depuis `data_dir`), l'override `DATABASE_URL` reste valable. (4) `Base.metadata` porte une convention de nommage des contraintes (nécessaire au mode batch d'Alembic sur SQLite). (5) Aucune clé étrangère vers `users` pour l'instant : `user_id` est indexé mais non contraint (le filtre applicatif du repository est la garantie ; `User.user_id == User.id` rendrait une clé étrangère auto-référente sans valeur). (6) `User.email` et `google_sub` sont uniques et nullables (l'utilisateur local de la tâche 0.4 n'a pas d'e-mail ; SQLite autorise plusieurs NULL sous contrainte unique). (8) `get_db` doit être déclaré avec `Depends(get_db, scope="function")` (alias `Db` dans `app/core/deps.py`) : avec la portée « request » par défaut de FastAPI, le commit s'exécute après l'envoi de la réponse. (7) `alembic/env.py` lit `sqlalchemy.url` s'il est fixé (tests, scripts), sinon `get_settings().database_url`.
- **Raison** : lectures fidèles au contrat « UTC tz aware », tests plus proches de la production (WAL, connexions distinctes), migrations vérifiables par `compare_metadata`.

## D23

- **Date** : 2026-11-11
- **Sujet** : Utilisateur local et `get_current_user` (tâche 0.4)
- **Décision** : (1) `UserRepository` (table `users`) est l'exception au filtrage par `user_id` : il filtre par `id` (ou retrouve le compte local) et n'hérite pas de `UserScopedRepository`. (2) En mode `local`, le lifespan appelle `AuthService.ensure_local_user()` (idempotent, `name="local"`, sans e-mail ni `google_sub`) dans sa propre session, commite et mémorise l'id sur `app.state.local_user_id` ; si la table `users` manque, le démarrage échoue avec un message français (`alembic upgrade head`). (3) En mode `google`, `get_current_user` lève `auth_required` (401) tant que la connexion n'existe pas (phase 9) ; le lifespan ne crée alors aucun utilisateur. (4) Alias `CurrentUserDep` dans `app/core/deps.py` pour les routeurs. (5) Les tests de `get_db` (0.3) filtrent désormais sur leurs propres lignes, l'utilisateur local existant dès le démarrage.
- **Raison** : un utilisateur unique stable sans authentification en local, et un point d'extension net pour Google sans toucher aux features.

## D24

- **Date** : 2026-11-11
- **Sujet** : Secret, chiffrement et filtre de journaux (tâche 0.5)
- **Décision** : (1) `SecretUnreadable` hérite d'`AppError` (code `secret_unreadable`, 500, message français) ; elle est aussi levée si le fichier `secret.key` n'est pas une clé Fernet valide. (2) `load_or_create_secret` crée le dossier parent et le fichier de façon atomique (`O_EXCL`, `0o600`) ; sous Windows `chmod` est sans effet et les tests ne vérifient pas les droits. (3) `KnownSecrets` (registre de processus dans `security.py`, ignore les valeurs vides ou de moins de 8 caractères) alimente `configure_logging` ; le lifespan y ajoute les clés `.env` non vides. (4) `RedactingFilter` est posé sur les handlers (racine et uvicorn), pas sur des loggers, car un filtre de logger ne s'applique pas aux enregistrements propagés ; il masque aussi les traces d'exception (`exc_text`) et `stack_info`. `configure_logging` est idempotent (remplace le filtre existant, n'ajoute un handler que si la racine n'en a aucun). Le niveau est fixé à `INFO` dans `main.py` (pas de réglage dédié pour l'instant). (5) Le lifespan ne traduit en message « base non initialisée » que les `OperationalError` contenant « no such table » ; les autres sont relevées telles quelles.
- **Raison** : aucune clé ne doit sortir en clair dans les journaux, y compris via une exception ; et un verrou ou une base illisible ne doit pas être pris pour un oubli de migration.

## D25

- **Date** : 2026-11-11
- **Sujet** : Réglages utilisateur et identifiants de modèles (tâche 0.6)
- **Décision** : (1) Identifiants relevés le 2026-11-11 : Anthropic `claude-haiku-5-5` (rapide) et `claude-sonnet-5-5` (fort), confirmés par le contrôleur ; OpenAI `gpt-6-luna` (rapide, « most efficient model for focused, high-volume tasks »), `gpt-6.1-sol` (fort, « near-Astra performance at a lower cost »), `gpt-6.1-terra` (vision, « visual reasoning ») d'après developers.openai.com/api/docs/models ; GLM (Z.ai) `glm-4.7-flash` (rapide, texte, gratuit), `glm-5.3` (fort, texte), `glm-5.3-flash` (vision : entrée image/vidéo/texte) d'après docs.z.ai (aperçu, tarifs, guide `glm-5.3-flash`). Sources consultées via context7, pas directement sur les sites : **à vérifier** avant la première utilisation réelle de OpenAI et GLM. (2) `supports_vision` : tout `claude-*` ; OpenAI et GLM par listes explicites (OpenAI : `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6.1-terra` ; GLM : `glm-5.3-flash`, `glm-5.3-flashx`, `glm-4.6v`, `glm-4.6v-flash`, `glm-4.6v-flashx`, `glm-4.5v`) ; fournisseur ou modèle inconnu = pas de vision (on désactive plutôt que de casser). `gpt-6-luna`, `glm-4.7-flash` et `glm-5.3` sont donc traités comme sans vision. (3) Constante ajoutée `OPENAI_VISION` (absente du brief) pour que le préréglage « Tout OpenAI » ait un niveau vision valide. Préréglages : rapide et standard = modèle rapide, fort = modèle fort, vision = modèle vision (Haiku pour les deux préréglages Anthropic). (4) Lecture tolérante : les clés inconnues du stockage sont ignorées ; un champ stocké invalide retombe sur son défaut (un avertissement ne journalise que les noms de champs) ; si cela ne suffit pas, tous les défauts. (5) `tiers` reçu ou lu avec un niveau absent est complété par le défaut du niveau. (6) Les champs calculés (`weekly_budget_minutes`, `vision_enabled`) sont des `computed_field` renvoyés par l'API, jamais stockés ; un `PUT` accepte donc tel quel le corps d'un `GET` (champs en trop ignorés). (7) `UserSettingsRow.data` est une colonne JSON simple : le repository affecte toujours un nouveau dict. (8) `Field(default=...)` en mot-clé et `default_factory` en lambda : mypy est lancé sans le plugin pydantic. (9) `SettingsModelReader(session_factory)` ouvre sa propre session ; il n'est pas encore branché (la fabrique LLM arrive en 0.7, la composition ira dans `app/bootstrap.py`).
- **Raison** : valeurs par défaut de la spec respectées, lecture qui ne casse jamais l'accueil à cause d'une donnée ancienne, et identifiants centralisés dans `model_defaults.py`.

## D26

- **Date** : 2026-11-11
- **Sujet** : Fournisseurs LLM, fabrique `get_chat_model` et prix (tâche 0.7)
- **Décision** : (1) Contrat d'import : `app/providers/` n'importe jamais `app/features/` ; la fabrique ne dépend que des protocoles `ModelChoiceReader` et `KeyReader` (définis dans `base.py`), la composition avec la feature réglages ira dans `app/bootstrap.py` (tâche 0.8). (2) Vérification des clés et listes de modèles en `httpx` simple (`_http.py`), pas via les SDK `anthropic` / `openai` : ces SDK (versions installées) utilisent `httpx2` et refusent un client `httpx` ; `respx` n'intercepte donc pas leurs appels et un test aurait atteint le vrai réseau (constaté lors du développement, corrigé). Les modèles de chat restent `ChatAnthropic` / `ChatOpenAI` ; `build` fixe `timeout=120`, `max_retries=2`, `streaming=True`. (3) `test_key` ne lève jamais (réseau, délai, 401/403 « Clé refusée par {fournisseur}. », autre statut) et ne reprend jamais la clé ; `list_models` lève `AppError("llm_models_unavailable", …, 502)`. (4) GLM : pas d'API de liste documentée par Z.ai (`list_models` renvoie `None`, saisie libre) ; `test_key` fait un appel `max_tokens=1` sur `glm-4.7-flash` (gratuit). Adresse par défaut `https://api.z.ai/api/paas/v4/`, remplacée par `base_urls["glm"]` (`Settings.zai_base_url`) à la construction. L'adresse « coding » (`/api/coding/paas/v4`) consomme le quota du forfait Coding Plan : non utilisée. (5) `FakeLlmProvider` (code applicatif, `fake.py`) : petit modèle `BaseChatModel` maison plutôt que `GenericFakeChatModel`, qui ne conserve pas les messages reçus et ne renseigne pas `usage_metadata` en flux. Il diffuse mot par mot, met `usage_metadata` (nombre de mots) sur le dernier morceau, et lève `RuntimeError` quand les réponses prévues sont épuisées. Il garde aussi `base_urls` (assertions). (6) `LlmFactory` : `SecretUnreadable` devient `llm_key_unreadable` (details `{provider}` ajouté), une clé vide ou absente `llm_key_missing`, un fournisseur absent du registre `llm_provider_unknown` ; aucun message ni détail ne contient la clé. (7) Prix (`model_prices.json`, USD par million de tokens, relevé du 2026-11-11 ; palier ≤ 100 K tokens d'entrée pour Haiku, ≤ 272 K pour OpenAI, les paliers supérieurs coûtent plus cher et ne sont pas modélisés) : `claude-haiku-5-5` 0,10 / 0,50 et `claude-sonnet-5-5` 2 / 10 (skill claude-api, tableau du 2026-11-03) ; `gpt-6-luna` 0,10 / 0,50, `gpt-6.1-sol` 2 / 10, `gpt-6.1-terra` 1 / 5 (developers.openai.com, pages des modèles) ; `glm-4.7-flash` 0 / 0 (docs.z.ai, tarifs). **À vérifier** : `glm-5.3` (1,40 / 4,40) et `glm-5.3-flash` (0,47 / 1,47) sont des estimations, absentes de la page des tarifs Z.ai consultée : `glm-5.3` reprend le tarif de `glm-5.1`, `glm-5.3-flash` en applique le tiers (rapport des multiplicateurs de crédits du forfait équipe, 2,3 / 6,9 et 8 / 24). Z.ai et OpenAI vérifiés via context7, pas sur les sites directement ; le fichier est éditable à la main.
- **Raison** : respecter « aucun appel réseau réel en test », garder la fabrique indépendante des features, et des erreurs lisibles sans fuite de clé.

## D27

- **Date** : 2026-11-11
- **Sujet** : Clés API, test de clé, liste des modèles et composition (tâche 0.8)
- **Décision** : (1) `app/bootstrap.py` : `Providers` (dataclass modifiable) et `build_providers(settings, session_factory, cipher)` ; GLM y est construit avec `GlmProvider(base_url=settings.zai_base_url)` pour que le test de clé et la liste honorent une adresse Z.ai surchargée (retour de revue 0.7) ; `env_keys` = `{anthropic, openai, glm}` issus de `Settings`. Le lifespan stocke le résultat dans `app.state.providers` ; `get_providers`, `get_llm_factory`, `get_cipher` (`core/deps.py`) lisent `app.state`, `Providers` n'y est importé que pour le typage. Correctif de revue : le dataclass `Providers` (données seulement) vit dans `app/core/providers.py`, `bootstrap.py` ne garde que `build_providers` ; ni `app.features.*` ni `app.core.*` n'importent `app.bootstrap`. (2) Clé : espaces autour retirés avant stockage ; vide = 422 `invalid_key` « La clé est vide. » ; moins de 8 caractères = 422 `invalid_key` « La clé est trop courte. » (contrôle fait dans le service, pas dans le schéma, pour que le 422 de validation Pydantic ne recopie jamais la valeur saisie). Le brief utilisait `"ui-key"` (6 caractères) dans un test : le test utilise `"ui-key-123"`. (3) `list()` ne lève jamais : une clé de la base qui ne se déchiffre plus donne `readable=False` (source `ui`, `last4` conservé) ; sans clé, `readable=True`, `source=None`. Une clé de la base illisible n'est pas remplacée par celle du `.env` (la clé de l'interface reste prioritaire, `get_plaintext` lève `SecretUnreadable`). (4) `test` : fournisseur sans clé = `KeyTestResult(ok=False, "Aucune clé enregistrée pour {label}.")` ; clé illisible = `ok=False` avec le message de `SecretUnreadable` ; le résultat (`last_tested_at`, `last_test_ok`) n'est mémorisé que pour une clé de l'interface (une clé `.env` n'a pas de ligne) ; remplacer une clé remet ce résultat à vide. (5) `GET /settings/models` : `has_key` = une clé lisible existe (interface ou `.env`) ; `list_models` n'est appelé que dans ce cas ; toute exception d'un fournisseur donne `models: None` et un avertissement qui ne contient que le nom du fournisseur et le type d'erreur. (6) `DELETE` est idempotent (204 même sans clé). `DbKeyReader` ouvre sa propre session et partage la résolution (base puis `.env`) avec `ApiKeyService` ; toute valeur déchiffrée ou saisie va dans `KnownSecrets`.
- **Raison** : aucune fuite de clé (réponse, journal, erreur de validation), une page de réglages qui ne casse jamais à cause d'un secret régénéré ou d'un fournisseur en panne, et composition concentrée dans `bootstrap.py`.
- **Correctif de revue (D27 bis)** : le gestionnaire d'erreurs de validation (`core/errors.py`) ne renvoie plus que `loc`, `msg` et `type` pour chaque erreur (ni `input`, ni `ctx`), pour toutes les routes : `input` recopiait la valeur reçue (clé d'API, plus tard données personnelles). `models_overview` réutilise `list_models`.

## D28

- **Date** : 2026-11-11
- **Sujet** : Santé des services et `GET /api/v1/health` (tâche 0.9)
- **Décision** : (1) Routes de santé vérifiées dans la documentation (context7) : Qdrant `GET /readyz` (depuis 1.5.0, accessible même avec une clé d'API) ; Gotenberg `GET /health` (200 si Chromium et LibreOffice répondent, 503 sinon) ; SearXNG `GET /healthz` (route Flask de `searx/webapp.py`, texte « OK », exemptée du limiteur) : aucun écart avec le brief. SearXNG renvoie 403 pour un format absent de `search.formats` de `settings.yml` (page `search_api`). (2) `Providers` gagne `health_checks: list[HealthCheck]` (valeur par défaut : liste vide), rempli par `build_providers` : `db`, `qdrant`, `ollama`, `searxng`, `gotenberg`, `llm` (ces noms sont les clés de `HealthReport.checks`). `build_providers` reçoit en plus le client `httpx.AsyncClient` partagé (créé dans le lifespan avec un délai de 3 s, fermé à l'arrêt) et un appelant `local_user_id` (le lifespan lit `app.state.local_user_id` à chaque contrôle, car l'utilisateur local est créé après la composition). (3) `HealthStatus` et `HealthCheck` vivent dans `app/providers/health.py` (sans import de `app.features`) ; `DatabaseCheck` et `LlmKeysCheck` dans `app/features/health/checks.py`, qui appelle `ApiKeyService.list()` (service de la feature réglages uniquement). `LlmKeysCheck` : `ok` si une clé lisible existe pour l'utilisateur local ; sans utilisateur local (mode `google` avant la phase 9) il rapporte « Aucun utilisateur local. » et `ok=False`, donc un état « dégradé » permanent dans ce mode d'ici là. (4) Les sondes laissent remonter les exceptions réseau ; `HealthService` les convertit (« Délai dépassé » pour un délai, « Erreur : <type> » sinon, jamais le message), avec un plafond de 3 s par contrôle et exécution en parallèle ; un statut HTTP inattendu donne « Réponse inattendue : HTTP <code> ». `GET /api/v1/health` est toujours 200, sans authentification ni dépendance à la base de la requête. La dépendance `get_health_service` est dans le routeur de la feature (le brief citait `core/deps.py`, qui n'a pas à connaître une feature). (5) `SearxngProbe` : la vérification JSON n'est faite qu'une fois par instance de sonde, mémorisée après le premier succès seulement (un échec est retenté). Cette requête exécute une vraie recherche : si SearXNG met plus de 3 s à répondre, le contrôle affiche « Délai dépassé » et sera retenté. (6) `OllamaProbe` : le modèle est présent si un nom vaut `bge-m3` ou `bge-m3:<étiquette>` (pas `bge-m3-large`). **Reporté** : le pourcentage de téléchargement de `bge-m3` (spec 15.5) n'est pas exposé ici ; il relève de l'écran de premier lancement (phase 9), le détail se limite à « Le modèle bge-m3 est en cours de téléchargement. ».
- **Raison** : un état de santé fiable qui ne divulgue ni clé ni adresse, sans appel réseau en test, et une composition qui reste dans `app/bootstrap.py`.

## D29

- **Date** : 2026-11-11
- **Sujet** : Retours de revue de la tâche 0.9 (sonde SearXNG, fermeture du client HTTP)
- **Décision** : (1) La vérification JSON de `SearxngProbe` a son propre délai de 10 s (paramètre `timeout` de la requête, le client partagé reste à 3 s). Un contrôle peut désormais exposer un attribut `timeout` : `HealthService` utilise `max(plafond par défaut, timeout du contrôle)`, jamais moins que le plafond du service ; la sonde SearXNG demande 15 s (sonde `/healthz` + recherche). Choix le plus simple : pas de tâche de fond ni de cache. Conséquence assumée : tant que la vérification JSON n'a pas réussi, un `GET /health` peut durer jusqu'à 15 s (premier appel, ou SearXNG lent) ; après le premier succès il ne fait plus que `/healthz`. Le `HEALTHCHECK` Docker du back a donc un délai de 20 s. (2) Un 403 de la recherche dit : « Le format JSON est peut-être désactivé dans SearXNG, ou la requête a été bloquée par son limiteur. » (le limiteur est désactivé dans notre `settings.yml`). (3) Le lifespan crée le moteur et le client HTTP dans un `AsyncExitStack` : ils sont fermés même si `build_providers` ou le démarrage lève.
- **Raison** : une première recherche réelle ne doit pas être comptée comme un échec, et aucune ressource ne doit fuir si la composition échoue.
