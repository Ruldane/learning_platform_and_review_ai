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
- **Décision** : (1) `created_at` / `updated_at` utilisent un `TypeDecorator` `UTCDateTime` (colonne `DateTime(timezone=True)`) qui restitue des datetimes UTC avec fuseau, car SQLite perd le fuseau à la lecture ; la migration 0001 écrit `sa.DateTime(timezone=True)` pour rester indépendante du code applicatif. (2) Les fixtures de test utilisent un vrai fichier `tmp_path/app.db` (schéma créé par `Base.metadata.create_all` avant le démarrage de l'app) plutôt qu'une base mémoire et un `get_db` surchargé : `client` et `db_session` voient les mêmes données. (3) `Settings.database_url` est une `str` (vide = calculée depuis `data_dir`), l'override `DATABASE_URL` reste valable. (4) `Base.metadata` porte une convention de nommage des contraintes (nécessaire au mode batch d'Alembic sur SQLite). (5) Aucune clé étrangère vers `users` pour l'instant : `user_id` est indexé mais non contraint (le filtre applicatif du repository est la garantie ; `User.user_id == User.id` rendrait une clé étrangère auto-référente sans valeur). (6) `User.email` est unique et obligatoire, `google_sub` unique et nullable. (7) `alembic/env.py` lit `sqlalchemy.url` s'il est fixé (tests, scripts), sinon `get_settings().database_url`.
- **Raison** : lectures fidèles au contrat « UTC tz aware », tests plus proches de la production (WAL, connexions distinctes), migrations vérifiables par `compare_metadata`.
