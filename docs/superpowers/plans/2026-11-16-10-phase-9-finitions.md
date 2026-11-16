# Phase 9 — Finitions : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mode d'exécution déjà choisi : **subagent-driven en mode économie, trois flux en parallèle dans trois `git worktree`** (voir « Déroulement »).

**Goal:** Tremplin devient utilisable à plusieurs : avec `AUTH_MODE=google`, chacun se connecte par Google (code d'autorisation avec PKCE, portées `openid email profile`, cookie de session `HttpOnly` `SameSite=Lax` de 30 jours, liste `ALLOWED_EMAILS`), le premier compte peut reprendre l'espace `local`, et deux comptes ne voient jamais les données l'un de l'autre (un test par routeur). January peut exporter toutes ses données et tout supprimer. Les réglages avancés de F6 sont complets : surcharge du modèle agent par agent, écran des coûts (par jour, feature, agent, modèle), journal des agents, disponibilité, style. Un premier lancement en cinq étapes accueille un nouveau compte. Plus les correctifs d'ouverture laissés par la phase 8, un cinquième parcours de bout en bout, une recette complète de l'application et le README.

**Architecture:** Contrat d'abord : une tâche socle (9.P) fige **avant la fourche** la migration de la phase, les champs de configuration et de réglages, et **toutes** les routes nouvelles sous forme de bouchons 501 avec leurs schémas définitifs ; le contrat OpenAPI et `schema.d.ts` sont régénérés une fois, là. Puis trois flux indépendants dans trois arbres de travail : **A** (back : connexion Google derrière un port `OidcProvider`, authentificateur posé sur `app.state`, reprise de l'espace local, isolation, progression du modèle d'embeddings, README), **B** (back : correctifs d'ouverture, features `costs` et `account`, catalogue des agents et surcharge par agent), **C** (front : correctifs d'ouverture, portes de la coquille et feature `auth/`, features `costs/` et `account/`, pages de réglages, premier lancement). C code contre les types générés en 9.P et MSW. Une tâche d'intégration fusionne, régénère le contrat et lance toutes les suites.

**Tech Stack:** FastAPI (dépendances, `RedirectResponse`, `StreamingResponse`), httpx (échange du code, `MockTransport` en test), `cryptography.Fernet` (existant, témoins de connexion chiffrés), SQLAlchemy 2 + Alembic, `zipfile` (bibliothèque standard), LangGraph (`adelete_thread`) · React 19, React Router (mode data), TanStack Query v5, Recharts (existant), Vitest, Testing Library, MSW, Playwright (Edge). **Aucune dépendance nouvelle** (P2).

**Spec:** `SPEC.md` §11.2 (mode avancé : surcharge par agent), §11.4 (disponibilité, style, autres réglages), §11.5 (suivi des coûts), §13.1, 13.2 (`users`, `user_settings`, `api_keys`, `llm_calls`), §14.2 (« Réglages », « Connexion »), §14.3, §15.1 (Réglages : modèles et clés, disponibilité, style, coûts, journal des agents), §15.4, §15.5 (premier lancement), §16.2 (`.env.example`, README), §17 (F7 en entier), §18.1 (phase 9), §18.2 (3 parcours de bout en bout, faux fournisseur), §18.3 (F6, F7, critères transverses). Plan directeur : `docs/superpowers/plans/2026-11-11-00-plan-directeur.md` (§1, §2, §3, §5 « Phase 9 », §6). Bilan : `docs/superpowers/bilans/phase-8.md` (« Points laissés pour plus tard »). Décisions : D1, D8, D18, D23, D28, D91, D117, D160, D165, D173, D174.

## Global Constraints

Toutes celles du plan directeur et des plans des phases 4 à 8 s'appliquent. Rappel des plus exposées, puis celles de cette phase.

- **Séparation** : `frontend/` et `backend/` strictement séparés, seul lien `contracts/openapi.json` ; un dossier par feature des deux côtés, mêmes noms (`auth`, `costs`, `account` des deux côtés) ; **un dossier par composant front** (`.tsx`, `.test.tsx`, `index.ts`) ; `components/` présentationnel ; une feature front n'importe jamais une autre feature (elle appelle une route d'une autre zone par son propre `api.ts`) ; `shared/` n'importe jamais `features/`.
- **Extensibilité** : une feature = un dossier + une ligne dans `FEATURE_ROUTERS` / `app/registry.ts` ; un fournisseur = une interface dans `app/providers/<type>/base.py` + une implémentation + un faux ; les registres existants (`GRAPHS`, `ROUTE_ONLY`, `JOBS`, `ACTIVITY_SOURCES`, `AGENTS`) ne changent pas de forme. L'export et la suppression parcourent **toutes les tables qui ont `user_id`** (`Base.metadata`) : une table ajoutée demain est exportée et supprimée sans toucher à `account`.
- **Contrôles** : mypy --strict, ruff (100 colonnes), import-linter : **8 contrats** (le contrat 3 nomme en plus `app.providers.auth.google`, sans contrat de plus) ; `check_file_length` : **300 lignes par fichier, 50 par fonction** ; front : ESLint (boundaries), Prettier, `tsc --noEmit`, Vitest + Testing Library + MSW. `app/main.py` est à 283 lignes : la composition de l'authentification passe par `app/bootstrap.py` et une fonction de `features/auth/service`, `main.py` ne gagne que des appels d'une ligne.
- **Clés d'API** : jamais renvoyées au navigateur (4 derniers caractères), jamais journalisées, chiffrées avec `APP_SECRET` ; **jamais dans l'export** (colonne `encrypted_key` retirée). Ne jamais lire ni afficher `.env`, ne jamais le commiter.
- **Erreurs** : `{error: {code, message, details}}`, message en français ; **une 422 ne renvoie jamais l'entrée** (ni e-mail, ni texte de confirmation, ni nom d'agent, ni modèle) : `details.fields` nomme les champs, sans valeur.
- **Journaux (17.2)** : identifiants (utilisateur, session, appel), nombres, codes et durées. **Jamais** : un e-mail, un nom, un `sub` Google, un code d'autorisation, un `state`, un vérificateur PKCE, un jeton, un cookie, un `login_hint`, un nom de fichier exporté, le texte de confirmation. Chaque nouvelle zone a son test `test_*_never_logged`.
- **Sécurité (17.1, 17.2, 17.4)** : cookie de session `tremplin_session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, 30 jours, `Secure` quand l'adresse de retour est en `https` ; jeton aléatoire de 32 octets, **seul son SHA-256 est stocké** ; CORS limité à l'origine du front (existant, `allow_credentials=True`) ; aucune redirection vers une adresse reçue en paramètre.
- **Tests sans réseau ni LLM** : Google remplacé par `httpx.MockTransport` (tests unitaires) ou par le faux fournisseur OIDC `scripts/fake_oidc.py` (e2e, essais) ; modèles scriptés ; seuls les essais réels (9.S, 9.Q) touchent GLM.
- **Données de test** : identités fictives « Camille Exemple » (`camille.exemple@example.org`), « Dominique Exemple » (`dominique.exemple@example.org`), domaines `example.org` / `example.invalid`.
- **Commits** : par chemins explicites (jamais `git add -A`), hooks jamais sautés (`--no-verify` interdit), message terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Docker** : ne jamais toucher aux conteneurs d'autres projets ; les nôtres : `learning_career_platform-*`, `tremplin-e2e-*`, plus les jetables `learning_career_platform-check9-*` de cette phase.
- **Environnement (hôte Windows, Smart App Control)** : `pnpm.exe`, le Chromium de Playwright et le lanceur du venv sont bloqués.
  - Back : `export PATH="/c/Users/lnizz/AppData/Local/Temp/claude/067b840c899f61c0/a91604fb-91ab-4f51-9a74-7afaf8679755/scratchpad/uv-shim:$PATH"` puis `cd <arbre>/backend && uv run pytest <dossiers> -q`. Le remplaçant `uv` lance uv dans l'image du back ; il est rendu **compatible avec les arbres de travail** en 9.P (étape 0).
  - Front : depuis `<arbre>/frontend` : `node node_modules/vitest/vitest.mjs run <chemins>` ; lint et types depuis la racine de l'arbre : `node frontend/scripts/run-tool.mjs lint`, `node frontend/scripts/run-tool.mjs typecheck` ; génération des types : `node frontend/scripts/run-tool.mjs gen:api` ; contrôle : `node frontend/scripts/check-api-types.mjs`.
  - Playwright sur Edge : config temporaire **non commitée** `frontend/playwright.edge.config.ts` (`import base from "./playwright.config"; export default { ...base, use: { ...base.use, channel: "msedge" } };`), lancée par `node node_modules/@playwright/test/cli.js test -c playwright.edge.config.ts`, retirée ensuite.
  - Images : `docker build -t learning_career_platform-backend:latest backend` et `docker build -t learning_career_platform-frontend:latest frontend` (pas `docker compose build`), pile par `docker compose up -d --no-build`.
- **Suite back complète** (30 à 40 min) : jamais lancée par un implémenteur ; il lance les dossiers concernés. Elle tourne à l'intégration (9.I), en fond.

**À vérifier dans la documentation actuelle avant de coder (context7)**, écart noté dans la décision de la tâche : Google Identity, OpenID Connect (paramètres `code_challenge_method=S256`, `nonce`, `login_hint`, `prompt`, réponse du point `token`, revendications `iss`, `aud`, `exp`, `email_verified` ; OIDC Core §3.1.3.7 n° 6 : un jeton d'identité reçu directement du point `token` par TLS peut se passer de la vérification de signature) ; Starlette, `Response.set_cookie(samesite=…, max_age=…)` et `delete_cookie` ; LangGraph, `BaseCheckpointSaver.adelete_thread` ; Ollama, `POST /api/pull` en flux (`status`, `total`, `completed`) ; React Router, routes sœurs hors de la mise en page ; TanStack Query v5, `refetchInterval` en fonction.

## Review Focus

1. **Cookie de session anormal** (absent, falsifié, expiré, utilisateur supprimé, e-mail retiré d'`ALLOWED_EMAILS` après la connexion, WebSocket sans cookie) : 401 `auth_required` lisible, jamais une 500, jamais un autre compte. → 9.A2 `test_forged_cookie_is_401`, `test_expired_session_is_401`, `test_deleted_user_cookie_is_401`, `test_email_removed_from_allowlist_is_401`, 9.A3 `test_websocket_without_cookie_refused`.
2. **Retour de Google rejoué ou trafiqué** (`state` différent, témoin `tremplin_oauth` absent ou de plus de 10 min, code déjà utilisé, `error=access_denied`, e-mail non vérifié, `aud` ou `nonce` faux, Google en panne) : redirection vers `/connexion?erreur=<code>`, aucun compte créé, aucune donnée dans les journaux. → 9.A2 `test_state_mismatch_creates_nothing`, `test_stale_oauth_cookie_refused`, `test_access_denied_redirects`, `test_unverified_email_refused`, `test_wrong_nonce_refused`, `test_token_endpoint_down_is_readable`.
3. **Reprise de l'espace local disputée** (deux onglets qui reprennent en même temps ; un second compte Google ; reprise après un premier choix « espace vide ») : un seul compte possède l'espace local, jamais deux comptes fusionnés, jamais une reprise proposée deux fois. → 9.A3 `test_concurrent_claims_one_owner`, `test_second_account_never_offered_local`, `test_claim_after_fresh_choice_refused`.
4. **« Tout supprimer » interrompu ou concurrent** (Qdrant en panne, session d'agent en cours, autre compte présent, second appel) : rejouable jusqu'au bout, sessions annulées avant, **aucune ligne d'un autre compte touchée**, l'application reste utilisable en mode local. → 9.B5 `test_delete_keeps_other_user`, `test_delete_cancels_running_sessions`, `test_delete_vector_down_then_retry_completes`, `test_local_mode_usable_after_delete`.
5. **Réglages réécrits par une autre page** (un `PUT /settings` depuis Modèles, Recherche ou Étude qui oublie `onboarding_done` ou `agent_overrides` ; un 401 en cours de navigation) : le premier lancement ne revient jamais une fois fini, les surcharges ne se perdent pas, pas de boucle entre `/connexion` et la porte. → 9.B3 `test_onboarding_done_never_reset`, 9.C4 `buildUserSettings keeps onboarding_done and agent_overrides`, 9.C2 `a 401 mid-session leads once to /connexion`.

---

## Décisions préalables (P1 à P24, écrites dans les décisions des tâches)

- **P1. Contrat d'abord.** Toute la surface d'API de la phase est posée par 9.P (routes bouchons 501 `not_implemented`, schémas, docstrings et codes d'erreur définitifs) ; le contrat et `schema.d.ts` sont régénérés **là, une fois**, puis **une seconde fois à l'intégration** (9.I). Un flux ne change jamais la surface (ni chemin, ni schéma, ni docstring de route, ni `responses=`) : le hook `openapi-contract` le bloquerait. Si un flux ne peut faire autrement, il régénère `contracts/openapi.json` **et** `schema.d.ts` dans son commit, le dit dans son rapport, et l'intégration résout tout conflit sur ces deux fichiers **en les régénérant**, jamais à la main. Raison : C code contre de vrais types générés sans attendre A et B.
- **P2. Aucune dépendance nouvelle** (ni `pyproject.toml` côté dépendances, ni `uv.lock`, ni `package.json`) : le venv Docker et `node_modules` sont partagés entre les arbres. OIDC à la main avec httpx (aucune bibliothèque OAuth) ; zip par `zipfile`.
- **P3. Migration unique** `0015_auth.py` (`down_revision = "0014"`), écrite en 9.P : table `auth_sessions` et passage de `onboarding_done` à vrai pour les réglages déjà stockés. **Aucun flux n'écrit de migration** ; s'il le faut vraiment, l'intégration ajoute `0016` sur la tête unique. `uv run alembic heads` doit rendre une seule tête à l'intégration.
- **P4. Propriétaire unique de chaque fichier partagé** (tableau « Fichiers partagés » plus bas). Les décisions ne sont pas écrites dans `DECISIONS.md` par les flux : chaque flux écrit les siennes dans `docs/superpowers/decisions/phase-9-<A|B|C>.md`, numéros réservés ; 9.I les recopie dans l'ordre dans `DECISIONS.md` et retire les fragments.
- **P5. Port OIDC** `app/providers/auth/base.py` (`OidcProvider`, `OidcIdentity`, `OidcError`), implémentation `google.py` ; les adresses `authorize` et `token` et l'émetteur attendu viennent de la configuration (défauts de Google) pour que le **faux fournisseur** `scripts/fake_oidc.py` serve aux e2e et aux essais par le même code. Le jeton d'identité vient directement du point `token` par TLS : pas de vérification de signature (OIDC Core §3.1.3.7 n° 6), mais `iss`, `aud`, `exp`, `nonce` et `email_verified` contrôlés.
- **P6. Témoins** : `tremplin_oauth` (chiffré par `Cipher`, `{state, verifier, nonce}`, 10 min, `Path=/api/v1/auth/google`) et `tremplin_claim` (chiffré, `{sub, email, name}`, 10 min, même chemin) ; `tremplin_session` (jeton opaque, 30 jours, `Path=/`). Jeton : `secrets.token_urlsafe(32)` ; base : `sha256` hexadécimal. Durée fixe de 30 jours depuis la connexion (pas glissante).
- **P7. Authentificateur** : `app.core.deps` définit le protocole `Authenticator` ; `get_current_user` devient asynchrone et délègue à `app.state.authenticator` (local : l'utilisateur unique ; google : le cookie). `core` n'importe aucune feature. Les tests gardent `act_as` (surcharge de `get_current_user`).
- **P8. `ALLOWED_EMAILS`** : liste séparée par des virgules, comparée en minuscules sans espaces ; vide = tous. Contrôlée à la connexion **et** à chaque requête (retirer une adresse coupe l'accès dès la requête suivante).
- **P9. Reprise de l'espace local** : proposée **seulement au tout premier compte Google** (aucun `users.google_sub` encore) et seulement si l'utilisateur `local` existe. « Reprendre » **attache l'identité Google à la ligne `local`** (même `id`, donc aucune donnée déplacée : base, Qdrant, fichiers, points de reprise) ; « Espace vide » crée un nouvel utilisateur et l'espace local reste intact (visible en repassant `AUTH_MODE=local`). Raison : 17.1 sans réécrire une seule ligne de données.
- **P10. Adresses** : retour `GOOGLE_REDIRECT_URI` (défaut `http://localhost:8000/api/v1/auth/google/callback`, 17.1) ; après connexion, redirection vers `FRONTEND_URL` (défaut `http://localhost:5173`) : `/` (connecté), `/connexion/reprise` (choix), `/connexion?erreur=<code>` (échec). En mode Google, l'application s'ouvre par `localhost` (le cookie est posé sur `localhost`).
- **P11. Mode Google sans `GOOGLE_CLIENT_ID` ou `GOOGLE_CLIENT_SECRET`** : le back refuse de démarrer avec un message clair (comme la base non migrée). `/auth/google/*` en mode local : 404 `google_auth_disabled`.
- **P12. Santé en mode Google** : `/health` reste public ; le contrôle `llm` ne regarde que les clés de `.env` (« Mode Google : les clés de chaque compte se vérifient dans ses réglages. », `ok=True`) ; plus d'état dégradé permanent (D28 n° 3).
- **P13. Progression du modèle d'embeddings** (15.5, reporté par D28) : `GET /health/embedding` ; si `bge-m3` manque, le back lance **une seule fois par processus** un `POST /api/pull` en flux vers Ollama et garde en mémoire le dernier pourcentage ; public comme `/health`.
- **P14. Isolation (17.2)** : registre `tests/isolation/cases_*.py` (routeur → test qui prouve qu'un autre compte ne lit rien) et test garde qui échoue si un routeur de `FEATURE_ROUTERS` n'a pas de cas ; `health` exempté (aucune donnée d'utilisatrice) ; plus un test en vrai mode Google à deux cookies.
- **P15. Coûts (11.5)** : `GET /costs?days=` (7, 30 ou 90 jours locaux ; défaut 30), agrégés en Python à partir de `llm_calls` (fuseau de January) ; « feature » = graphe de la session (`llm_calls.graph`, vide = hors session) ; « modèle » = `fournisseur:modèle` ; jours sans appel présents à zéro ; coûts tels qu'enregistrés (prix de `model_prices.json` au moment de l'appel).
- **P16. Journal des agents** = `GET /costs/calls` : appels journalisés du plus récent au plus ancien (curseur `before` opaque `(created_at, id)`, 50 par page), filtres `agent` et `graph` ; aucun contenu de prompt (la table n'en a pas).
- **P17. Surcharge par agent (11.2, mode avancé)** : `GET /settings/agents` (agents de `AGENTS` hors `demo_*`, avec leur niveau) ; `PUT /settings` refuse un agent inconnu (422, `fields: ["agent_overrides"]`) ; un agent surchargé utilise son modèle quel que soit le niveau demandé (déjà vrai dans `SettingsModelReader`).
- **P18. Export** : `GET /account/export` rend un zip en flux : `manifest.json` (`format_version: 1`, date, `user_id`, nombre de lignes par table, nombre de fichiers), `tables/<table>.json` pour chaque table qui a `user_id` (hors `auth_sessions` ; `api_keys` sans `encrypted_key`), `files/<clé>` pour chaque fichier de `storage/<user_id>/`. Ni vecteurs (recalculables) ni points de reprise LangGraph. Nom : `tremplin-export-AAAAMMJJ.zip`.
- **P19. « Tout supprimer »** : `POST /account/delete {confirm: "SUPPRIMER"}`. Ordre rejouable : sessions actives annulées → vecteurs (`MemoryRepository.delete_user`) → fichiers (`FileStorage.delete_user`) → points de reprise des sessions → lignes de toutes les tables à `user_id` dans une transaction (enfants d'abord). Mode local : la ligne `users` reste (même `id`, l'application continue) ; mode Google : elle part aussi, avec les `auth_sessions`, et le cookie est effacé. Les clés de `.env` ne sont pas touchées.
- **P20. Premier lancement (15.5, 17.3)** : réglage `onboarding_done` (défaut faux, vrai pour les réglages existants par la migration) ; cinq étapes : **1** santé des services et progression de `bge-m3`, **2** « Ce qui sort de ta machine » (17.3), **3** clé d'API et test, **4** import du CV et du profil LinkedIn (peut être passé), **5** disponibilité, puis « Terminer ». L'étape de confidentialité vient avant la clé : la clé envoie les prompts au fournisseur. Le back ne remet **jamais** `onboarding_done` à faux.
- **P21. Coquille front** : `FeatureManifest` gagne `publicRoutes` (hors mise en page, sans porte) et `shell.gate` (composant qui enveloppe la mise en page, dans l'ordre de `FEATURES`) ; `auth` déclare la porte de connexion, `settings` celle du premier lancement. Un 401 `auth_required` de n'importe quel appel émet un événement de `shared/api/authEvents.ts` que la porte écoute. Le client envoie les cookies (`credentials: "include"`).
- **P22. Features front** : `auth/` (connexion, reprise, menu du compte), `costs/` (Coûts, Journal des agents, section Réglages), `account/` (Mes données), et dans `settings/` : Disponibilité et rythme, Style, surcharge par agent (Modèles et clés, « Mode avancé »), premier lancement (`/bienvenue`, il réutilise `ApiKeyForm` et `AvailabilityFields` de `settings`).
- **P23. Parcours de bout en bout n° 5** « connexion, reprise, premier lancement, isolation, export, suppression », avec sa propre config Playwright (`playwright.auth.config.ts`, back e2e en mode Google, faux fournisseur monté dans le même serveur). Raison : F7 de bout en bout sans toucher aux parcours 1 à 4 (mode local).
- **P24. Écarts à la spec** (à écrire dans les décisions) : routes hors 14.2 `POST /auth/google/claim`, `GET /health/embedding`, `GET /account/export`, `POST /account/delete`, `GET /costs/calls`, `GET /settings/agents`, `POST /projects/{id}/drafts` ; réglage `onboarding_done` ; configuration `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, `GOOGLE_ISSUER`, `GOOGLE_REDIRECT_URI`, `FRONTEND_URL` ; table `auth_sessions` (13.2 ne la liste pas) ; cinquième parcours e2e.

---

## Déroulement (mode économie, trois flux en parallèle)

- **Modèles** : implémentation par **Sonnet**, relecture par **Sonnet**. Tâche **simple** : une relecture, un tour de correction, pas de revérification. Tâche **complexe** : relecture, un tour de correction, revérification. **Opus high** seulement pour la revue finale (9.R). Jamais Fable.
- **Un seul écrivain par arbre de travail** à la fois. Les relecteurs (lecture seule) tournent en parallèle des écrivains, sur l'arbre du flux ; le tour de correction attend que l'implémenteur en cours de ce flux ait commité. Trois écrivains en même temps au plus (un par flux).
- **Avant la fourche** : 9.P (≈ 30 min), sur `dev`, dans l'arbre principal. Puis :

```bash
cd /c/Users/lnizz/Documents/learning_career_platform
git worktree add ../tremplin-wt/a -b phase9/a dev
git worktree add ../tremplin-wt/b -b phase9/b dev
git worktree add ../tremplin-wt/c -b phase9/c dev
# front de C : node_modules partagé par jonction (aucune dépendance nouvelle, P2)
cmd //c mklink /J "C:\Users\lnizz\Documents\tremplin-wt\c\frontend\node_modules" "C:\Users\lnizz\Documents\learning_career_platform\frontend\node_modules"
```

  Si la jonction gêne Vitest, copier `node_modules` (`robocopy … /E /NFL /NDL /NJH /NJS`). L'arbre principal ne reçoit **aucune écriture** pendant les flux.
- **Fenêtre de 5 h à 8 h** : 9.P puis les trois flux (≈ 2 h 30 chacun, revues comprises). Ensuite, sur le nouveau quota : 9.I, 9.E, 9.R, 9.S, 9.Q, 9.Z.
- **Décisions** : numéros réservés ci-dessous ; un flux écrit les siennes dans son fragment (P4) au format existant (Date, Sujet, Décision en points numérotés, Raison), les points P recopiés par la tâche qui les met en œuvre.
- Commits par chemins explicites, hooks jamais sautés, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Heure vérifiée par `date` avant chaque lancement d'agent.

| Ordre | Tâche | Flux | Revue | Décision |
| --- | --- | --- | --- | --- |
| 1 | 9.P Socle commun et contrat | — (sur `dev`) | complexe | D175 |
| 2a | 9.A1 Port OIDC, Google, faux fournisseur | A | complexe | D176 |
| 3a | 9.A2 Connexion, cookie de session, utilisateur courant | A | complexe | D177 |
| 4a | 9.A3 Reprise de l'espace local, déconnexion, mode Google partout | A | complexe | D178 |
| 5a | 9.A4 Isolation : un test par routeur | A | complexe | D179 |
| 6a | 9.A5 Progression de `bge-m3`, README, `.env.example`, Compose | A | simple | D180 |
| 2b | 9.B1 Correctifs d'ouverture (back) | B | simple | D181 |
| 3b | 9.B2 Rapport des coûts | B | simple | D182 |
| 4b | 9.B3 Journal des agents, catalogue, surcharge par agent | B | simple | D183 |
| 5b | 9.B4 Export de toutes les données | B | complexe | D184 |
| 6b | 9.B5 Tout supprimer | B | complexe | D185 |
| 2c | 9.C1 Correctifs d'ouverture (front) | C | simple | D186 |
| 3c | 9.C2 Coquille (portes, routes publiques, cookie) et feature `auth/` | C | complexe | D187 |
| 4c | 9.C3 Coûts et journal des agents | C | simple | D188 |
| 5c | 9.C4 Disponibilité et rythme, style, surcharge par agent | C | simple | D189 |
| 6c | 9.C5 Mes données (export, suppression) | C | simple | D190 |
| 7c | 9.C6 Premier lancement en 5 étapes | C | simple | D191 |
| 8 | 9.I Intégration (fusion, contrat, suites complètes) | contrôleur | — | D192 |
| 9 | 9.E Parcours de bout en bout n° 5 | back + front | simple | D193 |
| 10 | 9.R Revue finale et vague de correctifs | contrôleur | Opus high | D194 |
| 11 | 9.S Essai réel de fin de phase (`check_phase9`, pile jetable) | contrôleur | — | D195 |
| 12 | 9.Q Recette complète de l'application et vague de correctifs | contrôleur | Sonnet | D196 |
| 13 | 9.Z Bilan, tag `phase-9`, push | contrôleur | — | D197 |

Commandes de contrôle d'une tâche back (dans son arbre, shim sur le `PATH`) : `cd backend && uv run pytest <dossiers de la tâche> -q && uv run ruff check . && uv run ruff format --check . && uv run python -m mypy app && uv run python -c "from importlinter.cli import lint_imports_command; lint_imports_command()" && uv run python -m scripts.export_openapi --check && uv run python -m scripts.check_file_length`. Front : depuis `frontend/`, `node node_modules/vitest/vitest.mjs run <dossiers>`, puis depuis la racine de l'arbre `node frontend/scripts/run-tool.mjs lint` et `node frontend/scripts/run-tool.mjs typecheck`.

### Fichiers partagés et leur propriétaire

Aucun fichier n'est modifié par deux flux. Un fichier absent de ce tableau appartient au flux dont la tâche le nomme ; s'il en faut un autre, l'implémenteur s'arrête et le signale.

| Fichier ou zone | Propriétaire |
| --- | --- |
| `backend/alembic/versions/0015_auth.py`, `backend/app/db/models/accounts.py` | 9.P (puis personne) |
| `backend/app/features/registry.py`, `frontend/src/shared/api/schema.d.ts`, `contracts/openapi.json` | 9.P, puis 9.I (régénération) |
| `backend/app/config.py`, `backend/app/main.py`, `backend/app/bootstrap.py`, `backend/app/core/deps.py`, `backend/app/core/security.py`, `backend/app/core/providers.py` | A (9.P n'ajoute que les champs de `config.py`) |
| `backend/app/features/auth/**`, `backend/app/features/health/**`, `backend/app/providers/auth/**`, `backend/app/providers/embeddings/**` | A |
| `backend/pyproject.toml` (contrats d'import seulement), `.env.example`, `docker-compose.yml`, `README.md` | A |
| `backend/tests/e2e/server.py`, `backend/scripts/fake_oidc.py`, `backend/tests/isolation/{guard,cases_a,…}` | A |
| `backend/app/features/{settings,costs,account,projects}/**`, `backend/app/providers/storage/**`, `backend/app/agents/**`, `backend/app/db/engine.py`, `backend/scripts/check_phase8.py`, `backend/scripts/phase8_*.py`, `backend/tests/isolation/cases_b.py`, `backend/tests/support/**` | B |
| tout `frontend/**` (hors `schema.d.ts`), dont `frontend/src/app/**`, `frontend/src/shared/**`, `frontend/src/shared/i18n/**`, `frontend/e2e/daily.spec.ts` | C |
| `frontend/playwright.auth.config.ts`, `frontend/e2e/account.spec.ts` | 9.E |
| `DECISIONS.md`, plan directeur, `docs/superpowers/bilans/phase-9.md` | 9.I, puis 9.R, 9.S, 9.Q, 9.Z |
| `docs/superpowers/decisions/phase-9-A.md`, `-B.md`, `-C.md` | A, B, C (retirés par 9.I) |
| `backend/scripts/check_phase9.py`, `backend/scripts/phase9_*.py` | 9.S |
| `docs/superpowers/recette/phase-9.md` | 9.Q |

## Interfaces consommées (phases 0 à 8)

- Cœur : `AppError(code, message, status_code, details)`, `Db`, `CurrentUserDep`, `CurrentUser(id, email)`, `get_runtime`, `Cipher` (`encrypt`, `decrypt`), `KnownSecrets`, `UserScopedMixin`, `UTCDateTime`, `new_id`, `UserScopedRepository[M]`, `core.clock` (`user_zone`, `local_today`), `KeyLocks`, `register_error_handlers` (422 sans écho).
- Comptes : `User` (`email`, `name`, `google_sub`, `language` ; `user_id == id`), `UserRepository` (`get`, `get_local`, `add_local` ; exception D23), `AuthService.ensure_local_user`, `MeOut`.
- Réglages : `UserSettings`, `SettingsOut`, `SettingsService(db, user_id).get/replace`, `_parse_stored`, `SettingsModelReader.get_model_choice(user_id, tier, agent)` (surcharge déjà lue), `ApiKeyService`, `ModelsOut`, `ModelChoice`, `TIERS`, `AGENTS` / `AgentSpec(name, tier)`.
- Données : `Base.metadata`, `LlmCall` (`session_id`, `graph`, `agent`, `provider`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `cost_usd`, `estimated`, index `(user_id, created_at)`), `AgentSession`, `MemoryProviders` (`index: MemoryRepository` avec `delete_user`, `storage: FileStorage`), `SessionRunner.cancel(user_id, session_id)`, `open_checkpointer`, `thread_config`.
- Santé : `HealthCheck`, `HealthStatus`, `LlmKeysCheck`, `OllamaProbe`, `HealthService`.
- Projets : `SessionStarted`, `project_review` (brouillons à la validation, D165 n° 5), `ProjectsRuntime`.
- Tests back : `settings`, `app`, `client`, `client_google_mode`, `db_session_factory`, `act_as` (`tests/sessions_support.py`), `RecordingLauncher`, `ScriptedModels`, `fake_memory_providers`, `tests/e2e/server.py`, `scripts/phase8_common.py`, `scripts/phase8_rules.check_logs_8`.
- Front : `api`, `apiBaseUrl`, `unwrap`, `errorMessage`, `ApiError`, `t`, `FeatureManifest` (`shell.topbar`, `shell.overlay`), `NavEntry`, `FEATURES`, `ShellSlots`, `AppLayout`, `agentIdentity`, `AGENT_COLORS`, `EmptyState`, `LoadingState`, `ErrorState`, `InlineError`, `Button`, `fieldClass`, `useRun`, `RunFeed` ; settings : `ApiKeyForm`, `ModelField`, `ProviderSelect`, `TierModelTable`, `buildUserSettings` (`userSettings.ts`), `useSettings`, `useUpdateSettings`, `useModels` ; outillage `src/test/server.ts`, `queryWrapper.tsx`, `renderRoutes.tsx`, `headingOutline.ts`.

---

### Task 9.P : Socle commun et contrat (avant la fourche) — complexe

**Zone : back + contrat, sur `dev`.** Change le contrat (une fois).

**Files:**
- Create: `backend/alembic/versions/0015_auth.py`, `backend/app/features/auth/service/{__init__.py, cookies.py}` (le module `service.py` devient paquet, `AuthService` déplacé tel quel), `backend/app/features/costs/{__init__.py, router.py, schemas.py}`, `backend/app/features/account/{__init__.py, router.py, schemas.py}`, `backend/tests/test_phase9_contract.py`, `backend/tests/db/test_auth_migration.py`
- Modify: `backend/app/db/models/accounts.py` (`AuthSession`), `backend/app/config.py`, `backend/app/features/settings/schemas.py` (`onboarding_done`, `AgentOut`), `backend/app/features/settings/keys_router.py` (`GET /settings/agents`), `backend/app/features/auth/{router.py, schemas.py}`, `backend/app/features/health/{router.py, schemas.py}`, `backend/app/features/projects/router.py` (`POST /projects/{id}/drafts`), `backend/app/features/registry.py`, `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`

- [ ] **Step 0 (contrôleur) : remplaçant `uv` compatible avec les arbres de travail.** Dans `…/scratchpad/uv-shim/uv` : `ROOT=$(git rev-parse --show-toplevel)` au lieu du chemin fixe, monté sur `/repo`, et volume de venv `tremplin-devvenv` pour l'arbre principal, `tremplin-devvenv-$(basename "$ROOT")` pour un arbre de travail. Dans `uv.cmd` (hooks, lancés depuis la racine de l'arbre) : monter `%CD%` au lieu du chemin fixe, même règle de volume. Vérifier dans l'arbre principal : `uv run python -c "print(1)"` puis un commit à blanc refusé ou accepté normalement par les hooks. Ces fichiers ne sont pas versionnés.

**Interfaces:**
- Produces:

```python
# db/models/accounts.py
class AuthSession(UserScopedMixin, Base):   # table auth_sessions ; index (user_id)
    token_hash: str      # String(64), unique : sha256 hexadécimal du jeton du cookie
    expires_at: datetime # UTCDateTime

# config.py (Settings) : champs ajoutés
google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
google_token_url: str = "https://oauth2.googleapis.com/token"
google_issuer: str = "https://accounts.google.com"
google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
frontend_url: str = "http://localhost:5173"
session_days: int = Field(default=30, ge=1, le=90)

# features/auth/service/cookies.py
SESSION_COOKIE = "tremplin_session"; OAUTH_COOKIE = "tremplin_oauth"; CLAIM_COOKIE = "tremplin_claim"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"; OAUTH_COOKIE_SECONDS = 600
def clear_session_cookie(response: Response) -> None     # même Path=/ que la pose

# features/settings/schemas.py
class UserSettings: ...; onboarding_done: bool = False
class AgentOut(BaseModel): name: str; tier: Tier

# features/auth/schemas.py
class ClaimIn(BaseModel): choice: Literal["take_local", "fresh"]
# MeOut inchangé : id, email, name, auth_mode

# features/health/schemas.py
class EmbeddingProgress(BaseModel): model: str; present: bool; percent: int | None; detail: str

# features/costs/schemas.py
class CostTotals(BaseModel): calls: int; tokens_in: int; tokens_out: int; cost_usd: float; estimated_calls: int
class CostRow(CostTotals): key: str      # "2026-11-16" | graphe ("" = hors session) | agent ("" = aucun) | "glm:glm-5.3-flash"
class CostsReport(BaseModel): days: int; since: date; until: date; total: CostTotals
    by_day: list[CostRow]; by_feature: list[CostRow]; by_agent: list[CostRow]; by_model: list[CostRow]
class AgentCallOut(BaseModel): id: str; at: datetime; session_id: str | None; graph: str | None
    agent: str | None; provider: str; model: str; tokens_in: int; tokens_out: int
    latency_ms: int; cost_usd: float; estimated: bool
class AgentCallPage(BaseModel): items: list[AgentCallOut]; next_before: str | None

# features/account/schemas.py
DELETE_CONFIRMATION = "SUPPRIMER"
class DeleteAccountIn(BaseModel): confirm: str = Field(max_length=32)
```

```text
GET  /auth/google/login?login_hint=      → 302 vers Google ; 404 google_auth_disabled (mode local)
GET  /auth/google/callback?code=&state=&error=   → 302 vers FRONTEND_URL (/, /connexion/reprise, /connexion?erreur=…)
POST /auth/google/claim  ClaimIn         → MeOut + cookie ; 409 claim_expired ; 409 local_already_claimed
POST /auth/logout                        → 204 (cookie effacé ; mode local : 204 sans effet)
GET  /auth/me                            → MeOut ; 401 auth_required (mode Google sans session)
GET  /health/embedding                   → EmbeddingProgress (public)
GET  /costs?days=30                      → CostsReport ; days ∈ {7, 30, 90}, sinon 422 fields ["days"]
GET  /costs/calls?before=&limit=50&agent=&graph=   → AgentCallPage ; limit 1..100 ; 422 fields ["before"] si curseur illisible
GET  /settings/agents                    → list[AgentOut]
GET  /account/export                     → 200 application/zip (Content-Disposition attachment)
POST /account/delete  DeleteAccountIn    → 204 ; 422 confirmation_required (fields ["confirm"])
POST /projects/{id}/drafts               → 202 SessionStarted ; 409 project_not_validated ; 409 drafts_present ; 409 review_in_progress
```

Routes bouchons : chaque nouvelle route lève `AppError("not_implemented", "Pas encore disponible.", 501)` après validation de l'entrée ; docstrings et `responses=` **définitifs** (P1). `GET /auth/google/login` et `/callback` déclarés avec `response_class=RedirectResponse`, `status_code=302` ; `/account/export` avec `responses={200: {"content": {"application/zip": {}}}}`.

Migration `0015` : création de `auth_sessions` ; `UPDATE user_settings SET data = json_set(data, '$.onboarding_done', json('true'))` ; `downgrade` retire la table (le drapeau reste, sans effet).

- [ ] **Step 1: Write the failing tests**

```python
async def test_migration_creates_auth_sessions(alembic_db): ...      # table, unique token_hash, index user_id
async def test_migration_marks_existing_settings_onboarded(alembic_db): ...   # ligne stockée avant 0015 : vrai après
def test_onboarding_done_defaults_false(): assert UserSettings().onboarding_done is False
@pytest.mark.parametrize("method,path", NEW_ROUTES)   # les 11 routes nouvelles du tableau (/auth/me existe déjà)
async def test_new_route_is_a_501_stub(client, method, path): ...
def test_contract_lists_phase9_paths(): ...            # contracts/openapi.json contient chaque chemin du tableau
```

- [ ] **Step 2: Run them, check they fail** — `cd backend && uv run pytest tests/test_phase9_contract.py tests/db/test_auth_migration.py -q`.
- [ ] **Step 3: Implement** les modèles, la migration, la configuration, les schémas et les bouchons ; `account_router` et `costs_router` ajoutés à `FEATURE_ROUTERS` (après `projects_router`).
- [ ] **Step 4: Regenerate and check** — `cd backend && uv run python -m scripts.export_openapi`, puis `node frontend/scripts/run-tool.mjs gen:api`, `node frontend/scripts/check-api-types.mjs`, `uv run alembic heads` (une tête : `0015`), tests de l'étape 1 et `tests/features/{auth,settings,health,projects}` verts, commandes de contrôle back, `node frontend/scripts/run-tool.mjs typecheck`.
- [ ] **Step 5: Commit** `feat(phase-9): socle commun et contrat des finitions (9.P)` ; D175 (P1 à P4, P24) dans `DECISIONS.md`. Puis créer les trois arbres (« Déroulement »).

---

## Flux A — Connexion Google et isolation (arbre `../tremplin-wt/a`, branche `phase9/a`)

### Task 9.A1 : Port OIDC, fournisseur Google, faux fournisseur — complexe

**Files:**
- Create: `backend/app/providers/auth/{__init__.py, base.py, google.py, pkce.py}`, `backend/scripts/fake_oidc.py`
- Modify: `backend/pyproject.toml` (contrat 3 : `app.providers.auth.google`)
- Test: `backend/tests/providers/auth/{test_pkce.py, test_google.py}`, `backend/tests/scripts/test_fake_oidc.py`

**Interfaces:**
- Produces:

```python
# providers/auth/base.py
@dataclass(frozen=True) class OidcIdentity: sub: str; email: str; email_verified: bool; name: str
class OidcError(Exception):   # code : "access_denied" | "google_unavailable" | "token_invalid"
    def __init__(self, code: str) -> None
class OidcProvider(Protocol):
    def authorization_url(self, *, state: str, code_challenge: str, nonce: str,
                          login_hint: str | None) -> str
    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> OidcIdentity

# providers/auth/pkce.py
def new_verifier() -> str            # secrets.token_urlsafe(64), 43 à 128 caractères
def challenge(verifier: str) -> str  # base64url(sha256(verifier)) sans « = »

# providers/auth/google.py
class GoogleOidc:
    def __init__(self, *, client_id: str, client_secret: str, auth_url: str, token_url: str,
                 issuer: str, redirect_uri: str, http: httpx.AsyncClient) -> None
    # authorization_url : response_type=code, scope="openid email profile",
    #   code_challenge_method=S256, prompt="select_account", login_hint si fourni
    # exchange : POST token_url (grant_type=authorization_code, code, redirect_uri, client_id,
    #   client_secret, code_verifier) ; délai 10 s ; réseau ou 5xx → google_unavailable ;
    #   4xx ou id_token absent → token_invalid ; revendications : iss ∈ {issuer, issuer sans
    #   « https:// »}, aud == client_id, exp > maintenant, nonce égal, email présent ;
    #   email_verified rendu tel quel (refus décidé par le service, 9.A2)

# scripts/fake_oidc.py
def create_fake_oidc_app(*, issuer: str, client_id: str,
                         default_email: str = "camille.exemple@example.org") -> FastAPI
    # GET /authorize : vérifie client_id, code_challenge_method=S256 ; e-mail = login_hint ou défaut ;
    #   ?deny=1 → redirect_uri?error=access_denied&state= ; sinon redirect_uri?code=<aléa>&state=
    # POST /token : code à usage unique, S256(code_verifier) == challenge, client_id ;
    #   id_token = JWT non signé (en-tête {"alg": "none"}) : iss, aud, exp (+1 h), nonce, sub =
    #   "fake-" + sha256(email)[:16], email, email_verified (faux si l'e-mail commence par
    #   « unverified »), name
# python -m scripts.fake_oidc --port 8099 --issuer … --client-id …  (uvicorn, 127.0.0.1 par défaut)
```

- [ ] **Step 1: Write the failing tests**

```python
def test_challenge_matches_rfc7636_example():
    assert challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGZh0eIHU0"
def test_authorization_url_has_pkce_scope_and_hint(): ...   # scope « openid email profile », S256, state, nonce
async def test_exchange_returns_identity(): ...             # MockTransport : id_token valide
async def test_wrong_audience_is_token_invalid(): ...
async def test_wrong_nonce_is_token_invalid(): ...
async def test_expired_id_token_is_token_invalid(): ...
async def test_token_endpoint_500_is_google_unavailable(): ...
async def test_token_endpoint_timeout_is_google_unavailable(): ...
async def test_fake_oidc_full_round_trip(): ...             # authorize → token avec le bon vérificateur : identité
async def test_fake_oidc_code_single_use(): ...
async def test_fake_oidc_rejects_wrong_verifier(): ...
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/providers/auth tests/scripts/test_fake_oidc.py -q`, commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): port OIDC, Google et faux fournisseur (9.A1)` ; D176 (P2, P5) dans `docs/superpowers/decisions/phase-9-A.md`.

---

### Task 9.A2 : Connexion, cookie de session, utilisateur courant — complexe

**Files:**
- Create: `backend/app/features/auth/repository_sessions.py` (`AuthSessionRepository`, exception D23 : filtre par `token_hash`), `backend/app/features/auth/service/{login.py, sessions.py, authenticator.py, allowlist.py}`
- Modify: `backend/app/core/deps.py` (`Authenticator`, `get_current_user` asynchrone), `backend/app/core/security.py` (`Cipher.decrypt(token, *, ttl: int | None = None)`), `backend/app/core/providers.py` (`Providers.oidc: OidcProvider | None`), `backend/app/bootstrap.py` (construit `GoogleOidc` en mode Google), `backend/app/main.py` (`app.state.authenticator`, refus de démarrer sans identifiants, P11), `backend/app/features/auth/router.py` (corps de `login` et `callback`)
- Test: `backend/tests/features/auth/{conftest.py, test_login.py, test_callback.py, test_sessions.py, test_authenticator.py, test_logs.py}`

**Interfaces:**
- Consumes: `OidcProvider`, `pkce`, `cookies.py`, `AuthSession`, `UserRepository`.
- Produces:

```python
# core/deps.py
class Authenticator(Protocol):
    async def authenticate(self, conn: HTTPConnection) -> CurrentUser   # lève AppError 401 auth_required
async def get_current_user(conn: HTTPConnection) -> CurrentUser          # délègue à app.state.authenticator

# features/auth/service/authenticator.py
class LocalAuthenticator:  def __init__(self, user_id: str) -> None
class CookieAuthenticator: def __init__(self, session_factory, settings: Settings, now: Callable[[], datetime]) -> None
    # cookie → sha256 → AuthSession non expirée → User → e-mail autorisé (P8) → CurrentUser
def build_authenticator(settings, session_factory, local_user_id: str | None) -> Authenticator

# features/auth/service/allowlist.py
def allowed(email: str, raw: str | None) -> bool

# features/auth/service/sessions.py
async def open_session(db, user_id: str, *, now: datetime, days: int) -> str   # jeton ; purge les sessions expirées de l'utilisatrice
async def close_session(db, token: str) -> None

# features/auth/service/login.py
@dataclass(frozen=True) class CallbackOutcome: kind: Literal["signed_in", "claim", "error"]
    token: str | None; claim_cookie: str | None; error: str | None
def start_login(oidc, cipher, login_hint: str | None) -> tuple[str, str]   # (adresse Google, valeur du témoin oauth)
async def finish_login(db, oidc, cipher, settings, *, code, state, error, oauth_cookie, now) -> CallbackOutcome
    # codes d'erreur : access_denied, state_invalid, google_unavailable, token_invalid,
    #   email_unverified, email_not_allowed
    # utilisateur trouvé par google_sub (e-mail et nom mis à jour) ; sinon, reprise proposée (9.A3)
    #   ou création (id == user_id, e-mail en minuscules)
```

Règles : `callback` rend toujours une 302 (jamais une page d'erreur JSON) ; le témoin `tremplin_oauth` est effacé dans tous les cas ; `state` comparé par `secrets.compare_digest` ; `login_hint` validé comme e-mail (≤ 320) sinon ignoré ; aucun paramètre d'adresse de retour accepté (P10).

- [ ] **Step 1: Write the failing tests**

```python
async def test_login_redirects_with_pkce_and_sets_oauth_cookie(google_client): ...   # 302, Location sur auth_url, témoin HttpOnly
async def test_login_in_local_mode_is_404(client): ...                                # google_auth_disabled
async def test_callback_signs_in_and_sets_30_day_cookie(google_client):
    r = await sign_in(google_client, "camille.exemple@example.org")
    cookie = r.cookies_header("tremplin_session")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie.lower() and "Max-Age=2592000" in cookie
    assert r.headers["location"] == "http://localhost:5173/"
async def test_me_with_cookie_returns_google_user(google_client): ...
async def test_state_mismatch_creates_nothing(google_client): ...       # /connexion?erreur=state_invalid ; 0 ligne users
async def test_stale_oauth_cookie_refused(google_client): ...           # témoin de 11 min : state_invalid
async def test_access_denied_redirects(google_client): ...
async def test_unverified_email_refused(google_client): ...
async def test_wrong_nonce_refused(google_client): ...                  # token_invalid
async def test_token_endpoint_down_is_readable(google_client): ...      # google_unavailable
async def test_email_not_allowed_creates_nothing(google_client): ...
async def test_forged_cookie_is_401(google_client): ...
async def test_expired_session_is_401(google_client): ...
async def test_deleted_user_cookie_is_401(google_client): ...
async def test_email_removed_from_allowlist_is_401(google_client): ...
async def test_returning_user_matched_by_sub_updates_email(google_client): ...
async def test_only_hash_of_token_stored(google_client): ...            # le jeton du cookie n'est nulle part en base
async def test_google_mode_without_client_id_refuses_to_start(settings): ...
async def test_auth_never_logged(caplog, google_client): ...            # e-mail, sub, code, state, vérificateur, jeton absents
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/auth tests/core -q`, plus `tests/features/sessions tests/realtime` (dépendance devenue asynchrone), commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): connexion Google et cookie de session (9.A2)` ; D177 (P5 à P8, P10, P11).

---

### Task 9.A3 : Reprise de l'espace local, déconnexion, mode Google partout — complexe

**Files:**
- Create: `backend/app/features/auth/service/claim.py`
- Modify: `backend/app/features/auth/{router.py, repository.py}` (`claim`, `logout`), `backend/app/features/health/checks.py` (P12), `backend/tests/e2e/server.py` (option `--auth google` : faux fournisseur monté sous `/fake-oidc`, adresses Google pointées dessus, docstring de tête corrigée, mineur du bilan 8)
- Test: `backend/tests/features/auth/{test_claim.py, test_logout.py}`, `backend/tests/features/health/test_google_mode.py`, `backend/tests/realtime/test_ws_auth.py`, `backend/tests/e2e/test_server.py`

**Interfaces:**
- Produces:

```python
# features/auth/service/claim.py
async def claim_offered(db) -> bool                 # aucun users.google_sub ET utilisatrice `local` présente
async def claim(db, cipher, claim_cookie: str | None, choice: Literal["take_local", "fresh"], *,
                now: datetime) -> User
    # take_local : UPDATE users SET google_sub, email, name WHERE id = local.id AND google_sub IS NULL
    #   (conditionnel : 0 ligne → 409 local_already_claimed) ; fresh : nouvel utilisateur ;
    #   témoin absent ou de plus de 10 min → 409 claim_expired ; une reprise déjà faite → plus jamais proposée
# UserRepository gagne : any_google_user() -> bool ; attach_identity(user_id, sub, email, name) -> bool
```

`finish_login` (9.A2) rend `kind="claim"` quand l'identité est nouvelle et `claim_offered` ; le callback pose `tremplin_claim` et redirige vers `/connexion/reprise`. `POST /auth/google/claim` ouvre la session (cookie) et rend `MeOut`. `POST /auth/logout` ferme la session et efface le cookie. En mode Google, le planificateur, la reprise des sessions au démarrage et la santé ne dépendent plus de `local_user_id`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_first_google_account_offered_local(google_client_with_local_data): ...   # 302 /connexion/reprise
async def test_take_local_keeps_same_id_and_data(google_client_with_local_data):
    me = await claim(google_client, "take_local")
    assert me["id"] == local_id and (await goals_of(google_client))  # objectif de l'espace local visible
async def test_fresh_leaves_local_untouched(...): ...
async def test_concurrent_claims_one_owner(...): ...         # deux reprises simultanées : 200 et 409 local_already_claimed
async def test_second_account_never_offered_local(...): ...
async def test_claim_after_fresh_choice_refused(...): ...
async def test_claim_without_cookie_is_409(...): ...         # claim_expired
async def test_logout_clears_cookie_and_session(...): ...    # me → 401 ensuite, ligne auth_sessions retirée
async def test_logout_local_mode_is_noop(client): ...
async def test_websocket_without_cookie_refused(google_client): ...
async def test_websocket_with_cookie_streams(google_client): ...
async def test_health_llm_ok_in_google_mode(google_client): ...   # plus « Aucun utilisateur local. »
async def test_e2e_server_google_mode_round_trip(): ...       # serveur e2e --auth google : login → faux fournisseur → cookie
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/auth tests/features/health tests/realtime tests/e2e/test_server.py -q`, commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): reprise de l'espace local et mode Google partout (9.A3)` ; D178 (P9, P12).

---

### Task 9.A4 : Isolation : un test par routeur — complexe

**Files:**
- Create: `backend/tests/isolation/{__init__.py, conftest.py, guard_support.py, test_guard.py, cases_a.py, test_cross_user_<zone>.py (un fichier par zone sans test existant), test_google_two_accounts.py}`
- Test: les mêmes

**Interfaces:**
- Produces:

```python
# tests/isolation/guard_support.py
def router_id(router: APIRouter) -> str          # module de l'endpoint de sa première route, ex. "app.features.cv.router.profile"
def load_cases() -> dict[str, str]               # fusion des CASES de tests/isolation/cases_*.py :
    # chaque module définit `CASES: dict[str, str]` (identifiant du routeur → nodeid
    # "tests/…/test_x.py::test_name"), sans rien importer d'autre ; deux modules qui nomment le
    # même routeur font échouer le chargement
EXEMPT: dict[str, str] = {"app.features.health.router": "aucune donnée d'utilisatrice"}
```

Inventaire d'abord (`grep` des tests `other_user`, `act_as`) : un cas existant est **référencé**, pas réécrit ; un routeur sans test reçoit le sien dans `test_cross_user_<zone>.py` (deux utilisateurs par `act_as`, une donnée créée par le premier ; le second reçoit 404 sur l'objet, une liste vide, ou ses propres valeurs pour les réglages et les clés). Les routeurs `costs` et `account` ont leurs cas dans `cases_b.py` (flux B, écrit en 9.B2) : **dans l'arbre A, le test garde échoue exactement sur ces deux routeurs** ; il passe après la fusion (vérifié en 9.I).

- [ ] **Step 1: Write the failing tests**

```python
def test_every_router_has_isolation_case():
    missing = {router_id(r) for r in FEATURE_ROUTERS} - load_cases().keys() - EXEMPT.keys()
    assert missing == set()
def test_every_case_points_to_an_existing_test(): ...   # module importable, fonction présente
async def test_google_two_accounts_never_see_each_other(google_client_factory):
    # Camille et Dominique par le faux fournisseur (MockTransport) : objectif, élément de mémoire,
    # capture, offre, réglages (style), clés (4 derniers caractères) de Camille absents chez Dominique ;
    # 404 sur l'id d'un objet de Camille ; WebSocket d'une session de Camille refusé à Dominique
```

- [ ] **Step 2: Run them** — `uv run pytest tests/isolation -q` : `missing` doit valoir `{"app.features.costs.router", "app.features.account.router"}` à la fin de la tâche, rien d'autre.
- [ ] **Step 3–4:** cas manquants écrits, pass (hors ces deux-là) ; commandes de contrôle.
- [ ] **Step 5: Commit** `test(phase-9): isolation des comptes, un test par routeur (9.A4)` ; D179 (P14).

---

### Task 9.A5 : Progression de `bge-m3`, README, `.env.example`, Compose — simple

**Files:**
- Create: `backend/app/providers/embeddings/ollama_pull.py`
- Modify: `backend/app/features/health/router.py` (corps de `GET /health/embedding`), `backend/app/bootstrap.py` (sonde de téléchargement sur `Providers`), `backend/app/core/providers.py`, `README.md`, `.env.example`, `docker-compose.yml` (passe `AUTH_MODE`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAILS`, `FRONTEND_URL`, `GOOGLE_REDIRECT_URI` au back, défauts vides)
- Test: `backend/tests/providers/embeddings/test_ollama_pull.py`, `backend/tests/features/health/test_embedding.py`, `backend/tests/test_readme.py`

**Interfaces:**

```python
class OllamaPullWatcher:
    def __init__(self, url: str, model: str, http: httpx.AsyncClient) -> None
    async def progress(self) -> EmbeddingProgressData   # présent (api/tags) → percent 100 ; sinon lance
        # une fois une tâche qui lit POST /api/pull {"name": model, "stream": true} et garde
        # completed/total (arrondi, 0..99) ; Ollama injoignable → present False, percent None,
        # detail « Ollama ne répond pas. »
@dataclass(frozen=True) class EmbeddingProgressData: model: str; present: bool; percent: int | None; detail: str
```

README (français) : démarrage (`docker compose up`, une seule clé dans `.env`), premier lancement, mode Google pas à pas (projet Google Cloud, écran de consentement, client « Application Web », origine `http://localhost:5173`, adresse de retour `http://localhost:8000/api/v1/auth/google/callback`, variables, `ALLOWED_EMAILS`, ouvrir par `localhost`), reprise de l'espace local, export et « Tout supprimer », ce qui sort de la machine (17.3), coûts, contrôles de qualité, parcours de bout en bout, mise à jour depuis une version précédente (`alembic upgrade head` à l'entrée du conteneur).

- [ ] **Step 1: Write the failing tests** — `test_progress_reports_percent_from_stream`, `test_pull_started_once_for_concurrent_calls`, `test_present_model_is_100`, `test_ollama_down_is_readable`, `test_embedding_route_public_in_google_mode`, `test_readme_lists_every_env_var_of_env_example` (chaque variable de `.env.example` citée dans le README), `test_env_example_has_no_value_for_secrets`.
- [ ] **Step 2–4:** fail, implement, pass ; commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): progression de bge-m3 et README (9.A5)` ; D180 (P13).

---

## Flux B — Données, coûts et correctifs (arbre `../tremplin-wt/b`, branche `phase9/b`)

### Task 9.B1 : Correctifs d'ouverture (back) — simple

**Files:**
- Modify: `backend/scripts/check_phase8.py`, `backend/scripts/phase8_common.py` (partie `journaux` seule), `backend/app/features/projects/{router.py (corps de POST /drafts), service/drafts.py}`, le graphe `project_review` et son entrée (`mode: Literal["review", "drafts"]`), `backend/app/db/engine.py` (si la cause des `ERROR sqlalchemy.pool` est là)
- Test: `backend/tests/scripts/test_check_phase8*.py`, `backend/tests/features/projects/test_regenerate_drafts.py`, `backend/tests/agents/graphs/test_project_review.py`, `backend/tests/db/test_engine.py`

Points :
1. **Journaux après l'essai** : `check_phase8 --part journaux` seul (lit l'entrée standard, mêmes motifs), à lancer **après** l'essai par `docker compose logs --since <début> backend | docker run … --part journaux --logs-file -` ; l'aide du script le dit.
2. **Brouillons d'un projet validé sans brouillons** : `POST /projects/{id}/drafts` relance `project_review` en mode `drafts` (aucune réévaluation, un appel standard + un nouvel essai au plus, `text_claims` comme D165) ; 409 `project_not_validated`, `drafts_present`, `review_in_progress`. Si le modèle d'entrée du graphe figure au contrat, le champ `mode` (défaut `"review"`) le change : régénérer les deux fichiers dans ce commit (P1) et le dire au contrôleur.
3. **`ERROR sqlalchemy.pool … Exception terminating connection`** (aiosqlite à la fermeture) : cause cherchée (superpowers:systematic-debugging, 30 min au plus) ; corrigée avec un test qui la reproduit, sinon décrite dans D181 et parquée.
4. **Mineurs back parqués de 8.9 et 8.10** (bilan phase 8) : test de reprise autour de `redo` ; garde sur `found` vide à la reprise ; JPEG nu de 4 octets refusé. Les autres restent parqués. A-M8 : si son détail n'est pas retrouvé dans les rapports de revue de la phase 8, il est noté parqué.

- [ ] **Step 1: Write the failing tests** — `test_journaux_part_alone_reads_stdin`, `test_regenerate_drafts_202_then_four_drafts`, `test_regenerate_drafts_refused_when_present`, `test_regenerate_drafts_refused_not_validated`, `test_drafts_mode_does_not_reevaluate`, `test_redo_resume_after_restart`, `test_bare_jpeg_header_refused`, (si reproduit) `test_engine_dispose_no_pool_error`.
- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/scripts tests/features/projects tests/agents/graphs/test_project_review.py tests/db -q` ; commandes de contrôle.
- [ ] **Step 5: Commit** `fix(phase-9): correctifs d'ouverture du back (9.B1)` ; D181 dans `docs/superpowers/decisions/phase-9-B.md`.

---

### Task 9.B2 : Rapport des coûts — simple

**Files:**
- Create: `backend/app/features/costs/{repository.py, service/__init__.py, service/report.py, service/rules.py}`, `backend/tests/isolation/cases_b.py`
- Modify: `backend/app/features/costs/router.py` (corps de `GET /costs`)
- Test: `backend/tests/features/costs/{test_rules.py, test_report.py, test_router.py}`

**Interfaces:**

```python
# costs/service/rules.py (pur)
WINDOWS = (7, 30, 90)
def window(today: date, days: int) -> tuple[date, date]               # (today - days + 1, today)
def aggregate(calls: Sequence[CallFact], zone: ZoneInfo, since: date, until: date) -> CostsReport
    # by_day : chaque jour de la fenêtre, zéros compris, ordre chronologique ; autres axes triés
    # par coût décroissant puis clé ; cost_usd arrondi à 6 décimales ; estimated_calls compté
@dataclass(frozen=True) class CallFact: at: datetime; graph: str | None; agent: str | None
    provider: str; model: str; tokens_in: int; tokens_out: int; cost_usd: float; estimated: bool
# costs/repository.py
class LlmCallRepository(UserScopedRepository[LlmCall]):
    async def since(self, start_utc: datetime) -> list[LlmCall]
    async def page(self, *, before: tuple[datetime, str] | None, limit: int,
                   agent: str | None, graph: str | None) -> list[LlmCall]   # servi en 9.B3
```

- [ ] **Step 1: Write the failing tests**

```python
def test_by_day_has_every_day_of_window(): ...        # 30 lignes, zéros compris
def test_day_is_local(): ...                          # 23 h 30 UTC le 15/11 → 16/11 à Paris
def test_feature_key_is_graph_or_empty(): ...
def test_model_key_is_provider_colon_model(): ...
def test_totals_equal_sum_of_rows(): ...
async def test_costs_route_default_30_days(client): ...
async def test_costs_days_not_in_windows_is_422(client): ...   # fields ["days"]
async def test_other_user_calls_invisible(client): ...         # cas d'isolation du routeur costs
```

`tests/isolation/cases_b.py` (lu par le test garde de 9.A4 après la fusion ; n'importe rien) :

```python
CASES: dict[str, str] = {
    "app.features.costs.router": "tests/features/costs/test_router.py::test_other_user_calls_invisible",
    "app.features.account.router": "tests/features/account/test_export.py::test_export_has_only_own_rows",
}
```

Dans l'arbre B, créer aussi `tests/isolation/__init__.py` s'il manque (vide ; 9.I garde celui de A si les deux existent, contenu identique).

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/costs -q` ; commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): rapport des coûts par jour, feature, agent et modèle (9.B2)` ; D182 (P15).

---

### Task 9.B3 : Journal des agents, catalogue, surcharge par agent — simple

**Files:**
- Create: `backend/app/features/costs/service/calls.py`, `backend/app/features/settings/agents.py`
- Modify: `backend/app/features/costs/router.py` (`GET /costs/calls`), `backend/app/features/settings/{schemas.py (validation), service.py (onboarding jamais remis à faux), keys_router.py (corps de GET /settings/agents)}`
- Test: `backend/tests/features/costs/test_calls.py`, `backend/tests/features/settings/{test_agents.py, test_overrides.py, test_onboarding.py}`

**Interfaces:**

```python
def encode_cursor(at: datetime, call_id: str) -> str     # base64url de "iso|id"
def decode_cursor(raw: str) -> tuple[datetime, str]     # AppError 422 fields ["before"] si illisible
async def list_calls(db, user_id, *, before: str | None, limit: int, agent: str | None,
                     graph: str | None) -> AgentCallPage
def agent_catalogue() -> list[AgentOut]                  # AGENTS hors « demo_ », triés par nom
# UserSettings : agent_overrides validé (clé ∈ AGENTS, sinon ValueError fixe « agent inconnu ») ;
# _parse_stored retire en silence une surcharge d'un agent disparu (journal : nom du champ seulement)
# SettingsService.replace : onboarding_done = stocké or nouveau
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_calls_newest_first_with_cursor(client): ...     # 120 appels : 50, 50, 20, next_before None
async def test_calls_filter_agent_and_graph(client): ...
async def test_bad_cursor_is_422_without_echo(client): ...
async def test_agents_catalogue_excludes_demo(client): ...
async def test_unknown_agent_override_is_422(client):
    r = await client.put("/api/v1/settings", json=body(agent_overrides={"inconnu": glm}))
    assert r.status_code == 422 and "inconnu" not in r.text
async def test_agent_override_used_by_next_session(...):     # F6 : llm_calls.model = modèle surchargé
async def test_tier_switch_visible_in_llm_calls(...):         # F6 : niveau fort passé de anthropic à glm
async def test_onboarding_done_never_reset(client): ...       # PUT avec false après true : reste true
async def test_stored_override_of_removed_agent_dropped(db_session): ...
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/costs tests/features/settings -q` ; commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): journal des agents et surcharge du modèle par agent (9.B3)` ; D183 (P16, P17, P20 côté back).

---

### Task 9.B4 : Export de toutes les données — complexe

**Files:**
- Create: `backend/app/features/account/{repository.py, service/__init__.py, service/tables.py, service/export.py}`
- Modify: `backend/app/features/account/router.py` (dépendance locale `get_account_runtime` qui lit `app.state.memory_providers` et `app.state.runtime`, corps de `GET /account/export`), `backend/app/providers/storage/{base.py, local.py}` (`list_user`), le faux stockage de `tests/support/` s'il existe
- Test: `backend/tests/features/account/{test_tables.py, test_export.py, test_logs.py}`, `backend/tests/providers/storage/test_local_user.py`

**Interfaces:**

```python
# account/service/tables.py
EXCLUDED_TABLES = frozenset({"auth_sessions"})
REDACTED_COLUMNS: Mapping[str, frozenset[str]] = {"api_keys": frozenset({"encrypted_key"})}
def user_tables() -> list[Table]          # Base.metadata.sorted_tables qui ont une colonne user_id
def row_json(row: Mapping[str, Any]) -> dict[str, Any]   # datetime/date en ISO, JSON tel quel
# account/repository.py
class AccountRepository:                   # exception documentée : parcourt toutes les tables, filtre user_id
    def __init__(self, session: AsyncSession, user_id: str) -> None
    async def rows(self, table: Table) -> list[dict[str, Any]]
# providers/storage/base.py
async def list_user(self, user_id: str) -> list[str]     # clés relatives sous storage/<user_id>/
# account/service/export.py
async def build_export(db, storage: FileStorage, user_id: str, now: datetime) -> SpooledTemporaryFile[bytes]
    # zip écrit dans un SpooledTemporaryFile (32 Mo en mémoire, puis disque), servi en flux par
    # morceaux de 64 Kio ; verrou par utilisateur (KeyLocks) : un export à la fois
def export_filename(now: datetime, zone: ZoneInfo) -> str   # tremplin-export-20261117.zip
```

- [ ] **Step 1: Write the failing tests**

```python
def test_user_tables_include_every_scoped_table(): ...   # au moins users, user_settings, llm_calls, goals, memory_items
async def test_export_zip_has_manifest_tables_and_files(client): ...
async def test_export_has_only_own_rows(client): ...      # cas d'isolation du routeur account (deux comptes)
async def test_export_never_contains_encrypted_key(client):
    data = await export_bytes(client)
    assert b"encrypted_key" not in data and cipher_token not in data.decode("latin-1")
async def test_export_files_of_other_user_absent(client): ...
async def test_export_new_table_needs_no_change(tmp_metadata): ...   # table de test avec user_id : exportée
async def test_export_never_logged(caplog, client): ...   # nom de fichier, contenu, e-mail absents
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/account tests/providers/storage -q` ; commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): export de toutes les données (9.B4)` ; D184 (P18).

---

### Task 9.B5 : Tout supprimer — complexe

**Files:**
- Create: `backend/app/features/account/service/delete.py`
- Modify: `backend/app/features/account/{router.py, repository.py}`, `backend/app/providers/storage/{base.py, local.py}` (`delete_user`), `backend/app/agents/runtime/{handle.py ou runner.py}` (`delete_threads(session_ids)` par `checkpointer.adelete_thread`)
- Test: `backend/tests/features/account/test_delete.py`, `backend/tests/providers/storage/test_local_user.py`, `backend/tests/agents/runtime/test_delete_threads.py`

**Interfaces:**

```python
async def delete_account(rt: AccountRuntime, user_id: str, *, auth_mode: Literal["local", "google"]) -> None
    # P19 : sessions running/waiting_user/paused annulées (runner.cancel) → index.delete_user →
    # storage.delete_user → runtime.delete_threads(ids des sessions) → une transaction :
    # DELETE de chaque table de user_tables() (ordre inverse de sorted_tables), sauf `users` en mode local
@dataclass class AccountRuntime: session_factory; index: MemoryRepository; storage: FileStorage; runtime: AgentRuntime
```

Route : `confirm != DELETE_CONFIRMATION` → 422 `confirmation_required` (`fields: ["confirm"]`, sans écho) ; succès → 204 et, en mode Google, `clear_session_cookie` (`app.features.auth.service.cookies`, posé en 9.P) ; Qdrant indisponible → 503 `vector_store_unavailable` **avant** toute suppression en base (un nouvel appel reprend).

- [ ] **Step 1: Write the failing tests**

```python
async def test_wrong_confirmation_is_422_without_echo(client): ...
async def test_delete_empties_every_scoped_table(client): ...      # local : seules users (1 ligne) reste
async def test_delete_keeps_other_user(client): ...                # cas d'isolation : Dominique intacte (base, vecteurs, fichiers)
async def test_delete_cancels_running_sessions(client): ...
async def test_delete_vector_down_then_retry_completes(client): ...
async def test_delete_removes_checkpoints(client): ...
async def test_local_mode_usable_after_delete(client): ...         # GET /settings défauts, onboarding_done false, /auth/me 200
async def test_google_mode_delete_removes_user_and_clears_cookie(google_client): ...
async def test_delete_never_logged(caplog, client): ...
```

- [ ] **Step 2–4:** fail, implement, pass — `uv run pytest tests/features/account tests/providers/storage tests/agents/runtime -q` ; commandes de contrôle.
- [ ] **Step 5: Commit** `feat(phase-9): tout supprimer (9.B5)` ; D185 (P19).

---

## Flux C — Front (arbre `../tremplin-wt/c`, branche `phase9/c`)

Toutes les tâches de C codent contre les types générés en 9.P (`frontend/src/shared/api/schema.d.ts`) et simulent l'API par MSW (`src/test/<zone>Api.ts`) ; aucune ne touche `schema.d.ts`. Textes dans `shared/i18n/messages/<zone>.ts` (zones nouvelles `auth.ts`, `costs.ts`, `account.ts`, `onboarding.ts`, ajoutées à l'agrégateur `fr.ts`). États vide, chargement, erreur avec « Réessayer » ; jamais `window.confirm` ; focus jamais perdu sur `body` après une action ; 1 024 px sans défilement horizontal ; un `h1` par page.

### Task 9.C1 : Correctifs d'ouverture (front) — simple

**Files:** `frontend/src/features/radar/pages/RadarPage/RadarContent.tsx` (N4 : focus sans lire `location.state`, état passé par le magasin de la page), `frontend/src/features/projects/pages/ProjectPage/ProjectView.tsx` (N5 : `retried` remis à faux), formulaire « à reprendre » prérempli avec le dernier rendu, bouton « Régénérer les brouillons » (`POST /projects/{id}/drafts`, visible si validé sans brouillons), `frontend/e2e/daily.spec.ts` (ne suppose plus qu'aucun parcours n'a ouvert l'accueil avant), mineurs parqués 8.13 (notices de rattrapage en rafale : 3 au plus par relecture, la plus récente d'abord ; notice en pause au survol et au focus) ; leurs tests.

- [ ] **Step 1–4:** tests `radar focus without location state`, `retry flag resets after success`, `to-redo form prefilled with last submission`, `regenerate drafts button only when validated without drafts`, `catch-up notices capped at three`, `notice pauses on hover and focus` ; implémentation ; `vitest`, `lint`, `typecheck`.
- [ ] **Step 5: Commit** `fix(phase-9): correctifs d'ouverture du front (9.C1)` ; D186 dans `docs/superpowers/decisions/phase-9-C.md`.

---

### Task 9.C2 : Coquille (portes, routes publiques, cookie) et feature `auth/` — complexe

**Files:**
- Create: `frontend/src/shared/api/authEvents.ts`, `frontend/src/features/auth/{manifest.ts, api.ts, queryKeys.ts}`, `hooks/{useMe.ts, useClaim.ts, useLogout.ts}`, `components/{AuthGate, AccountMenu, ClaimChoice, LoginCard}/`, `pages/{LoginPage, ClaimPage}/`, `frontend/src/test/authApi.ts`, `frontend/src/shared/i18n/messages/auth.ts`
- Modify: `frontend/src/shared/lib/feature.ts`, `frontend/src/shared/api/client.ts`, `frontend/src/app/{router.tsx, registry.ts}`, `frontend/src/app/layout/AppLayout/` (enveloppe par les portes), `frontend/src/shared/i18n/fr.ts`

**Interfaces:**

```ts
// shared/lib/feature.ts
export interface FeatureShell { topbar?: ComponentType; overlay?: ComponentType;
  gate?: ComponentType<{ children: ReactNode }> }          // enveloppe la mise en page, ordre de FEATURES
export interface FeatureManifest { id: string; routes: RouteObject[]; publicRoutes?: RouteObject[];
  nav?: NavEntry[]; shell?: FeatureShell }
// shared/api/authEvents.ts
export function onAuthRequired(listener: () => void): () => void
export function emitAuthRequired(): void                    // appelé par le middleware sur 401 auth_required
// shared/api/client.ts : createClient({ …, credentials: "include" })
// features/auth/api.ts
export const loginUrl: (hint?: string) => string           // `${apiBaseUrl}/api/v1/auth/google/login`
```

Comportements : `AuthGate` lit `GET /auth/me` ; 200 → enfants ; 401 → `<Navigate to="/connexion" replace />` ; autre erreur → `ErrorState` avec « Réessayer » ; un `emitAuthRequired` invalide `me` (une seule redirection, jamais de boucle). `authManifest` est **premier** dans `FEATURES`. `/connexion` (public) : `LoginCard` « Se connecter avec Google » (lien plein vers `loginUrl()`), messages d'erreur par code (`access_denied` « Connexion annulée. », `state_invalid` « La connexion a expiré, recommence. », `email_not_allowed` « Ce compte n'est pas autorisé sur cette instance. », `email_unverified` « Adresse Google non vérifiée. », `google_unavailable` « Google ne répond pas, réessaie dans un instant. », `token_invalid` « Réponse de Google refusée. ») ; en mode local, `/connexion` renvoie vers `/`. `/connexion/reprise` (public) : `ClaimChoice` « Reprendre les données de cet ordinateur » / « Commencer un espace vide », 409 `claim_expired` → retour à `/connexion` avec message. `AccountMenu` (`shell.topbar`, mode Google seulement) : e-mail et « Se déconnecter ».

- [ ] **Step 1–4:** tests `client sends credentials include`, `gate renders children when signed in`, `gate redirects to /connexion on 401`, `a 401 mid-session leads once to /connexion`, `public routes render without layout or gates`, `login error messages by code`, `claim take_local then home`, `claim expired returns to login`, `account menu hidden in local mode`, `logout returns to /connexion`, `buildNav ignores publicRoutes` ; implémentation ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-9): connexion et portes de la coquille (9.C2)` ; D187 (P21, P22).

---

### Task 9.C3 : Coûts et journal des agents — simple

**Files:** `frontend/src/features/costs/{manifest.ts, api.ts, queryKeys.ts, toView.ts}`, `hooks/{useCosts.ts, useAgentCalls.ts}`, `components/{CostTotalsCard, CostByDayChart, CostTable, WindowPicker, AgentCallList, CallFilters}/`, `pages/{CostsPage, AgentLogPage}/`, `frontend/src/app/registry.ts`, `frontend/src/test/costsApi.ts`, `messages/costs.ts`

Routes `/reglages/couts` (Réglages, ordre 6, « Coûts ») et `/reglages/journal` (ordre 7, « Journal des agents »). Coûts : fenêtre 7 / 30 / 90 jours, total (appels, jetons entrants et sortants, coût « 0,42 $ », appels estimés signalés « dont 3 estimés »), barres par jour (Recharts, tableau équivalent pour les lecteurs d'écran), tableaux par feature (libellé du graphe, « Hors session » pour la clé vide, nom brut pour un graphe inconnu), par agent (`agentIdentity`), par modèle. Journal : liste datée (agent, graphe, modèle, jetons, durée, coût, « estimé »), filtres agent et graphe, « Voir plus » par `next_before`, lien vers la session quand il y en a une.

- [ ] **Step 1–4:** tests `costs page shows totals and four breakdowns`, `window change refetches`, `empty window shows empty state`, `unknown graph shown raw`, `chart has a table alternative`, `agent log paginates with next_before`, `filters reset the cursor` ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-9): écran des coûts et journal des agents (9.C3)` ; D188.

---

### Task 9.C4 : Disponibilité et rythme, style, surcharge par agent — simple

**Files:** `frontend/src/features/settings/components/{AvailabilityFields, DelaysField, StyleGuideEditor, AgentOverridesTable}/`, `pages/{AvailabilityPage, StylePage}/`, `hooks/{useAgents.ts}`, `frontend/src/features/settings/{manifest.ts, userSettings.ts, api.ts}`, `pages/ModelsAndKeysPage/` (section « Mode avancé »), `frontend/src/test/settingsApi.ts`, `messages/settings.ts`

`/reglages/disponibilite` (ordre 3, « Disponibilité et rythme ») : `AvailabilityFields` (minutes en semaine, bloc du week-end min et max, budget hebdomadaire calculé écrit), heure du brief, délais de relance (trois nombres croissants), tours de débat (1 à 5), plafond par session (≥ 10 000 jetons), langue des leçons. `/reglages/style` (ordre 5, « Style ») : guide de style personnel (texte, compteur). Modèles et clés : « Mode avancé » replié, `AgentOverridesTable` (agent par `agentIdentity`, niveau par défaut écrit, choix « Niveau par défaut » ou fournisseur + modèle via `ModelField`). **`buildUserSettings` recopie `onboarding_done` et `agent_overrides`**.

- [ ] **Step 1–4:** tests `buildUserSettings keeps onboarding_done and agent_overrides`, `availability saves and shows weekly budget`, `delays must increase`, `422 field error attached without echo`, `style guide saves`, `advanced mode lists agents and saves an override`, `removing an override returns to tier` ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-9): disponibilité, style et surcharge par agent (9.C4)` ; D189 (P17 côté front).

---

### Task 9.C5 : Mes données (export, suppression) — simple

**Files:** `frontend/src/features/account/{manifest.ts, api.ts}`, `hooks/useDeleteAccount.ts`, `components/{ExportCard, DeleteAccountCard}/`, `pages/DataPage/`, `frontend/src/app/registry.ts`, `frontend/src/test/accountApi.ts`, `messages/account.ts`

`/reglages/donnees` (ordre 8, « Mes données ») : « Exporter toutes mes données » (lien plein vers `${apiBaseUrl}/api/v1/account/export`, texte de ce que contient l'archive, sans les clés) ; « Tout supprimer » : explication (irréversible, ce qui part, les clés de `.env` restent), champ « Tape SUPPRIMER pour confirmer », bouton actif seulement si la saisie est exacte, `aria-busy` pendant l'appel ; 204 → mode local : retour à `/bienvenue` (réglages vidés) ; mode Google : `/connexion`.

- [ ] **Step 1–4:** tests `export link targets the API`, `delete disabled until exact word`, `delete sends confirm and goes to welcome in local mode`, `delete goes to login in google mode`, `422 shows field error`, `focus moves to result message` ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-9): export et suppression des données (9.C5)` ; D190.

---

### Task 9.C6 : Premier lancement en 5 étapes — simple

**Files:** `frontend/src/features/settings/components/{OnboardingSteps, ServiceChecklist, EmbeddingProgressBar, PrivacyNotice, CvImportStep}/`, `pages/WelcomePage/`, `OnboardingGate.tsx` (`shell.gate` du manifeste `settings`), `hooks/{useEmbeddingProgress.ts, useFinishOnboarding.ts, useImportProfile.ts}`, `frontend/src/features/settings/{manifest.ts, api.ts}`, `frontend/src/test/onboardingApi.ts`, `messages/onboarding.ts`

`/bienvenue` (hors navigation). `OnboardingGate` : `onboarding_done` faux et page ≠ `/bienvenue` → `<Navigate to="/bienvenue" replace />`. Étapes (`OnboardingSteps` : « Étape 2 sur 5 », précédent / suivant, focus sur le titre de l'étape) : **1** `ServiceChecklist` (`GET /health` toutes les 5 s, un état écrit par service) et `EmbeddingProgressBar` (`GET /health/embedding` toutes les 3 s tant que `present` est faux, « bge-m3 : 42 % ») ; **2** `PrivacyNotice` (tableau de 17.3, retrait du nom, de l'e-mail et du téléphone des requêtes, contacts limités au nom, au rôle et à un lien public) ; **3** clé d'API : `ApiKeyForm` et « Tester » ; une clé déjà fournie par `.env` le dit ; « Plus tard » possible ; **4** `CvImportStep` (CV PDF, profil LinkedIn PDF facultatif, `POST /cv/profile/import` multipart, « Passer ») ; **5** `AvailabilityFields`, puis « Terminer » : `PUT /settings` complet avec la disponibilité et `onboarding_done: true`, vers `/`. Lien « Passer l'accueil » à chaque étape (même `PUT`, sans disponibilité changée).

- [ ] **Step 1–4:** tests `gate sends a new account to /bienvenue`, `gate lets an onboarded account through`, `five steps in order with step counter`, `embedding progress polls until present`, `key step accepts env key and moves on`, `cv step can be skipped`, `finish saves availability and onboarding_done`, `skip link finishes without changing availability`, `onboarding never shown again after finish` ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-9): premier lancement en cinq étapes (9.C6)` ; D191 (P20).

---

## Après les flux

### Task 9.I : Intégration (contrôleur)

- [ ] **Step 1: Fusion** dans l'arbre principal, sur `dev` : `git merge --no-ff phase9/a`, puis `phase9/b`, puis `phase9/c` (messages `merge(phase-9): flux A …`). Conflit attendu : `tests/isolation/__init__.py` (vide des deux côtés : garder l'un) ; sur `contracts/openapi.json` ou `schema.d.ts` seulement, régénérer (P1).
- [ ] **Step 2: Contrat** — `cd backend && uv run python -m scripts.export_openapi`, `node frontend/scripts/run-tool.mjs gen:api`, `node frontend/scripts/check-api-types.mjs` ; tout écart avec 9.P est expliqué dans D192 et commité (`chore(contrat): régénération après fusion (9.I)`). `uv run alembic heads` : une tête, `0015`.
- [ ] **Step 3: Décisions** — fragments `docs/superpowers/decisions/phase-9-{A,B,C}.md` recopiés dans `DECISIONS.md` (D176 à D191, dans l'ordre), fragments retirés.
- [ ] **Step 4: Suites complètes** — back en fond (`uv run pytest -q`, 30 à 40 min, `tests/isolation/test_guard.py` vert) ; front complet (`node node_modules/vitest/vitest.mjs run`), lint, typecheck ; commandes de contrôle back ; parcours Playwright n° 1 à 4 sur Edge (config temporaire). Un échec est corrigé ici (un test qui échoue d'abord), par Sonnet, une tâche par zone.
- [ ] **Step 5:** arbres retirés (`git worktree remove ../tremplin-wt/{a,b,c}`, branches `phase9/*` supprimées), volumes `tremplin-devvenv-{a,b,c}` retirés. Commit `docs(phase-9): intégration des trois flux (9.I)` ; D192.

### Task 9.E : Parcours de bout en bout n° 5 — simple

**Files:** Create `frontend/playwright.auth.config.ts` (back `uv run python -m tests.e2e.server --auth google --port 8766 …`, Vite sur 5181, mêmes gardes que `playwright.config.ts`), `frontend/e2e/account.spec.ts`.

Parcours : sur une base neuve en mode Google avec un espace `local` préparé (une capture au journal) : (1) `/` → `/connexion` → « Se connecter avec Google » (faux fournisseur, Camille) → `/connexion/reprise` → « Reprendre » → `/bienvenue` (étapes 1 à 5, CV passé) → accueil ; la capture de l'espace local est au journal. (2) Réglages > Style : un texte enregistré. (3) Déconnexion → `/connexion` ; connexion de Dominique (`/api/v1/auth/google/login?login_hint=dominique.exemple@example.org`) → **pas** de page de reprise → `/bienvenue` ; le journal de Dominique est vide, son style aussi. (4) Dominique : Mes données → « Exporter » (téléchargement, zip non vide) → « Tout supprimer » (`SUPPRIMER`) → `/connexion`. (5) Camille se reconnecte : ses données sont intactes.

- [ ] **Step 1–4:** spec, exécution sur Edge (config temporaire qui étend `playwright.auth.config.ts`, retirée ensuite) ; parcours n° 1 à 4 toujours verts.
- [ ] **Step 5: Commit** `test(e2e): parcours n° 5, connexion, isolation et données (9.E)` ; D193 (P23).

### Task 9.R : Revue finale et vague de correctifs (contrôleur)

Revue sur **Opus high**, trois zones en parallèle en lecture seule, une par flux : **A** (connexion, témoins, authentificateur, reprise, isolation, santé, README), **B** (coûts, journal, surcharge, export, suppression, correctifs back), **C** (coquille et portes, auth, coûts, réglages, données, premier lancement, e2e n° 5) ; chacune relit aussi les Review Focus de sa zone. Une vague de corrections (Sonnet, un test qui échoue avant chaque correction, un écrivain à la fois), revérification sur Sonnet ; les résiduels sont tranchés ou parqués. Commit des correctifs par zone ; D194 résume.

### Task 9.S : Essai réel de fin de phase (contrôleur)

- [ ] **Step 1: Script** `backend/scripts/check_phase9.py` (+ `phase9_*.py`, mêmes conventions que `check_phase8` : une ligne par étape, aucune donnée affichée, `--api`, `--logs-file -`) et ses tests contre une fausse API. Parties :
  - `couts` : `GET /costs` (30 jours) cohérent avec la somme de `GET /costs/calls` sur la même fenêtre ; 30 jours dans `by_day` ;
  - `modele` (F6) : surcharge de l'agent du graphe `capture` vers un autre modèle GLM listé par `GET /settings/models`, une capture d'un lien public fictif-sans-donnée (`https://example.org/`), puis `GET /costs/calls?graph=capture` : le dernier appel porte le modèle surchargé ; surcharge retirée ensuite ;
  - `donnees` (**pile jetable seulement**, option `--disposable` obligatoire) : export (manifeste, tables, aucun `encrypted_key`), puis « Tout supprimer » : coûts vides, mémoire vide, réglages par défaut, `/auth/me` en 200 (mode local) ;
  - `connexion` (**pile jetable en mode Google seulement**) : deux comptes par le faux fournisseur (conteneur annexe `learning_career_platform-check9-oidc` lancé par `python -m scripts.fake_oidc`, port publié sur `127.0.0.1:8099`), reprise de l'espace local par le premier, isolation vérifiée sur objectifs, mémoire, captures, offres, coûts ;
  - `journaux` : lit l'entrée standard **après** l'essai (`docker compose logs --since …`) ; aucun e-mail, `sub`, code, jeton, cookie, nom de fichier.
- [ ] **Step 2: Pile jetable** : volumes `learning_career_platform_app_data` et `learning_career_platform_qdrant_data` copiés vers `learning_career_platform_check9_app_data` et `learning_career_platform_check9_qdrant_data` ; conteneurs `learning_career_platform-check9-*` (back, Qdrant, front pointé sur ce back) sur les images finales ; GLM réel. Parties `couts`, `modele`, `donnees`, puis back relancé en mode Google pour `connexion`, puis `journaux`. Durées, appels, coûts notés. Pile et volumes jetables retirés.
- [ ] **Step 3: Google réel (optionnel, quand les identifiants seront là)** : client OAuth créé par l'utilisatrice, `.env` rempli **par elle** ; connexion réelle sur la vraie pile, reprise de l'espace local, déconnexion ; résultat ajouté à D195. Sans identifiants : noté « non joué » dans le bilan.
- [ ] **Step 4:** D195 (résultats chiffrés).

### Task 9.Q : Recette complète de l'application et vague de correctifs (contrôleur, Sonnet)

Tourne après 9.R et 9.S, sur le nouveau quota. Budget annoncé : **4 à 6 points de quota** ; l'agent s'arrête et rend un rapport partiel s'il dépasse **environ 2 h**.

- [ ] **Step 1: Pile jetable neuve** : volumes `learning_career_platform_app_data` et `learning_career_platform_qdrant_data` **recopiés** vers `learning_career_platform_check9_*` (ceux de 9.S ont été vidés par « Tout supprimer »), conteneurs `learning_career_platform-check9-*` (back + Qdrant + front pointé sur ce back), **GLM réel**. Jamais le vrai compte : aucune fausse donnée dans les données de l'utilisatrice.
- [ ] **Step 2: Parcours** dans Edge (Playwright avec la config Edge temporaire non commitée, ou le MCP Playwright), à **1 024 px**, **chaque action principale une fois** par feature : objectifs, conseil, programme, leçons, bibliothèque, séance guidée, révisions, quiz, journal, carte des compétences, Portfolio (rendu d'un projet), profil maître, CV (revue), offres, écarts, candidatures (fiche, relance, kit, entretien blanc, comité), radar, accueil (brief, actions rapides, fil), capture rapide, réglages (modèles et clés, mode avancé, recherche, étude, disponibilité, style, coûts, journal), et les nouveautés de la phase : connexion par le faux fournisseur OIDC (sans identifiants Google), reprise de l'espace local, premier lancement, export, puis **suppression en dernier** (pile jetable seulement). Un passage **clavier** sur les actions clés.
- [ ] **Step 3: Critères** à chaque page : aucun défilement horizontal, aucune erreur de console, focus jamais perdu sur `body`, textes en français ; après coup, journaux du back jetable relus à la main : aucune donnée personnelle.
- [ ] **Step 4: Rapport** `docs/superpowers/recette/phase-9.md` : une ligne par page et action (ok / défaut, gravité Critical / Important / Minor, étapes pour reproduire, sans donnée personnelle), coût LLM total (depuis `GET /costs` de la pile jetable). Pile et volumes jetables retirés.
- [ ] **Step 5: Vague** : les Critical et Important passent dans une petite vague de correctifs (Sonnet, un test qui échoue avant chaque correction, un écrivain à la fois, relecture Sonnet) **avant le tag** ; les Minor vont au bilan « Points laissés pour plus tard ». Commit `docs(phase-9): recette complète (9.Q)` et commits des correctifs ; D196.

### Task 9.Z : Bilan, tag, push (contrôleur)

- [ ] **Step 1:** suite back complète et front complet sur la tête finale (si la vague de 9.Q a touché du code), parcours n° 1 à 5 sur Edge.
- [ ] **Step 2:** `docs/superpowers/bilans/phase-9.md` (même forme que `phase-8.md`, dont « Points laissés pour plus tard » et les Minor de la recette), D197, plan directeur (« Phase 9 » faite), mémoire du projet ; quota hebdomadaire demandé à l'utilisatrice.
- [ ] **Step 3:** `git tag phase-9`, `git push origin dev --tags`.

---

## Questions ouvertes

1. **Identifiants Google** (client OAuth « Application Web ») : pas encore fournis. Hypothèse retenue : tout est construit et prouvé avec le faux fournisseur (tests, e2e n° 5, 9.S, 9.Q) ; l'essai réel (9.S étape 3) se joue quand l'utilisatrice aura créé le client et rempli `.env` elle-même.
2. **`ALLOWED_EMAILS`** : hypothèse, vide par défaut (tous les comptes Google autorisés) ; l'utilisatrice y mettra son adresse si l'instance est exposée.
3. **Premier lancement pour le compte existant** : hypothèse, la migration le marque fait (January ne le revoit pas) ; il reste visible pour tout nouveau compte Google et après « Tout supprimer ».

## Auto-relecture (faite à l'écriture)

- **Couverture de la spec** : 17.1 (deux modes, PKCE, portées, cookie 30 jours `HttpOnly` `SameSite=Lax`, adresse de retour, reprise de `local`, `ALLOWED_EMAILS`, README) → 9.P, 9.A1 à 9.A3, 9.A5, 9.C2 ; 17.2 (isolation par routeur, clés jamais renvoyées ni journalisées, journaux sans contenu) → 9.A4, 9.B4, tests `never_logged` ; 17.3 (premier lancement l'explique, Exporter, Tout supprimer) → 9.C6, 9.B4, 9.B5, 9.C5 ; 17.4 CORS (existant, cookies `credentials`) → 9.C2 ; 11.2 mode avancé → 9.B3, 9.C4 ; 11.4 (disponibilité, langue des leçons, tours, plafond, heure du brief, délais, style ; langues et domaines existants) → 9.C4 ; 11.5 → 9.B2, 9.C3 ; 14.2 « Réglages » (`GET /costs`) et « Connexion » (`login`, `callback`, `logout`, `me`) → 9.P, 9.A2, 9.A3, 9.B2 ; 15.1 Réglages (modèles et clés, disponibilité, style, coûts, journal) → 9.C3, 9.C4 ; 15.5 (santé et progression d'embedding, clé et test, import CV et LinkedIn passable, disponibilité) → 9.A5, 9.C6 ; 16.2 (`.env.example`, README) → 9.A5 ; 18.1 phase 9 (« les 3 parcours de bout en bout passent ») → 9.I, 9.E, 9.Z ; 18.3 F6 (niveau `fort` changé visible dans `llm_calls`, clé invalide signalée : existant) → 9.B3, 9.S `modele` ; F7 → 9.A4, 9.E, 9.S `connexion` ; critères transverses (une clé dans `.env` suffit, 300 lignes, coût journalisé) → 9.I, 9.Q ; bilan 8 « Phase 9 — correctifs d'ouverture » → 9.B1, 9.C1, 9.A3 (docstring du serveur e2e).
- **Types cohérents** : `CostsReport`, `CostRow`, `AgentCallPage`, `AgentOut`, `EmbeddingProgress`, `ClaimIn`, `DeleteAccountIn`, `DELETE_CONFIRMATION`, `SESSION_COOKIE`, `clear_session_cookie`, `onboarding_done` définis en 9.P et repris sous les mêmes noms par A, B et C ; `CASES: dict[str, str]` lu par `load_cases` (9.A4), même forme dans `cases_a.py` et `cases_b.py` (9.B2).
- **Fichiers partagés** : vérifiés ligne à ligne contre le tableau « Fichiers partagés » : `main.py`, `bootstrap.py`, `core/*`, `config.py`, `pyproject.toml`, `README.md`, `docker-compose.yml`, `.env.example`, `tests/e2e/server.py` → A seul ; `settings`, `projects`, `costs`, `account`, `storage`, `agents/runtime`, `scripts/check_phase8*` → B seul ; tout `frontend/` → C seul ; `registry.py`, migration, `schema.d.ts`, `openapi.json` → 9.P puis 9.I ; `DECISIONS.md` → 9.I et après. Point de contact unique entre flux : `tests/isolation/` (A écrit le garde et `cases_a.py`, B écrit `cases_b.py` : fichiers distincts). B importe `app.features.auth.service.cookies` (posé en 9.P, que A ne modifie pas : il ajoute des modules au paquet `service/`).
- **Écarts assumés** : P24.
- **Laissé aux phases suivantes** : jeton MCP distinct du cookie (phase MCP du plan directeur) ; Google Agenda (18) réutilisera le port OIDC avec une portée de plus ; une seconde voie de connexion (autre fournisseur) = une implémentation de `OidcProvider`.
