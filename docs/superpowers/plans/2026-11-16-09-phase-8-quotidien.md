# Phase 8 — Quotidien : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mode d'exécution déjà choisi : **subagent-driven en mode économie** (voir « Déroulement »).

**Goal:** Chaque matin, January trouve sur l'accueil son brief du jour, généré seul à l'heure réglée (7 h) ou à l'ouverture s'il date de la veille : bloc d'étude, fiches à réviser, relances dues, nouvelles offres du Radar (score ≥ 70), avancement de la semaine, une ressource sourcée et deux phrases du conseil, avec quatre actions rapides, un fil d'activité et des notifications de fond. Le Radar du marché relève chaque semaine (et à la demande) 30 à 50 offres publiques, dit combien ont été lues et bloquées, classe les compétences par fréquence avec leur évolution et alerte sur ce qui manque au programme. Chaque module reçoit un mini projet que le Praticien évalue ; un projet validé fait passer l'acquis à `prouve` et produit quatre brouillons contrôlés. Le registre des tâches planifiées est complet (brief, radar, bilan, relances, leçons J-7, rafraîchissement ATS) et tenu par la table `jobs`. Plus les correctifs d'ouverture laissés par la phase 7.

**Architecture:** Quatre features back nouvelles : `radar` (relevés, classement, demande du marché), `brief` (brief du jour), `projects` (projets preuves, Portfolio), `activity` (fil d'activité sans table, registre de sources) et un registre des passages `ledger` (table `jobs`). Quatre parcours LangGraph : `market_radar` (Éclaireur : recherche et lecture par lots ; Analyste : extraction par lots de 5), `daily_brief` (Éclaireur : ressource ; Modérateur : conseil), `project_brief` (Praticien : énoncé du mini projet) et `project_review` (Praticien : évaluation et quatre brouillons). Aucun agent nouveau. Les agents n'importent aucune feature (contrat 6) : trois ports de plus dans `AgentPorts` (`radar`, `brief`, `projects`), composés par un nouveau module `app/bootstrap_daily.py` pour garder `app/main.py` sous 300 lignes. Les règles (classement, évolution, alertes, score, périodes, échéances, verdict d'un projet, rubriques du brief) sont des modules purs. Quatre tâches planifiées de plus (`daily_brief`, `market_radar`, `project_briefs`, `ats_refresh`). Côté front : `home/` (brief, actions rapides, `ActivityFeed`, notifications de fond par l'emplacement `overlay`), `radar/` (Carrière), `projects/` (Portfolio, Compétences), parcours Playwright n° 4.

**Tech Stack:** LangGraph (boucles par nœud, `node_timeout`), Pydantic v2 (`Prose`), SQLAlchemy 2 + Alembic, APScheduler 3.11 (existant), `FileStorage` (captures) · React 19, TanStack Query (`refetchInterval`), Zustand (demande de capture partagée), Vitest, Testing Library, MSW, Playwright.

**Spec:** `SPEC.md` §1 (honnêteté, humain dans la boucle), §7 F11, F12, F13 (bilan : planificateur seulement), §8 F15 (taille d'un nœud = demande du marché, référentiel enrichi par le Radar), F17, F18 (capture ouverte depuis l'accueil), §9.1 (Praticien, Éclaireur, Analyste, Modérateur), §9.2, 9.4, 9.5, 9.6 (sorties structurées, 120 s par nœud, tâches planifiées : brief, radar, bilan, relances, leçons à 7 jours, rafraîchissement ATS), §10 (SearXNG, lecture des pages), §11.4 (heure du brief 7 h), §12.3 et 12.4 (`projects/`, `radar/`, `brief/`, `home/`), §13.1, 13.2 (`jobs`), 13.3 (`projects`), 13.5 (`radar_runs`), 13.6 (`briefs`), §14.2 (« Radar et projets », « Accueil »), §15.1 (Accueil ; Compétences : Portfolio ; Carrière : Radar), §15.4, §16.4 n° 6 (graphes longs), §17.2 à 17.4, §18.1 (phase 8), §18.3 (F11, F12, F17 ; critère transverse d'honnêteté). Plan directeur : `docs/superpowers/plans/2026-11-11-00-plan-directeur.md` (§1, §3, §5 « Phase 8 », « Liens entre les phases »). Bilans : `docs/superpowers/bilans/phase-7.md` (« Points laissés pour plus tard »), `phase-6.md` (« Phase 8 » : rafraîchissement ATS). Décisions : D6, D18, D91, D98, D99, D106, D118, D121, D129, D136, D139 à D155.

## Global Constraints

Toutes celles du plan directeur et des plans des phases 4 à 7 s'appliquent. Rappel des plus exposées, puis celles de cette phase.

- **Séparation** : `frontend/` et `backend/` strictement séparés, seul lien `contracts/openapi.json` ; un dossier par feature des deux côtés ; **un dossier par composant front** (`.tsx`, `.test.tsx`, `index.ts`) ; `components/` présentationnel ; une feature front n'importe jamais une autre feature (elle appelle une route d'une autre zone par son propre `api.ts`).
- **Extensibilité** : une feature = un dossier + une ligne dans `FEATURE_ROUTERS` / `app/registry.ts` ; un graphe = un fichier + une ligne dans `GRAPHS` (+ `ROUTE_ONLY`) ; un port = un champ d'`AgentPorts` + une ligne dans `bootstrap_agents.agent_ports` + un faux dans `tests/support/` ; une tâche planifiée = un fichier `scheduler/jobs/` + une ligne dans `JOBS`, sa logique dans un service de feature (contrat 8) ; une source du fil d'activité = une ligne dans `ACTIVITY_SOURCES`.
- **Contrôles** : mypy --strict, ruff (100 colonnes), import-linter : **8 contrats** (le contrat 5 nomme en plus `app.bootstrap_daily`, sans contrat de plus). Sens des imports entre features, sans cycle : `brief` → `radar`, `quiz`, `study`, `applications`, `replan`, `program`, `settings` ; `radar` → `skills`, `program`, `research`, `postings`, `settings` ; `skills` → `radar.service.demand` seulement (ce module n'importe ni `skills` ni rien qui l'importe ; `radar/service/__init__.py` reste vide) ; `projects` → `program`, `lessons`, `skills`, `memory`, `cv`, `capture`, `settings`, `research` ; `activity` → les services lus ; `ledger` n'importe aucune feature. ESLint boundaries, `tsc --noEmit`, Prettier.
- **Taille** : 300 lignes par fichier, 50 par fonction. `app/main.py` est à 272 lignes : **toute la composition de la phase passe par `app/bootstrap_daily.py`** (8.4), `main.py` ne gagne que des appels d'une ligne.
- **Clés API** : jamais renvoyées au navigateur, jamais journalisées.
- **Erreurs** : `{error: {code, message, details}}`, message en français ; **une 422 ne renvoie jamais l'entrée** (ni description de projet, ni lien de dépôt, ni poste ou zone du radar) : `details.fields` nomme les champs, sans valeur.
- **Journaux (17.2)** : identifiants (utilisateur, session, relevé, brief, projet, module, passage), nombres, codes et durées. **Jamais** : un nom d'entreprise, un intitulé, un lien ou un domaine, un texte d'offre, un poste ou une zone visés, une description ou un lien de projet, un critère, un brouillon, une phrase du conseil, une ressource, un nom de fichier de capture. Chaque nouvelle zone a son test `test_*_never_logged`.
- **Honnêteté (1, 18.3, F11)** : aucun texte au nom de January ne contient un chiffre, un outil, un titre ou un nom propre absent de son profil validé **ou de son propre rendu** ; les quatre brouillons passent par `text_claims` (un nouvel essai nommant les termes, puis « à vérifier ») ; « **Rien n'entre dans le profil maître sans validation** » : l'entrée de projet n'y entre que par un clic explicite de January ; le radar dit **toujours** combien d'offres ont réellement été lues, les sites bloqués comptés à part, et ne prétend jamais un échantillon qu'il n'a pas ; un salaire n'est rapporté que s'il figure dans le texte lu ; le conseil ne cite aucun chiffre absent des faits du jour.
- **Tâches planifiées** : idempotentes par jour (brief) ou par semaine (radar), sûres au redémarrage (jamais deux briefs pour le même jour local, jamais deux relevés planifiés la même semaine) ; une panne pour une utilisatrice n'arrête pas les autres ; journaux sans donnée. Le brief est généré à l'heure réglée **et** à l'ouverture s'il date de la veille.
- **Tests sans réseau ni LLM** : modèles scriptés par agent (`ScriptedModels`, `fake_llm`), faux ports (`tests/support/`), `RecordingLauncher`, passerelle web sur fournisseurs factices ; seuls les essais réels (8.8, 8.18) touchent GLM 5.3 flash (Z.ai), SearXNG et la pile Docker.
- **Données de test** : identité fictive « Camille Exemple » (`camille.exemple@example.org`), entreprises « Société Fictive », « Autre SA », « Exemple Tech », domaines `example.org` / `example.invalid` ; offres de `backend/scripts/sample_posting.py`.
- **LangGraph (9.4)** : aucun `interrupt()` dans cette phase ; chaque écriture d'un port est **idempotente** (clé : session + référence) ; une session survit à `docker compose restart backend` ; une boucle (lecture, extraction) relit l'état du port à chaque passage, jamais un compteur gardé seul dans l'état.
- **Sorties structurées (D97, D115)** : `structured_call` (2 nouveaux essais) ; texte libre à lire = `Prose` ; `node_timeout` par nœud (120 s au plus, 9.6) : un graphe long avance **par lots** (risque 16.4 n° 6).
- **Contenu non fiable (17.4)** : texte d'offre, page web, résultat de recherche, README d'un dépôt, description de January, extrait de leçon : **toujours** dans `untrusted(…, label)`.
- **Coût** : radar ≤ 10 appels rapides (lots de 5 offres) ; brief 2 appels rapides ; énoncé d'un projet 1 appel standard ; évaluation 1 appel standard + 1 pour les brouillons (+ 1 nouvel essai au plus) ; aucune requête de recherche écrite par un modèle (requêtes du radar et de la ressource construites par le code).
- **Contrat front/back** : toute tâche back qui change l'API régénère `contracts/openapi.json` (`cd backend && uv run python -m scripts.export_openapi`) **et** `frontend/src/shared/api/schema.d.ts` (`node frontend/scripts/run-tool.mjs gen:api`) dans le même commit ; aucune tâche front ne les touche.
- **Front (15.4)** : textes dans `frontend/src/shared/i18n/messages/<zone>.ts` ; jamais de `window.confirm` ; état vide avec action, chargement, erreur avec « Réessayer » ; couleur jamais seule (évolution écrite « +8 pts », « nouvelle ») ; animations < 300 ms coupées par `prefers-reduced-motion` ; contraste AA ; clavier ; 1 024 px sans défilement horizontal.
- **Environnement (poste Windows)** : Python et `uv` par le remplaçant Docker du scratchpad (`PATH` préfixé par `…/scratchpad/uv-shim`) ; outils front par `node frontend/scripts/run-tool.mjs lint|typecheck`, Vitest par `node node_modules/vitest/vitest.mjs run` ; Playwright avec Edge par une config temporaire retirée ensuite ; images par `docker build -t learning_career_platform-{backend,frontend}:latest`, pile par `docker compose up -d --no-build`. Ne jamais toucher aux conteneurs d'autres projets.

**À vérifier dans la documentation actuelle avant de coder (context7)**, écart noté dans la décision de la tâche : LangGraph, arête conditionnelle qui reboucle sur un nœud (limite `recursion_limit` par défaut 25 : la fixer au lancement si la boucle de lecture peut la dépasser) ; SearXNG, opérateur `site:` transmis aux moteurs activés et paramètre `time_range=month` ; FastAPI, `UploadFile` multiple (`list[UploadFile]`) avec champs de formulaire ; TanStack Query v5, `refetchInterval` en fonction et `refetchIntervalInBackground: false`.

## Review Focus

1. **Deux briefs pour le même jour** (accueil ouvert à 6 h 59 pendant que la tâche de 7 h passe ; double lecture du mode strict de React ; back redémarré entre la création du brief et la fin de sa session ; aucune clé LLM) : un seul brief par jour local, une seule session ; sans modèle, les rubriques du code sont là et le conseil se dit indisponible. → 8.6 `test_concurrent_ensure_creates_one_brief`, `test_job_after_opening_does_nothing`, `test_dead_session_marks_advice_failed`, `test_brief_without_llm_has_code_rubrics`.
2. **Le jour et la semaine de January, pas ceux du serveur** (00 h 30 à Paris = veille en UTC ; dimanche 23 h 30 locale = lundi UTC ; jour de changement d'heure) : le brief porte le jour local, le relevé planifié la semaine ISO locale. → 8.1 `test_brief_day_is_local`, `test_week_period_local_sunday_night`, `test_brief_moment_on_dst_day`.
3. **Radar presque aveugle** (SearXNG en panne, toutes les pages bloquées, 8 offres seulement, des pages qui ne sont pas des offres) : le rapport dit les nombres réels (lues, bloquées, pas des offres), pas d'alerte sous 10 offres analysées, mention « échantillon réduit » sous 30, jamais un échec silencieux. → 8.1 `test_alerts_need_ten_postings`, 8.3 `test_all_blocked_still_reports_counts`, `test_search_unavailable_fails_readably`, 8.4 `test_low_sample_flag`.
4. **Rendu de projet faible ou étrange** (captures seules ; dépôt privé ou illisible sans description ; deuxième envoi après validation ; fiche ratée sur une compétence `prouve`) : 422 sans écho, aucun appel au modèle sur un rendu vide, jamais « validé » sur rien, `prouve` jamais baissé. → 8.1 `test_submission_needs_link_or_description`, 8.9 `test_unreadable_repo_without_description_skips_model`, 8.10 `test_validated_project_refuses_resubmit`, `test_failed_cards_do_not_demote_prouve`.
5. **Brouillon qui invente** (post LinkedIn « 10 000 utilisateurs », « déployé sur Kubernetes » absent du rendu et du profil ; entrée de projet jamais cliquée) : brouillon « à vérifier » avec ses termes, profil maître inchangé tant que January n'a pas cliqué. → 8.9 `test_drafts_with_unsupported_claim_retry_then_flag`, 8.10 `test_profile_unchanged_until_explicit_entry`.

---

## Décisions préalables (P1 à P20, écrites dans les décisions des tâches)

- **P1. Mini projet d'un module** : un projet par module non sauté d'un programme validé (`projects` unique par `module_id`), créé quand la semaine du module commence (lundi local ≤ aujourd'hui), par la tâche `project_briefs` (15 min) ; l'énoncé est écrit par le **Praticien** dans le graphe `project_brief` (un appel standard). Trois essais automatiques, puis « Réessayer » (`POST /projects/{id}/brief`). Le projet n'est **pas placé dans le calendrier** (les règles de planification et le plafond de 85 % ne changent pas). Raison : « chaque module se termine par un mini projet » sans payer d'énoncés pour des modules jamais atteints ni réécrire le planning.
- **P2. Forme du rendu** : lien http(s) d'un dépôt et/ou description (≤ 4 000 caractères), plus 0 à 5 captures PNG, JPEG ou WebP de 5 Mo au plus, rangées par `FileStorage` (`storage/<user_id>/projects/…`, 13.1) ; au moins un lien ou une description. Le dépôt est lu par la passerelle web (une page : README par le lecteur GitHub existant) ; **les captures ne sont pas envoyées au modèle** (niveau vision, coût) : elles sont montrées dans le Portfolio et l'évaluation le dit. Raison : rendu prouvé par ce que le Praticien peut lire, phase 14 (GitHub) remplacera la lecture du dépôt.
- **P3. Validation** : le **verdict est calculé par le code** sur l'évaluation du Praticien (un résultat par critère, tous atteints → `validated`, sinon `to_redo`) ; à la validation, le port monte les compétences du module à `prouve` (preuve `project`), les reflète en mémoire, écrit une ligne `project` au journal ; aucune interruption (comme le quiz à 80 %). Les quatre brouillons ne sont générés qu'à la validation. L'entrée de projet n'entre au profil maître **que par `POST /projects/{id}/profile-entry`** (nouvelle version validée, source `january`). Raison : F11 et « Rien n'entre dans le profil maître sans validation ».
- **P4. Référence d'honnêteté des brouillons** : `text_claims` contre le profil validé **plus un fait de projet** construit du titre de l'énoncé, de la description de January et des compétences du module ; le README n'est jamais une référence (texte web). Raison : un brouillon peut citer ce que January a dit de son projet, rien d'autre.
- **P5. Sources du radar** : requêtes construites par le code (2 génériques et 4 ciblées `site:` sur des pages d'offres publiques : `jobs.lever.co`, `boards.greenhouse.io`, `welcometothejungle.com`, `jobs.ashbyhq.com`), une langue par langue de recherche ; 80 candidats au plus, **60 pages lues au plus, arrêt à 50 offres lisibles** ; « lue » = page `ok`, « bloquée » = page `unreadable` (comptée par domaine, à part), « pas une offre » comptée à part ; la lecture passe par le port du radar, hors plafond de pages de session (budget propre de 60) ; LinkedIn reste exclu par les réglages. Moins de 30 offres lisibles : `low_sample`, le rapport le dit.
- **P6. Extraction** : l'Analyste lit les offres par lots de 5 (4 000 caractères chacune, encadrées), 10 appels au plus ; outils gardés seulement s'ils figurent dans le texte ; salaire gardé seulement si ses chiffres y figurent ; classement, évolution, alertes et scores par le code.
- **P7. Évolution** : comparée au dernier relevé `done` de même poste et même zone (normalisés) : écart de part en points, rang gagné ou perdu, « nouvelle » ; sans précédent, « premier relevé ».
- **P8. Alerte « absente de ton programme »** : au moins 10 offres analysées, part ≥ 50 %, compétence absente de tout module non sauté du programme validé (noms normalisés et synonymes du référentiel) et niveau inférieur à `valide` ; 5 au plus ; « Demandée dans 62 % des offres, absente de ton programme. ».
- **P9. Score et brief** : score de match d'une offre du radar = `match_score` (D118) par le code, niveaux lus par nom normalisé (sans l'appel de rattachement de l'Analyste) ; `HIGH_MATCH = 70`. « Nouvelles offres » du brief : offres ≥ 70 des relevés finis depuis le brief précédent (ou du dernier relevé), hors liens déjà montrés dans les 7 derniers briefs et hors offres ou fiches déjà saisies (lien normalisé), 5 au plus. Le référentiel est enrichi des compétences demandées par ≥ 30 % des offres (15 au plus, sans niveau, F15) et la carte lit `demand` = part du dernier relevé.
- **P10. Rythme du radar** : planifié le lundi à 06:00 locale (avant le brief), période = semaine ISO locale, sauté si un relevé (manuel compris) a été créé cette semaine ; à la demande `POST /radar/runs {role?, zone?}`, mémorisés dans les réglages (`radar_role`, `radar_zone`) ; défaut du poste : réglage, sinon `target_role` du dernier objectif ; zone par défaut « France » ; un seul relevé en cours ; sans poste : 409 `radar_role_required`, passage planifié `skipped`.
- **P11. Rubriques du brief** : bloc, révisions, relances, offres et avancement **calculés par le code** ; seuls la ressource (l'Éclaireur choisit parmi 8 résultats d'une recherche du mois, le code lit la page) et les deux phrases du conseil (Modérateur, au nom du conseil) appellent un modèle : 2 appels rapides ; les chiffres du conseil sont contrôlés par le code. Le brief est un **instantané du jour** (JSON) ; chaque rubrique mène à l'écran vivant.
- **P12. Déclenchement du brief** : `GET /brief/today` crée le brief du jour local s'il manque, quelle que soit l'heure (« à l'ouverture s'il date de la veille ») ; la tâche `daily_brief` (10 min, au démarrage) le crée quand l'heure du brief est passée ; unicité `(user_id, day)` par `INSERT … ON CONFLICT DO NOTHING`, la session n'est lancée que par celui qui a inséré ; la session survit au redémarrage, une session morte rend le conseil `failed` à la lecture.
- **P13. `jobs` et APScheduler** : APScheduler reste en mémoire (intervalles, `coalesce`, `max_instances=1`) ; `jobs` est le **registre persistant des passages** par `(user_id, name, period)` : statut, début, fin, essais, code d'erreur, référence, prochain passage. `claim` atomique (insertion sans conflit, sinon reprise conditionnelle d'une ligne `failed` ou `running` de plus de 30 minutes, 3 essais). Rattrapage = la règle « dû » est relue à chaque passage et au démarrage. Utilisé par `daily_brief` (jour), `market_radar` (semaine), `ats_refresh` (30 jours) ; les 4 tâches existantes gardent leur idempotence ; `project_briefs` s'appuie sur l'unicité des projets.
- **P14. Rafraîchissement ATS** : tâche `ats_refresh`, due quand aucun passage `done` depuis 30 jours ; elle lance le graphe existant `web_research` (requête fixe sur le fonctionnement des ATS, sujet `ats_refresh`) ; le Lecteur ATS reçoit les 3 sources retenues du dernier rafraîchissement de moins de 60 jours, encadrées, après `_shared/ats_base.md`, qui n'est jamais réécrit.
- **P15. Fil d'activité** : aucune table ; registre `ACTIVITY_SOURCES` (une source = une fonction de service d'une feature) : leçons prêtes ou en échec, relevés du radar, briefs, écritures en mémoire des agents, évaluations de projets, passages planifiés en échec. Les phases 10 à 20 ajoutent leur ligne.
- **P16. Notifications de fond** : relecture `GET /activity?after=` toutes les 60 s, onglet visible seulement, depuis l'emplacement `overlay` du manifeste `home` (toutes les pages) ; région `aria-live="polite"`, 3 au plus, 8 s ; ni notification du navigateur (phase 19) ni canal WebSocket nouveau (le WebSocket reste par session, 14.1).
- **P17. Actions rapides** : « Commencer mon bloc » → `/etudier/session`, « Réviser » → `/etudier/revisions`, « Ajouter une offre » → `/carriere/offres`, « Capturer » → ouvre la capture par un magasin partagé `shared/lib/captureRequest.ts` (`home` n'importe pas `capture`).
- **P18. Parcours e2e n° 4** « brief à l'ouverture et relevé du radar » : le serveur e2e coupe le planificateur, il prouve donc le chemin « à l'ouverture » ; web factice d'offres et de sites bloqués. Raison : critère F17 et graphe long du radar couverts de bout en bout à faible coût.
- **P19. Écarts à la spec** : graphe `project_brief` en plus des 16 de 9.2 (comme `application_intake`) ; routes hors 14.2 : `GET /projects/{id}`, `GET /projects/{id}/screenshots/{n}`, `PATCH /projects/{id}/drafts/{kind}`, `POST /projects/{id}/profile-entry`, `POST /projects/{id}/brief`, `GET /radar/runs`, `GET /radar/runs/{id}` ; réglages `radar_role`, `radar_zone`.
- **P20. Points d'accroche, sans les construire** : phase 13 (alertes d'offres) lira `radar_runs.postings` et `HIGH_MATCH` ; phase 14 remplacera `repo_text` du port des projets ; phase 19 lira `GET /brief/today` et `GET /activity` ; phase 20 lira `GET /projects` (validés, brouillons).

---

## Déroulement (mode économie)

- **Modèles** : implémentation par **Sonnet** ; revue par tâche par **Sonnet**. Tâche **simple** : une relecture, un tour de correction, pas de revérification. Tâche **complexe** (graphes LangGraph, contrat central, honnêteté, concurrence du planificateur) : relecture, un tour de correction, revérification. **Opus high** seulement pour la revue finale (8.17). Jamais Fable.
- **Jamais un écrivain front en parallèle d'un écrivain back dans le même arbre** (le stash du hook mélange les fichiers non commités) : les tâches s'enchaînent dans l'ordre ci-dessous. Les relecteurs (lecture seule) peuvent tourner pendant l'implémentation suivante ; le tour de correction attend que l'implémenteur en cours ait commité.
- **Essai réel en milieu de phase (8.8)** : dès que radar et brief existent côté back, avant projets et écrans, le contrôleur les lance contre GLM 5.3 flash et SearXNG dans la pile Docker ; ses correctifs sont faits dans 8.8.
- **Décisions** : une entrée par tâche, **D(156 + n)** pour la tâche 8.n (8.0 → D156 … 8.18 → D174). Format existant (Date, Sujet, Décision en points numérotés, Raison) ; les points P1 à P20 y sont recopiés par la tâche qui les met en œuvre.
- Commits par chemins explicites (jamais `git add -A`), hooks jamais sautés.
- Heure vérifiée par `date` avant chaque lancement d'agent ; quota hebdomadaire demandé à l'utilisatrice en fin de phase.

| Ordre | Tâche | Zone | Revue |
| --- | --- | --- | --- |
| 1 | 8.0 Correctifs d'ouverture (back) | back | simple |
| 2 | 8.1 Tables, règles pures | back | complexe |
| 3 | 8.2 Registre des passages, planificateur, rafraîchissement ATS | back | complexe |
| 4 | 8.3 Parcours `market_radar` | back | complexe |
| 5 | 8.4 Feature `radar` (contrat, tâche hebdomadaire, demande) | back | complexe |
| 6 | 8.5 Parcours `daily_brief` | back | complexe |
| 7 | 8.6 Feature `brief` (contrat, ouverture, tâche du matin) | back | complexe |
| 8 | 8.7 Fil d'activité (contrat) | back | simple |
| 9 | 8.8 Essai réel en milieu de phase | contrôleur | — |
| 10 | 8.9 Parcours `project_brief` et `project_review` | back | complexe |
| 11 | 8.10 Feature `projects` (contrat, rendus, brouillons, profil) | back | complexe |
| 12 | 8.11 Correctifs d'ouverture (front) | front | simple |
| 13 | 8.12 Composants présentationnels | front | simple |
| 14 | 8.13 Accueil : brief, actions rapides, fil, notifications | front | simple |
| 15 | 8.14 Page du Radar | front | simple |
| 16 | 8.15 Portfolio et page d'un projet | front | simple |
| 17 | 8.16 Parcours Playwright n° 4 | back + front | simple |
| 18 | 8.17 Revue complète | contrôleur | Opus high |
| 19 | 8.18 Contrôle réel de fin de phase et bilan | contrôleur | — |

Commandes de contrôle d'une tâche back : `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run python -m mypy app && uv run python -c "from importlinter.cli import lint_imports_command; lint_imports_command()" && uv run python -m scripts.export_openapi --check && uv run python -m scripts.check_file_length`. Front : `node node_modules/vitest/vitest.mjs run` puis `node frontend/scripts/run-tool.mjs lint` et `node frontend/scripts/run-tool.mjs typecheck` (depuis `frontend/` pour Vitest).

## Interfaces consommées (phases 0 à 7)

- Cœur : `AppError(code, message, status_code, details)`, `app.core.deps` (`Db`, `CurrentUserDep`), `UserScopedMixin`, `UTCDateTime`, `new_id`, `UserScopedRepository[M]`, `core.clock` (`user_zone`, `local_today`, `week_start`, `local_moment(day, hhmm, zone)`, `WEEKDAYS`), `KeyLocks`, `core.skills` (`normalize_skill_name`, `evidence(kind, ref_id, label, at)` avec `EvidenceKind` qui contient déjà `"project"`), `core.limits.BodySizeLimit` et `core/body_limits.add_body_limits`.
- Moteur : `AgentPorts` / `NO_PORTS`, `SessionLauncher.start(user_id, graph, input, *, subject_type, subject_id) -> str`, `GraphDeps` (`user_id`, `session_id`, `models.get_chat_model(user_id, tier, agent)`, `settings: RunSettings` dont `lesson_language`, `search_languages`, `web`, `ports`), `structured_call(model, schema, messages, *, agent, step, intent, retries=2)`, `Prose`, `speak`, `emit(type, payload, *, agent)`, `node_timeout(seconds)`, `render_prompt(agent, **vars)` (modes `{% if mode == … %}`), `untrusted(text, label)`, `AGENTS` (`practitioner` standard, `scout` rapide, `analyst` rapide, `moderator` rapide : aucun ajout), `GRAPHS` / `GraphSpec`, `ArtifactReadyPayload(artifact_id, kind, title, url)`, `ROUTE_ONLY`, `web_tools.web_search(deps, query, *, lang, agent)` et `web_read(deps, url, *, agent)`, `WebGateway` (`search(..., time_range=…)`, `read`), `PageRead`, `text_claims(text, profile, *, allowed)`, `Claim`, `MasterProfileData`, `Project`, `SkillFact`, `Identity` (`agents/tools/cv_schema.py`), `PostingAnalysis.level` (valeurs), `contains_term`, `normalize_term`, `ATS_HOSTS`.
- Features : `match_score`, `GapRow` (`features/gap/service/score.py`), `posting_url_key` (`postings.service.rules`), `SkillsService(db, user_id)` (`raise_levels(names, level, evidence)`, `known_levels()`, `upsert_catalog`), `reflect_skill_levels(runtime, user_id, levels, *, author, session_id, reason)`, `program.service.programs.list_validated_programs`, `program.service.skill_modules.skill_weeks`, `replan.service.facts.week_facts(db, user_id, program_id, week) -> WeekFacts`, `study.service.block.block_of_day(db, user_id, today)`, `study.service.view.summary` (série), `quiz.service.cards.due_queue(rt, db, user_id) -> DueQueue`, `applications.service.reminders.list_reminders(rt, user_id, *, due)`, `applications.repository.user_ids` (modèle de la seule lecture sans `user_id`), `cv.service.profile.save_profile(rt, user_id, ProfilePutIn)`, `profile_draft_pending`, `capture.service.journal.add_entry(db, user_id, *, kind, text, occurred_on, ref_key, links, data)`, `research.service.reading.read(runtime, user_id, None, url)` (lecture hors session : cache, débit, garde SSRF), `research.service.reading.list_sources`, `SettingsService(db, user_id).get()` → `UserSettings.brief_time = "07:00"`, `timezone`, `search_languages`, `lesson_language`.
- Planificateur : `JobSpec(name, every, run, at_startup)`, `JobContext`, `JOBS`, `bootstrap_agents.scheduler_context`, `open_scheduler`.
- Tests back : `settings`, `db_session_factory`, `client`, `act_as`, `RecordingLauncher`, `ScriptedModels`, `merge_scripts`, `fake_llm`, `fake_research_providers`, `FakeWebReader`, `all_events`, `final_state`, `tests/agents/graphs/conftest.py`, `tests/e2e/server.py`, `scripts/phase4_steps.py` (`Run`, `CheckFailed`, `EventFeed`, `websocket_feed`), `scripts/phase7_common.py` (`Step`, `Track`), `scripts/sample_posting.py`.
- Front : `api`, `unwrap`, `errorMessage`, `t`, `FeatureManifest` (`shell.overlay`), `NavEntry` (`useBadge`, `badgeLabel`), `FEATURES`, `useRun` (`shared/realtime/useRun.ts`), `RunFeed`, `SideTabs`, `AGENT_COLORS`, `agentIdentity`, `EmptyState`, `LoadingState`, `ErrorState`, `InlineError`, `Button`, `fieldClass`, `usePollingBudget` ; `features/capture/captureDialog.ts` (`useCaptureDialog.openDialog`) ; outillage `src/test/server.ts`, `fakeSocket.ts`, `queryWrapper.tsx`, `renderRoutes.tsx`, `streamHarness.ts`.

---

### Task 8.0 : Correctifs d'ouverture (back) — simple

**Zone : back (`applications`, `postings`).** Ne change le contrat que par une description (régénéré s'il bouge).

**Files:**
- Modify: `backend/app/features/applications/service/kit_store.py` (M1), le module qui découpe les relances du kit côté graphe et côté route (M3 : une seule fonction `split_followups(text) -> tuple[str, str]` dans `agents/tools/kit_schema.py`, appelée des deux côtés), `backend/app/agents/nodes/committee/votes.py` (M5), `backend/app/features/postings/service/` suppression (M6), le service de la fiche entreprise (M7 : un seul verrou), `backend/app/features/applications/schemas.py` (M8), `service/adopt_link.py`, `service/adopt.py` (docstring), `service/views.py` ou le module qui écrit l'événement `version`, `agent_store.py` (`intake_info`), `agents/tools/committee_schema.py` (`SECTION_WORDS`), `postings.service.rules.company_key` usage dans `matching.py`
- Test: les tests voisins sous `backend/tests/features/applications/`, `tests/features/postings/test_delete.py`, `tests/agents/graphs/test_hiring_committee.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_kit_cv_piece_uses_sent_version(...):       # M1 : fiche postulée avec version n° 2 figée, n° 3 prête ensuite
    assert piece["meta"]["version_id"] == v2.id
def test_followups_split_same_rule_graph_and_route(): ...  # M3 : « ---\n » et « --- » collé : même découpe
async def test_vote_values_never_logged(caplog, ...): ...  # M5 : « oui », « non », « peut_etre » absents des journaux
async def test_posting_delete_refused_with_running_committee(...): ...   # M6 : 409 posting_has_running_work
async def test_posting_delete_refused_with_running_free_interview(...): ...
async def test_company_created_once_under_one_lock(...): ...   # M7 : deux créations concurrentes : une ligne
async def test_event_in_future_is_422(client):             # M8
    r = await client.post(f"/api/v1/applications/{app_id}/events", json={"kind": "note", "text": "x", "on": "2099-01-01"})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["on"]
def test_adopt_link_certain_beats_probable(): ...          # hit certain vers une fiche liée ailleurs : aucun lien
async def test_linking_applied_card_says_linked_not_sent(...): ...   # « Version N du CV liée à la fiche. »
async def test_intake_info_failure_still_creates(...): ... # lecture de l'info en panne : fiche créée, info vide
def test_section_words_include_certifications_interests(): ...
def test_empty_company_key_never_probable(): ...           # entreprises non latines : pas de doublon probable
```

- [ ] **Step 2: Run them, check they fail** — `cd backend && uv run pytest tests/features/applications tests/features/postings/test_delete.py tests/agents/graphs/test_hiring_committee.py -q`.
- [ ] **Step 3: Implement** : M1 la pièce `cv` lit `application.cv_version_id` quand il est figé, sinon la version prête la plus récente ; M3 `split_followups` unique ; M5 journal du comité : identifiants et nombre de votes seulement ; M6 suppression refusée 409 `posting_has_running_work` (`details.kind`) tant qu'un comité ou un entretien libre `running` cite l'offre, sous le même verrou que la vérification ; M7 un seul `KeyLocks` par `company_key` ; M8 `EventIn.on ≤ aujourd'hui` (fuseau de January) ; `target_of` examine les hits certains avant les probables ; texte de l'événement d'une fiche reliée déjà postulée : « Version N du CV liée à la fiche. » ; `intake_info` enveloppé (info vide, journal du type d'erreur) ; `SECTION_WORDS` complété (Certifications, Intérêts, Loisirs, Bénévolat, Publications et formes anglaises) ; `matching.match` : `company_norm` vide → jamais `probable`.
- [ ] **Step 4: Run tests, then the full back check commands** — PASS.
- [ ] **Step 5: Commit** `fix(phase-8): correctifs d'ouverture des candidatures (8.0)` ; D156.

---

### Task 8.1 : Tables, migration et règles pures — complexe

**Zone : back (base, règles).** Ne change pas le contrat.

**Files:**
- Create: `backend/app/db/models/daily.py`, `backend/alembic/versions/0013_daily.py`, `backend/app/features/ledger/{__init__.py, service/__init__.py, service/periods.py}`, `backend/app/features/radar/{__init__.py, service/__init__.py, service/rules.py}`, `backend/app/features/brief/{__init__.py, service/__init__.py, service/rules.py}`, `backend/app/features/projects/{__init__.py, service/__init__.py, service/rules.py}`
- Modify: `backend/app/db/models/__init__.py`, `backend/app/db/models/study.py` (`JournalKind` gagne `"project"`)
- Test: `backend/tests/db/test_daily_migration.py`, `backend/tests/features/ledger/test_periods.py`, `backend/tests/features/radar/test_rules.py`, `backend/tests/features/brief/test_rules.py`, `backend/tests/features/projects/test_rules.py`

**Interfaces:**
- Produces:

```python
# db/models/daily.py (types partagés avec les agents : déclarés ici, contrat 6)
ProjectStatus = Literal["brief_pending", "brief_failed", "todo", "reviewing", "to_redo", "validated"]
DraftKind = Literal["cv_line", "profile_entry", "linkedin_post", "readme_plan"]
DraftStatus = Literal["ready", "to_check"]
RadarStatus = Literal["running", "done", "failed"]
RadarTrigger = Literal["schedule", "manual"]
PostingRead = Literal["ok", "blocked", "not_posting", "extract_failed"]
BriefOrigin = Literal["schedule", "opening"]
AdviceStatus = Literal["pending", "ready", "failed", "unavailable"]
JobStatus = Literal["running", "done", "failed", "skipped"]

class Project(UserScopedMixin, Base):    # table projects ; unique (user_id, module_id)
    module_id: str; program_id: str       # String(36), sans FK (le projet survit à une replanification)
    title: str                            # ≤ 200, titre du module jusqu'à l'énoncé
    brief: dict | None                    # ProjectBrief (8.9) sérialisé
    status: ProjectStatus                 # défaut "brief_pending"
    session_id: str | None; brief_attempts: int
    submissions: list[dict]               # [{at, repo_url, description, screenshots: [clés], session_id}], ≤ 10
    evaluation: dict | None               # dernière : {verdict, results, feedback, repo_status, session_id, at}
    drafts: dict                          # kind → {content, entry?, status, flags, edited}
    validated_at: datetime | None; profile_version: int | None
class RadarRun(UserScopedMixin, Base):   # table radar_runs ; index (user_id, created_at)
    role: str; zone: str; role_norm: str; zone_norm: str   # ≤ 120
    trigger: RadarTrigger; period: str | None; status: RadarStatus; session_id: str | None
    queries: int; candidates: int; read_count: int; blocked_count: int; not_postings: int; analyzed: int
    blocked_domains: dict                 # domaine → nombre (jamais journalisé)
    postings: list[dict]                  # [{ref, url, url_key, domain, read, title, company, level, remote,
                                          #   salary, skills: [{name, required}], tools, score}]
    ranking: list[dict]; alerts: list[dict]; previous_id: str | None; finished_at: datetime | None
class Brief(UserScopedMixin, Base):      # table briefs ; unique (user_id, day)
    day: date; origin: BriefOrigin; sections: dict; offer_keys: list[str]
    resource: dict | None; advice: dict | None; advice_status: AdviceStatus; session_id: str | None
class JobRun(UserScopedMixin, Base):     # table jobs ; unique (user_id, name, period) ; index (user_id, name, started_at)
    name: str (≤ 40); period: str (≤ 16); status: JobStatus; started_at: datetime; finished_at: datetime | None
    attempts: int; error_code: str | None (≤ 64); ref_id: str | None; next_due_at: datetime | None

# features/ledger/service/periods.py (pur)
def day_period(day: date) -> str                       # "2026-11-16"
def week_period(day: date) -> str                      # semaine ISO locale : "2026-W47"
def brief_moment(day: date, hhmm: str, zone: ZoneInfo) -> datetime    # local_moment, UTC
def is_stale(started_at: datetime, now: datetime, minutes: int = 30) -> bool
RADAR_WEEKDAY = "monday"; RADAR_TIME = "06:00"; ATS_EVERY_DAYS = 30; MAX_ATTEMPTS = 3

# features/radar/service/rules.py (pur)
MIN_RUN = 30; MAX_RUN = 50; MAX_READS = 60; MAX_CANDIDATES = 80; HIGH_MATCH = 70
ALERT_SHARE = 0.5; ALERT_MIN_POSTINGS = 10; ALERT_MAX = 5; ENRICH_SHARE = 0.3; ENRICH_MAX = 15
@dataclass(frozen=True) class SkillFreq: skill: str; norm: str; count: int; share: float; rank: int
@dataclass(frozen=True) class SkillTrend(SkillFreq): delta_share: float | None; delta_rank: int | None; new: bool
def rank_skills(postings: Sequence[Mapping[str, Any]]) -> list[SkillFreq]
    # postings dont read == "ok" et analysées ; chaque compétence comptée une fois par offre (nom normalisé),
    # nom affiché = forme la plus fréquente ; part = compte / analysées arrondie à 0,01 ; tri compte décroissant
    # puis nom ; rangs 1, 2, 2, 4 (ex æquo)
def evolution(current: Sequence[SkillFreq], previous: Sequence[SkillFreq] | None) -> list[SkillTrend]
    # delta_share en points (×100, arrondi à l'entier), delta_rank = ancien − nouveau ; absente avant : new=True ;
    # previous None : deltas None, new False
def program_alerts(ranking, analyzed: int, in_program: AbstractSet[str],
                   levels: Mapping[str, SkillLevel]) -> list[Alert]     # règle P8 ; Alert(skill, share, message)
def alert_message(share: float) -> str          # « Demandée dans 62 % des offres, absente de ton programme. »
def posting_score(skills: Sequence[Mapping[str, Any]], levels: Mapping[str, SkillLevel]) -> int
    # GapRow(skill, required, levels.get(norm), "to_add", None) puis match_score ; aucune compétence : 0
def salary_shown(salary: str | None, text: str) -> str | None   # gardé si chaque nombre du salaire figure dans text
def enrich_names(ranking: Sequence[SkillFreq]) -> list[str]     # part ≥ 0,3, 15 au plus
def low_sample(read_ok: int) -> bool                            # < MIN_RUN

# features/brief/service/rules.py (pur)
BRIEF_KEYS = ("block", "reviews", "reminders", "offers", "week")   # rubriques du code ; + resource, advice
OFFERS_MAX = 5; REMINDERS_MAX = 5; SHOWN_BRIEFS = 7
def brief_day(now: datetime, zone: ZoneInfo) -> date             # local_today
def brief_due(now: datetime, zone: ZoneInfo, hhmm: str) -> bool   # instant ≥ brief_moment(jour local)
def new_offers(postings: Sequence[Mapping[str, Any]], shown: AbstractSet[str],
               known: AbstractSet[str]) -> list[dict[str, Any]]  # score ≥ 70, url_key hors shown et known,
               # triées score décroissant puis titre, 5 au plus
def advice_numbers(facts: Mapping[str, int | None]) -> set[str]  # nombres permis dans le conseil

# features/projects/service/rules.py (pur)
DESCRIPTION_MAX = 4000; SCREENSHOTS_MAX = 5; SCREENSHOT_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
def submission_problems(repo_url: str | None, description: str | None, screenshots: int) -> list[str]
    # noms de champs : ni lien ni description → ["repo_url", "description"] ; lien non http(s) → ["repo_url"] ;
    # > 5 captures → ["screenshots"]
def verdict(criteria: int, results: Sequence[Mapping[str, Any]]) -> Literal["validated", "to_redo"]
    # un résultat par index 1..criteria, tous met=True → validated ; manquant, en double ou hors bornes : to_redo
def week_started(week_start: date, today: date) -> bool
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_migration_creates_daily_tables(alembic_db): ...   # projects, radar_runs, briefs, jobs ; uniques ; index
def test_brief_day_is_local():
    assert brief_day(datetime(2026, 11, 15, 23, 30, tzinfo=UTC), ZoneInfo("Europe/Paris")) == date(2026, 11, 16)
def test_week_period_local_sunday_night(): ...   # lundi 00 h 30 Paris (dimanche 23 h 30 UTC) : semaine du lundi local
def test_brief_moment_on_dst_day(): ...          # 29/03/2026 07:00 Paris = 05:00 UTC ; 25/10/2026 = 06:00 UTC
def test_brief_due_before_and_after_hour(): ...
def test_rank_skills_counts_once_per_posting():
    r = rank_skills([ok(["Python", "python", "SQL"]), ok(["Python"]), blocked(["Go"])])
    assert [(s.skill, s.count, s.share) for s in r] == [("Python", 2, 1.0), ("SQL", 1, 0.5)]
def test_evolution_points_rank_and_new(): ...    # 40 % → 62 % : +22 pts, rang 5 → 2 : +3 ; absente avant : new
def test_evolution_without_previous(): ...
def test_alerts_need_ten_postings(): ...         # 9 analysées : aucune alerte même à 100 %
def test_alert_skips_program_and_valide(): ...   # dans un module, ou niveau valide : pas d'alerte
def test_alert_message_wording(): assert alert_message(0.62) == "Demandée dans 62 % des offres, absente de ton programme."
def test_posting_score_uses_match_score(): ...   # requise valide + préférée absente : 67
def test_salary_shown_only_if_in_text(): ...     # « 45-55 k€ » absent du texte : None
def test_new_offers_filters_shown_and_known(): ...
def test_submission_needs_link_or_description():
    assert submission_problems(None, "  ", 3) == ["repo_url", "description"]
def test_verdict_needs_every_criterion(): ...    # 4 critères, 3 résultats : to_redo ; index en double : to_redo
```

- [ ] **Step 2: Run, check they fail** — `uv run pytest tests/db/test_daily_migration.py tests/features/ledger tests/features/radar tests/features/brief tests/features/projects -q`.
- [ ] **Step 3: Implement** models, migration `0013` (`down_revision = "0012"`), modules purs ci-dessus (aucun n'importe la base ni une feature hors `gap.service.score` et `core`).
- [ ] **Step 4: Run tests and full back checks** — PASS.
- [ ] **Step 5: Commit** `feat(phase-8): tables du quotidien et règles pures (8.1)` ; D157 (P6 à P9, P13 pour les périodes).

---

### Task 8.2 : Registre des passages, planificateur complet, rafraîchissement ATS — complexe

**Zone : back (`ledger`, `scheduler`, `cv`).** Ne change pas le contrat.

**Files:**
- Create: `backend/app/features/ledger/{repository.py, service/ledger.py}`, `backend/app/features/cv/service/ats_refresh.py`, `backend/app/scheduler/jobs/ats_refresh.py`
- Modify: `backend/app/scheduler/registry.py`, `backend/app/agents/tools/cv_review_port.py` (`ReviewContext.ats_updates`), `backend/app/features/cv/service/review_store.py` (lecture), `backend/app/agents/nodes/ats_reader.py` et `backend/app/agents/prompts/_shared/ats_base.md` (bloc `{% if ats_updates %}`), `backend/app/agents/tools/web_tools.py` (`web_search(..., time_range: str | None = None)`, transmis à la passerelle)
- Test: `backend/tests/features/ledger/test_ledger.py`, `backend/tests/features/cv/test_ats_refresh.py`, `backend/tests/scheduler/test_registry.py`, `backend/tests/agents/graphs/test_cv_review.py` (ajout)

**Interfaces:**
- Produces:

```python
# features/ledger/service/ledger.py
@dataclass(frozen=True) class Claim: run_id: str; attempt: int
async def claim(db, user_id: str, name: str, period: str, now: datetime) -> Claim | None
    # INSERT … ON CONFLICT DO NOTHING ; sinon : done/skipped → None ; running non périmé → None ;
    # failed, ou running périmé (is_stale), et attempts < MAX_ATTEMPTS → UPDATE … WHERE id = :id AND attempts = :old
    # (rowcount 1 → Claim) ; commit par l'appelant
async def finish(db, user_id, run_id, *, status: Literal["done", "skipped"], now, ref_id=None, next_due_at=None) -> None
async def fail(db, user_id, run_id, *, code: str, now) -> None     # code = type d'erreur ou code AppError
async def last_done(db, user_id, name) -> JobRunView | None
async def recent_failures(db, user_id, since: datetime | None, limit: int) -> list[JobRunView]   # pour le fil
async def user_ids(db) -> list[str]   # SEULE lecture sans user_id du registre (comme D18, D91), tâches planifiées

# features/cv/service/ats_refresh.py
ATS_QUERY = "fonctionnement logiciels ATS recrutement Greenhouse Workday Lever Teamtailor nouveautés"
async def run_ats_refresh(session_factory, launcher: SessionLauncher, now: datetime) -> int   # sessions lancées
    # par compte : due si last_done("ats_refresh") absent ou fini il y a ≥ 30 jours ; claim(période = jour local) ;
    # launcher.start(user, "web_research", {"query": ATS_QUERY}, subject_type="ats_refresh") ;
    # finish(ref_id=session, next_due_at=now + 30 j) ; lancement refusé → fail(code)
# cv_review_port.py
@dataclass(frozen=True) class AtsUpdate: title: str; url: str; summary: str; published: str | None
ReviewContext.ats_updates: list[AtsUpdate] = []   # sources « kept » de la dernière session ats_refresh
                                                  # terminée il y a < 60 jours, 3 au plus
```

`JOBS` gagne `JobSpec("ats_refresh", timedelta(hours=6), ats_refresh.run)` ; le module `scheduler/jobs/ats_refresh.py` ne fait que déballer son contexte. Le prompt du Lecteur ATS rend les mises à jour dans `untrusted(…, "base ATS : mises à jour du web")` avec leur date, après la base datée ; sans mise à jour, rien ne change.

- [ ] **Step 1: Write the failing tests**

```python
async def test_claim_once_per_period(db): ...                    # deux claims : un Claim, puis None
async def test_concurrent_claims_one_winner(db_session_factory): ...   # asyncio.gather de 5 claims : 1 gagnant
async def test_failed_is_reclaimed_until_three_attempts(db): ...
async def test_running_reclaimed_only_when_stale(db): ...        # 29 min : None ; 31 min : Claim(attempt=2)
async def test_finish_records_next_due(db): ...
async def test_ats_refresh_due_every_thirty_days(...):
    # passage done il y a 29 jours : rien lancé ; 30 jours : une session web_research, sujet ats_refresh
async def test_ats_refresh_launch_failure_recorded(...): ...     # launcher qui lève : ligne failed, code seul
async def test_review_context_has_recent_ats_updates(...): ...   # 3 sources « kept » au plus, < 60 jours
async def test_ats_updates_are_untrusted_in_prompt(...): ...
def test_registry_lists_every_scheduled_job(): ...               # noms attendus présents (complété en 8.4, 8.6, 8.10)
async def test_ledger_never_logs_data(caplog, ...): ...
```

- [ ] **Step 2: Run, check they fail.**
- [ ] **Step 3: Implement** (repository `UserScopedRepository[JobRun]` + `user_ids`, ledger, ATS, une ligne dans `JOBS`).
- [ ] **Step 4: Run tests and full back checks** — PASS.
- [ ] **Step 5: Commit** `feat(phase-8): registre des passages planifiés et rafraîchissement ATS (8.2)` ; D158 (P13, P14).

---

### Task 8.3 : Parcours `market_radar` (Éclaireur et Analyste) — complexe

**Zone : back (agents, graphe, port).** Ne change pas le contrat.

**Files:**
- Create: `backend/app/agents/tools/radar_schema.py`, `backend/app/agents/tools/radar_port.py` (`RadarStore`, `NO_RADAR`), `backend/app/agents/state/market_radar.py`, `backend/app/agents/nodes/scout/radar.py`, `backend/app/agents/nodes/analyst_radar.py`, `backend/app/agents/graphs/market_radar.py`, `backend/tests/support/radar.py` (`FakeRadarStore`), `backend/tests/agents/graphs/radar_support.py`
- Modify: `agents/prompts/analyst.md` (mode `radar`), `agents/prompts/scout.md` (aucun mode : les requêtes sont du code ; seule la phrase d'intention), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`radar`), `bootstrap_agents.agent_ports` (paramètre `radar: RadarStore = NO_RADAR`), `features/sessions/service.py` (`ROUTE_ONLY["market_radar"] = "POST /radar/runs"`)
- Test: `backend/tests/agents/graphs/test_market_radar.py`, `backend/tests/agents/tools/test_radar_schema.py`

**Interfaces:**

```python
# agents/tools/radar_schema.py
SITE_HINTS = ("jobs.lever.co", "boards.greenhouse.io", "welcometothejungle.com", "jobs.ashbyhq.com")
def radar_queries(role: str, zone: str, languages: Sequence[str]) -> list[str]
    # fr : « offre d'emploi {role} {zone} », « {role} {zone} recrutement CDI » ; en : « {role} job {zone} » ;
    # puis « {role} {zone} site:{hint} » pour chaque hint ; sans doublon, 6 au plus (plafond de session : 12)
class SkillNeedLite(BaseModel): name: str (2..80); required: bool
class RadarItem(BaseModel):
    ref: str (pattern ^p[1-5]$); is_job_posting: bool; title: str | None (≤ 200); company: str | None (≤ 200)
    level: Literal["junior", "confirme", "senior", "lead", "inconnu"]; remote: str | None (≤ 60)
    salary: str | None (≤ 80); skills: list[SkillNeedLite] (≤ 15); tools: list[str] (≤ 15)
class RadarBatch(BaseModel): items: list[RadarItem] (≤ 5)
BATCH = 5; TEXT_MAX = 4000; READ_BATCH = 10; READ_PARALLEL = 5
# agents/tools/radar_port.py
@dataclass(frozen=True) class PostingPage: ref: str; url: str; domain: str; status: Literal["ok", "unreadable"]; text: str
@dataclass(frozen=True) class RadarContext: run_id; role; zone; languages: tuple[str, ...]
    read: list[PostingPage]          # pages déjà lues par ce relevé (rejeu), dans l'ordre de lecture
    extracted: frozenset[str]        # refs déjà extraites (ou en échec d'extraction)
    attempts: int                    # lectures déjà faites (≤ MAX_READS)
@dataclass(frozen=True) class RadarSummary: read_ok: int; blocked: int; not_postings: int; analyzed: int; low_sample: bool
class RadarStore(Protocol):
    async def context(self, user_id: str, run_id: str) -> RadarContext
    async def save_candidates(self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]) -> None
    async def read_posting(self, user_id: str, session_id: str, run_id: str, url: str) -> PostingPage
        # idempotent par (relevé, lien normalisé) : page déjà lue rendue sans relecture ni recompte
    async def save_extraction(self, user_id: str, session_id: str, run_id: str,
                              items: list[RadarItem], failed_refs: list[str]) -> None   # idempotent par ref
    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary     # idempotent
    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None
```

Graphe : `load` → `search` (Éclaireur, sans modèle : `web_search(…, time_range="month")` pour chaque requête de `radar_queries`, liens dédoublonnés par `posting_url_key`, 80 au plus, `save_candidates` ; aucune requête possible → `fail("search_unavailable")`, `run.failed` « La recherche web ne répond pas : relevé impossible pour l'instant. ») → `read` (boucle : relit `context`, prend les 10 prochains liens non lus, les lit par le port, 5 en parallèle, `agent.message` « 24 pages lues : 19 offres, 5 bloquées. » ; reboucle tant que offres lisibles < 50, liens restants et lectures < 60 ; `node_timeout(120)`) → `extract` (boucle : 5 offres `ok` non extraites, Analyste `structured_call(RadarBatch)`, chaque texte dans `untrusted(…, "offre p1")` coupé à 4 000 caractères ; ref inconnue ignorée, outils absents du texte retirés (`contains_term`), salaire passé par `salary_shown` ; lot invalide après les nouveaux essais → refs en `failed_refs` ; reboucle tant qu'il reste des offres) → `finish` (`finalize`, `artifact.ready` `kind = "radar"`, `url = "/carriere/radar/<run_id>"`, `run.completed` « 47 offres lues, 6 bloquées, 41 analysées. » ; `low_sample` : « Seulement 18 offres lisibles : classement indicatif. »). `recursion_limit` fixé au lancement (8.4) au-dessus de 6 + 2 × (60 / 10 + 50 / 5).

- [ ] **Step 1: Write the failing tests**

```python
async def test_radar_reads_extracts_and_finalizes(radar_runner):
    final = await run(radar_runner, pages=postings(12) + blocked(3), analyst=[batch(5), batch(5), batch(2)])
    assert store.summary == RadarSummary(read_ok=12, blocked=3, not_postings=0, analyzed=12, low_sample=True)
    assert analyst_calls == 3 and final.events[-1].type == "run.completed"
def test_queries_built_by_code(): ...              # 6 requêtes au plus, site: présents, aucune donnée inventée
async def test_stops_at_fifty_readable(...): ...   # 70 candidats lisibles : 50 lues, 10 appels de l'Analyste
async def test_stops_at_sixty_reads(...): ...      # 45 bloquées sur 60 : 60 lectures, pas une de plus
async def test_all_blocked_still_reports_counts(...): ...   # 0 lisible, 12 bloquées : run.completed, aucun appel
async def test_search_unavailable_fails_readably(...): ...
async def test_not_a_posting_counted_apart(...): ...
async def test_tool_not_in_text_dropped_and_salary_checked(...): ...
async def test_invalid_batch_marks_refs_failed_and_continues(...): ...
async def test_postings_are_untrusted(...): ...
async def test_replay_mid_read_never_rereads(...): ...       # redémarrage après 20 lectures : 50 lectures en tout
async def test_replay_mid_extract_never_reextracts(...): ...
async def test_radar_never_logs_urls_or_text(caplog, ...): ...
```

- [ ] **Step 2–4:** fail, implement, pass (contrôles back complets).
- [ ] **Step 5: Commit** `feat(phase-8): parcours du radar du marché (8.3)` ; D159 (P5, P6).

---

### Task 8.4 : Feature `radar` : port réel, routes, relevé hebdomadaire, demande du marché (contrat) — complexe

**Zone : back.** Change le contrat.

**Files:**
- Create: `backend/app/features/radar/{repository.py, schemas.py, router.py}`, `service/{runtime.py, runs.py, store.py, finalize.py, demand.py, schedule.py, views.py}`, `backend/app/bootstrap_daily.py`, `backend/app/scheduler/jobs/market_radar.py`
- Modify: `backend/app/features/registry.py`, `backend/app/main.py` (composition par `bootstrap_daily`, appels d'une ligne), `backend/app/bootstrap_agents.py` (`scheduler_context(..., daily)`), `backend/app/scheduler/{base.py, registry.py}` (`JobContext.daily`), `backend/app/features/settings/schemas.py` (`radar_role: str = Field("", max_length=120)`, `radar_zone: str = Field("France", max_length=120)`), `backend/app/features/skills/map.py` (`demand`), `pyproject.toml` (contrat 5 : `app.bootstrap_daily`)
- Test: `backend/tests/features/radar/{conftest.py, test_runs.py, test_store.py, test_finalize.py, test_router.py, test_schedule.py, test_logs.py}`, `backend/tests/features/skills/test_map.py` (ajout), `backend/tests/test_bootstrap_daily.py`

**Interfaces:**

```text
POST /radar/runs  RadarRunIn {role?: str (2..120), zone?: str (2..120)}   → 202 {run_id, session_id}
     409 radar_in_progress (details.run_id) ; 409 radar_role_required ; 422 fields
GET  /radar/latest                     → RadarLatestOut {defaults: {role, zone}, running: RunRef | None, latest: RadarRunOut | None}
GET  /radar/runs                       → list[RadarRunSummary] (récent d'abord, 20)
GET  /radar/runs/{id}                  → RadarRunOut
```

```python
class RadarRunOut(BaseModel): id; role; zone; status: RadarStatus; trigger; created_at; finished_at
    read_count; blocked_count; not_postings; analyzed; low_sample: bool
    blocked_domains: list[DomainCount]            # [{domain, count}], décroissant
    ranking: list[TrendOut]                       # skill, count, share, rank, delta_share, delta_rank, new
    alerts: list[AlertOut]                        # skill, share, message
    offers: list[OfferOut]                        # url, title, company, level, remote, salary, score ; score décroissant
    previous: RunRef | None
# service/runtime.py
@dataclass class RadarRuntime: session_factory; launcher; research: ResearchRuntime; now: Callable[[], datetime]; locks: KeyLocks
async def start_run(rt, user_id, body: RadarRunIn, *, trigger: RadarTrigger, period: str | None) -> RunStarted
async def run_weekly_radar(rt, now: datetime) -> int     # tâche planifiée, par compte (user_ids du registre)
# service/demand.py (n'importe ni skills ni un module qui l'importe)
async def latest_demand(db, user_id) -> dict[str, float]  # nom normalisé → part du dernier relevé done
# bootstrap_daily.py
@dataclass(frozen=True) class DailyRuntimes: radar: RadarRuntime; radar_store: RadarStore   # brief, projects : 8.6, 8.10
def daily_runtimes(session_factory, launcher, *, research: ResearchRuntime, career: CareerRuntimes, study: StudyRuntimes) -> DailyRuntimes
```

Règles :
1. **Lancement** sous le verrou des relevés de l'utilisatrice : un relevé `running` dont la session est ouverte → 409 ; dont la session est close → `failed` d'abord (le statut suit la session, comme D129 n° 5). `role`/`zone` fournis : enregistrés dans les réglages ; sinon défauts de P10. Session `market_radar`, sujet `radar_run`, `recursion_limit` du lancement fixé (D159).
2. **Lecture** (`read_posting`) : `research.service.reading.read(runtime, user_id, None, url)` (cache 7 jours, débit par domaine, garde SSRF, domaines exclus jamais lus et comptés bloqués) ; refs `p1`, `p2`… dans l'ordre ; `blocked_domains` tenu à jour ; plus de 60 lectures → refusé par le port.
3. **Finalisation** : `rank_skills`, `evolution` contre le dernier `done` de même poste et zone normalisés, `program_alerts` (modules non sauté du programme validé par `skill_weeks`, niveaux `SkillsService.known_levels`), `posting_score` par offre, `SkillsService.upsert_catalog(enrich_names(...))` sans niveau, statut `done`, `finished_at`.
4. **Hebdomadaire** : tâche `market_radar` toutes les 15 min, au démarrage ; par compte : lundi ≥ 06:00 locale, `claim(…, "market_radar", week_period(jour local))` ; un relevé créé cette semaine ou aucun poste → `finish(status="skipped")` ; sinon `start_run(trigger="schedule")`, `finish(ref_id=run_id, next_due_at=lundi suivant 06:00)`.
5. **Carte** : `skill_graph` remplit `demand` par `latest_demand` (0 à 1), `None` sans relevé.

- [ ] **Step 1: Write the failing tests**

```python
async def test_start_run_202_then_409(client): ...
async def test_role_required_without_goal_or_setting(client): ...   # 409 radar_role_required
async def test_role_and_zone_saved_in_settings(client): ...
async def test_read_posting_idempotent_and_capped(...): ...         # même lien deux fois : une lecture ; 61e : refusé
async def test_excluded_domain_counted_blocked(...): ...
async def test_finalize_ranking_evolution_alerts(...):
    run2 = await finalized(previous=run1)
    assert run2.ranking[0].delta_share == 22 and run2.alerts[0].message.startswith("Demandée dans")
async def test_low_sample_flag(...): ...                            # 18 lisibles : low_sample True
async def test_enrich_catalog_without_level(...): ...
async def test_weekly_once_per_local_week(...): ...                 # deux passages lundi : un relevé ; dimanche : aucun
async def test_weekly_skipped_after_manual_run(...): ...
async def test_dead_session_marks_run_failed(...): ...
async def test_skill_map_demand_from_latest_run(client): ...
async def test_other_user_run_404(...): ...
async def test_422_never_echoes_role(client): ...
async def test_radar_data_never_logged(caplog, ...): ...            # rôle, zone, liens, domaines, titres absents
```

- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-8): relevés du radar, tâche hebdomadaire et demande du marché (8.4)` ; D160 (P9, P10).

---

### Task 8.5 : Parcours `daily_brief` (ressource et conseil) — complexe

**Zone : back (agents, graphe, port).** Ne change pas le contrat.

**Files:**
- Create: `backend/app/agents/tools/brief_schema.py`, `backend/app/agents/tools/brief_port.py` (`BriefStore`, `NO_BRIEF`), `backend/app/agents/state/daily_brief.py`, `backend/app/agents/nodes/scout/brief_resource.py`, `backend/app/agents/nodes/moderator_brief.py`, `backend/app/agents/graphs/daily_brief.py`, `backend/tests/support/brief.py` (`FakeBriefStore`), `backend/tests/agents/graphs/brief_support.py`
- Modify: `agents/prompts/scout.md` (mode `brief_resource`), `agents/prompts/moderator.md` (mode `brief`), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`brief`), `bootstrap_agents.agent_ports`, `features/sessions/service.py` (`ROUTE_ONLY["daily_brief"] = "GET /brief/today"`)
- Test: `backend/tests/agents/graphs/test_daily_brief.py`

**Interfaces:**

```python
# agents/tools/brief_schema.py
class ResourcePick(BaseModel): index: int | None = Field(ge=1, le=8); why: str = Field(max_length=200)
class CouncilAdvice(BaseModel): sentences: list[str] = Field(min_length=2, max_length=2)   # 10 à 240 caractères chacune
@dataclass(frozen=True) class ResourceView: title: str; url: str; domain: str; published: str | None; why: str
def numbers_in_advice(sentences: Sequence[str]) -> set[str]      # via cv_lexicon.numbers_in
# agents/tools/brief_port.py
@dataclass(frozen=True) class AdviceFacts: block_title: str | None; block_minutes: int; cards_due: int;
    reminders_due: int; offers: int; best_score: int | None; week_planned: int; week_done: int; streak_days: int
@dataclass(frozen=True) class BriefContext: brief_id; day: date; language: Literal["fr", "en"]; topic: str | None
    facts: AdviceFacts; resource_done: bool; advice_done: bool; allowed_numbers: frozenset[str]
class BriefStore(Protocol):
    async def context(self, user_id: str, brief_id: str) -> BriefContext
    async def save_resource(self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None) -> None
    async def save_advice(self, user_id: str, session_id: str, brief_id: str, sentences: list[str] | None) -> None
        # idempotents : la première écriture gagne ; None = rubrique vide (ressource) ou conseil `failed`
```

Graphe : `load` → `resource` (si `resource_done` : sauté ; sans `topic` : `save_resource(None)` ; sinon `web_search(topic, time_range="month")`, 8 premiers résultats dans `untrusted(…, "résultats")`, Éclaireur `ResourcePick` ; le code lit la page choisie (`web_read`), illisible → résultats suivants dans l'ordre, 3 lectures au plus, sans nouvel appel ; aucune → `None` ; panne de recherche → `None`, le parcours continue) → `advice` (si `advice_done` : sauté ; Modérateur, faits du jour rendus en phrases par le code dans `untrusted(…, "faits du jour")`, `CouncilAdvice` ; un nombre hors `allowed_numbers` → un nouvel essai qui nomme le nombre, puis `save_advice(None)`) → `close` (`run.completed` « Brief du jour prêt. »). Aucune exception d'une rubrique n'empêche l'autre.

- [ ] **Step 1: Write the failing tests**

```python
async def test_brief_graph_two_calls(brief_runner):
    final = await run(brief_runner, scout=[pick(2)], moderator=[advice("Commence par ton bloc de 45 minutes.", "Puis 12 fiches.")])
    assert store.resource.url == hits[1].url and store.advice == [...] and model_calls == 2
async def test_unreadable_pick_falls_back_without_new_call(...): ...
async def test_no_topic_no_resource(...): ...
async def test_search_down_keeps_advice(...): ...
async def test_advice_number_not_in_facts_retries_then_fails(...): ...   # « 3 heures » inventé deux fois : advice None
async def test_facts_and_results_are_untrusted(...): ...
async def test_replay_after_resource_skips_it(...): ...    # redémarrage avant le conseil : pas de second appel à l'Éclaireur
async def test_brief_graph_never_logs_texts(caplog, ...): ...
```

- [ ] **Step 2–4:** fail, implement, pass.
- [ ] **Step 5: Commit** `feat(phase-8): parcours du brief du matin, ressource et conseil (8.5)` ; D161 (P11).

---

### Task 8.6 : Feature `brief` : rubriques, ouverture, tâche du matin (contrat) — complexe

**Zone : back.** Change le contrat.

**Files:**
- Create: `backend/app/features/brief/{repository.py, schemas.py, router.py}`, `service/{runtime.py, sections.py, ensure.py, store.py, schedule.py, views.py}`, `backend/app/scheduler/jobs/daily_brief.py`
- Modify: `backend/app/bootstrap_daily.py` (`brief`, `brief_store`), `backend/app/main.py` (une ligne de port), `backend/app/scheduler/registry.py`, `backend/app/features/registry.py`, `backend/app/features/radar/service/views.py` (`offers_since(db, user_id, since) -> list[dict]`)
- Test: `backend/tests/features/brief/{conftest.py, test_sections.py, test_ensure.py, test_store.py, test_router.py, test_schedule.py, test_logs.py}`

**Interfaces:**

```text
GET /brief/today   → BriefOut (crée le brief du jour local s'il manque ; n'attend jamais un agent)
```

```python
class BriefOut(BaseModel): id; day: date; origin: BriefOrigin; generated_at: datetime
    block: BlockRubric | None             # module_title, lesson_id, lesson_title, minutes, tasks: [{title, minutes}]
    reviews: ReviewsRubric                # queue: int (fiches de la file du jour), remaining: int
    reminders: RemindersRubric            # due: int, items: [{reminder_id, application_id, company, title, kind, due_on}] ≤ 5
    offers: OffersRubric                  # run_id | None, items: [{url, title, company, score}] ≤ 5
    week: WeekRubric | None               # planned_minutes, done_minutes, tasks_done, tasks_total, study_minutes, streak_days
    resource: ResourceOut | None          # title, url, domain, published, why
    advice: list[str] | None; advice_status: AdviceStatus; session_id: str | None
# service/runtime.py
@dataclass class BriefRuntime: session_factory; launcher; quiz: QuizRuntime; study: StudyRuntime;
    applications: ApplicationsRuntime; now: Callable[[], datetime]
async def build_sections(rt, db, user_id, today: date) -> dict[str, Any]   # rubriques du code (BRIEF_KEYS)
async def ensure_today(rt, user_id, *, origin: BriefOrigin) -> tuple[BriefOut, bool]   # (brief, créé ?)
async def run_daily_briefs(rt, now: datetime) -> int     # tâche planifiée
```

Règles :
1. **Création** : jour = `brief_day(now, fuseau)` ; rubriques par `build_sections` (bloc `block_of_day`, révisions `due_queue`, relances `list_reminders(due=True)`, offres `new_offers` sur `offers_since(dernier brief)` avec `shown` = `offer_keys` des 7 derniers briefs et `known` = liens normalisés des offres et fiches, semaine `week_facts` du programme validé le plus récent et série de `summary`) ; insertion `ON CONFLICT (user_id, day) DO NOTHING` ; seul l'inserteur lance la session `daily_brief` (sujet `brief`) et pose `session_id` ; lancement refusé (moteur absent, aucune clé) → `advice_status = "unavailable"`, rubriques du code intactes.
2. **Statut du conseil** : `pending` tant que la session vit ; session close sans conseil → `failed` à la lecture ; `save_advice(None)` → `failed`.
3. **Tâche `daily_brief`** (10 min, au démarrage) : par compte, `brief_due` → `claim(…, "daily_brief", day_period(jour))` → `ensure_today(origin="schedule")` → `finish(status="done" si créé, "skipped" sinon, next_due_at = demain à l'heure du brief)`.
4. **Port réel** (`AgentBriefStore`) : `context` relit le brief (faits du conseil tirés des rubriques ; `topic` = « {poste visé} actualités » ou `None`) ; écritures conditionnelles (`WHERE resource IS NULL` / `advice IS NULL`).
5. Journaux : brief, jour, compteurs ; jamais une rubrique, une ressource ou une phrase.

- [ ] **Step 1: Write the failing tests**

```python
async def test_get_today_creates_with_all_rubrics(client):
    b = (await client.get("/api/v1/brief/today")).json()
    assert set(b) >= {"block", "reviews", "reminders", "offers", "week", "resource", "advice"} and b["origin"] == "opening"
async def test_concurrent_ensure_creates_one_brief(rt): ...   # 5 ensure_today en parallèle : 1 ligne, 1 session
async def test_second_get_same_brief_no_new_session(client): ...
async def test_job_after_opening_does_nothing(rt): ...        # ouverture 6 h 30, tâche 7 h 05 : passage skipped
async def test_job_creates_after_hour_only(rt): ...           # 6 h 55 : rien ; 7 h 05 : origin schedule
async def test_brief_without_llm_has_code_rubrics(client): ...   # lanceur qui lève : advice_status unavailable
async def test_dead_session_marks_advice_failed(client): ...
async def test_due_reminder_listed(client): ...               # fiche postulée il y a 8 jours : 1 relance due
async def test_offers_new_since_last_brief_only(rt): ...
async def test_week_progress_from_validated_program(rt): ...
async def test_yesterday_brief_replaced_by_today_at_opening(client): ...   # brief de la veille : nouveau jour créé
async def test_other_user_brief_isolated(...): ...
async def test_brief_data_never_logged(caplog, ...): ...
```

- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-8): brief du matin, à l'ouverture et à l'heure réglée (8.6)` ; D162 (P11, P12).

---

### Task 8.7 : Fil d'activité (contrat) — simple

**Zone : back.** Change le contrat.

**Files:**
- Create: `backend/app/features/activity/{__init__.py, schemas.py, router.py, service/__init__.py, service/sources.py, service/feed.py}`
- Modify: `backend/app/features/registry.py` ; fonctions de lecture ajoutées aux services : `lessons.service` (`recent_lessons`), `radar.service.views` (`recent_runs`), `brief.service.views` (`recent_briefs`), `memory.service` (`recent_agent_writes`), `ledger.service.ledger.recent_failures` (8.2)
- Test: `backend/tests/features/activity/{test_feed.py, test_router.py}`

**Interfaces:**

```python
ActivityKind = Literal["lesson", "radar", "brief", "memory", "project", "job_failed"]
class ActivityItem(BaseModel): id: str; kind: ActivityKind; at: datetime; title: str; detail: str | None; link: str | None
class ActivityPage(BaseModel): items: list[ActivityItem]; latest_at: datetime | None
ActivitySource = Callable[[AsyncSession, str, datetime | None, datetime | None, int], Awaitable[list[ActivityItem]]]
ACTIVITY_SOURCES: tuple[ActivitySource, ...]   # (db, user_id, after, before, limit) ; une ligne par source
async def activity_page(db, user_id, *, after: datetime | None, before: datetime | None, limit: int) -> ActivityPage
    # fusion triée par `at` décroissant, `limit` (≤ 50, défaut 30) ; id stable « {kind}:{ref}:{état} »
```

`GET /activity?after=&before=&limit=` → `ActivityPage`. Libellés (code, sans contenu inventé) : « Leçon prête : {titre} » / « Leçon en échec : {titre} » (lien `/apprendre/lecons/{id}`), « Relevé du radar : 47 offres lues, 6 bloquées » (`/carriere/radar/{id}`), « Brief du jour prêt » (`/`), « {Agent} a écrit en mémoire : {titre de l'élément} » (raison en `detail`, auteur ≠ `user`), « Un passage planifié a échoué ({nom lisible}) : nouvel essai au prochain passage. ». La source `project` est ajoutée par 8.10.

- [ ] **Step 1: Write the failing tests** — `test_feed_merges_sources_by_time`, `test_after_returns_only_newer`, `test_before_pages_older`, `test_user_writes_excluded`, `test_job_failure_item_has_no_error_text`, `test_limit_capped_at_50`, `test_activity_isolated_by_user`, `test_activity_never_logged`.
- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-8): fil d'activité des agents en tâche de fond (8.7)` ; D163 (P15).

---

### Task 8.8 : Essai réel en milieu de phase (contrôleur)

**Zone : contrôleur (pile Docker, GLM 5.3 flash, SearXNG).** Aucun écran. Correctifs back faits dans cette tâche.

- [ ] **Step 1:** reconstruire l'image du back, `docker compose up -d --no-build backend frontend`, `date` vérifiée.
- [ ] **Step 2:** écrire `backend/scripts/check_phase8.py` et `scripts/{phase8_radar.py, phase8_brief.py, phase8_rules.py}` (même forme que `check_phase7` : `Run`, `CheckFailed`, une ligne par étape, aucune donnée imprimée ; conteneur jetable `learning_career_platform-check8`, `--api http://backend:8000 --part … --logs-file -`), tests dans `backend/tests/scripts/test_check_phase8.py`. Parties :
  - `planifie` (**à lancer avant toute ouverture de l'accueil du jour**) : `PUT /settings` met l'heure du brief 3 minutes plus tard ; le script relit `GET /activity` (qui ne crée rien) jusqu'à l'élément « Brief du jour prêt » (10 min au plus), puis `GET /brief/today` : `origin == "schedule"` ; l'heure d'origine est remise.
  - `radar` (`POST /radar/runs` avec un poste et une zone fictifs génériques, « Développeur Python », « Lyon ») : relevé `done` en 15 min au plus, `read_count + blocked_count` ≤ 60, `read_count` = nombre d'offres `ok`, classement non vide si `analyzed > 0`, chaque salaire rapporté présent dans la page relue, `low_sample` cohérent, second `POST` pendant le relevé → 409 ; durée, appels (`llm_calls`), coût affichés.
  - `brief` : `GET /brief/today` a les 7 rubriques ; conseil `ready` en 3 min au plus, 2 phrases, chaque nombre présent dans les rubriques ; ressource avec un lien lu ou `null` ; second `GET` même `id` ; `journaux`.
- [ ] **Step 3:** deux essais réels de chaque partie ; noter durées, coûts, pages lues et bloquées par essai (nombres seulement), offres ≥ 70 ; ajuster `SITE_HINTS` ou les requêtes si moins de 30 offres lisibles (écart noté).
- [ ] **Step 4:** correctifs back éventuels (un test qui échoue avant), contrôles back complets.
- [ ] **Step 5: Commit** `feat(scripts): contrôle réel de la phase 8, radar et brief (8.8)` ; D164 (résultats chiffrés).

---

### Task 8.9 : Praticien : énoncé et évaluation des projets (`project_brief`, `project_review`) — complexe

**Zone : back (agents, graphes, port).** Ne change pas le contrat.

**Files:**
- Create: `backend/app/agents/tools/project_schema.py`, `backend/app/agents/tools/project_port.py` (`ProjectStore`, `NO_PROJECTS`), `backend/app/agents/state/{project_brief.py, project_review.py}`, `backend/app/agents/nodes/practitioner/{__init__.py, brief.py, evaluate.py, drafts.py}`, `backend/app/agents/graphs/{project_brief.py, project_review.py}`, `backend/tests/support/projects.py` (`FakeProjectStore`), `backend/tests/agents/graphs/project_support.py`
- Modify: `agents/prompts/practitioner.md` (modes `project_brief`, `project_review`, `project_drafts`), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`projects`), `bootstrap_agents.agent_ports`, `features/sessions/service.py` (`ROUTE_ONLY["project_brief"] = "planificateur ou POST /projects/{id}/brief"`, `ROUTE_ONLY["project_review"] = "POST /projects/{id}/submit"`)
- Test: `backend/tests/agents/graphs/{test_project_brief.py, test_project_review.py}`, `backend/tests/agents/tools/test_project_schema.py`

**Interfaces:**

```python
# agents/tools/project_schema.py
class ProjectBrief(BaseModel):
    title: str (3..120); context: Prose (≤ 120 mots); objective: Prose (≤ 60 mots)
    constraints: list[str] (2..5, ≤ 160 chacune); criteria: list[str] (3..6, ≤ 200 chacun)
    hours: int = Field(ge=3, le=6); deliverable: Literal["repo", "description", "either"]
class CriterionResult(BaseModel): index: int (≥ 1); met: bool; comment: str (≤ 300)
class ProjectEvaluation(BaseModel): results: list[CriterionResult] (≤ 6); feedback: Prose (≤ 200 mots)
class ProfileEntryDraft(BaseModel): name: str (1..120); description: str (≤ 600); achievements: list[str] (≤ 4, ≤ 200)
class ProjectDrafts(BaseModel): cv_line: str (≤ 200); profile_entry: ProfileEntryDraft
    linkedin_post: Prose (80 à 200 mots, compté par le code); readme_plan: list[str] (5..10, ≤ 120)
def project_fact(title: str, description: str | None, skills: Sequence[str], repo_url: str | None) -> Project
def project_reference(profile: MasterProfileData | None, fact: Project, skills: Sequence[str]) -> MasterProfileData
    # profil validé (ou identité vide) + le fait de projet + les compétences du module (SkillFact)
def draft_text(kind: DraftKind, drafts: ProjectDrafts) -> str     # texte contrôlé de chaque brouillon
# agents/tools/project_port.py
@dataclass(frozen=True) class BriefInputs: module_title; skills: list[str]; prerequisites: list[str];
    lesson_excerpt: str | None (≤ 3 000); week_deliverable: str | None; role: str | None; language: Literal["fr", "en"]
@dataclass(frozen=True) class ReviewInputs: title; brief: ProjectBrief; repo_url: str | None; description: str | None;
    screenshots: int; skills: list[str]; profile: MasterProfileData | None; language
@dataclass(frozen=True) class DraftResult: kind: DraftKind; content: str; entry: ProfileEntryDraft | None;
    status: DraftStatus; flags: list[str]
@dataclass(frozen=True) class ReviewOutcome: verdict: Literal["validated", "to_redo"]; results: list[CriterionResult];
    feedback: str; repo_status: Literal["read", "unreadable", "none"]; drafts: list[DraftResult] | None
class ProjectStore(Protocol):
    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs
    async def save_brief(self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief) -> None
    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None
    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs
    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None   # point d'accroche phase 14
    async def save_review(self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome) -> None
        # idempotents par session
```

`project_brief` : `load` → `write` (Praticien, `structured_call(ProjectBrief)`, titre du module, compétences, extrait de leçon et livrable de la semaine dans `untrusted(…)`, 3 à 6 critères vérifiables par un relecteur) → `save` → fin ; sortie invalide → `brief_failed("structured_output_invalid")`, `run.failed` lisible.

`project_review` : `load` → `read_repo` (lien → `repo_text` (une page, texte coupé à 8 000 caractères) ; illisible → `unreadable`) → **sans description ni dépôt lisible : `to_redo` sans appel au modèle**, feedback « Je n'ai pas pu lire ton dépôt : ajoute une description de ce que tu as fait. » → `evaluate` (Praticien, énoncé et critères numérotés, description de January et README dans `untrusted`, mention des captures non lues ; verdict par `verdict()` du code) → validé : `drafts` (Praticien `ProjectDrafts`, puis `text_claims(draft_text(kind), project_reference(...), allowed=[titre de l'énoncé])` pour chacun ; un brouillon avec des termes → **un** nouvel essai qui nomme tous les termes ; restent des termes → ce brouillon `to_check` avec `flags` ; post LinkedIn hors 80–200 mots après l'essai → `to_check`) → `save` → `announce` (`artifact.ready` `kind = "project"`, `url = "/competences/portfolio/<id>"` ; `run.completed` « Projet validé : 4 brouillons prêts, 1 à vérifier. » ou « Projet à reprendre : 2 critères sur 5 non atteints. »).

- [ ] **Step 1: Write the failing tests**

```python
async def test_brief_has_criteria_and_hours(brief_runner): ...      # 3 à 6 critères, 3 à 6 heures, enregistré une fois
async def test_brief_inputs_untrusted(...): ...
async def test_brief_invalid_output_marks_failed(...): ...
async def test_all_criteria_met_validates_and_drafts(review_runner):
    final = await run(review_runner, evaluation=all_met(4), drafts=[clean_drafts()])
    assert store.outcome.verdict == "validated" and len(store.outcome.drafts) == 4
async def test_one_criterion_missing_is_to_redo_without_drafts(...): ...
async def test_missing_result_is_to_redo(...): ...                 # 4 critères, 3 résultats
async def test_unreadable_repo_without_description_skips_model(...): ...   # 0 appel, to_redo, feedback fixe
async def test_unreadable_repo_with_description_evaluates(...): ...  # repo_status unreadable, prompt le dit
async def test_drafts_with_unsupported_claim_retry_then_flag(...):
    # post « 10 000 utilisateurs, déployé sur Kubernetes » deux fois → linkedin_post to_check, flags {"10 000", "Kubernetes"}
async def test_description_tools_are_allowed_in_drafts(...): ...   # « FastAPI » dit par January : pas de flag
async def test_readme_terms_not_a_reference(...): ...              # outil vu seulement dans le README : flag
async def test_replay_saves_review_once(...): ...
async def test_project_texts_never_logged(caplog, ...): ...
```

- [ ] **Step 2–4:** fail, implement, pass.
- [ ] **Step 5: Commit** `feat(phase-8): Praticien, énoncé et évaluation des projets preuves (8.9)` ; D165 (P1 à P4).

---

### Task 8.10 : Feature `projects` : port réel, rendus, brouillons, profil maître (contrat) — complexe

**Zone : back.** Change le contrat.

**Files:**
- Create: `backend/app/features/projects/{repository.py, schemas.py, router.py}`, `service/{runtime.py, briefs.py, submit.py, store.py, drafts.py, profile_entry.py, screenshots.py, views.py}`, `backend/app/scheduler/jobs/project_briefs.py`
- Modify: `backend/app/bootstrap_daily.py` (`projects`, `project_store`), `backend/app/main.py` (une ligne de port), `backend/app/core/body_limits.py` (`/projects`, 5 × 5 Mo + 1 Mo), `backend/app/scheduler/registry.py`, `backend/app/features/registry.py`, `backend/app/features/activity/service/sources.py` (ligne `project`)
- Test: `backend/tests/features/projects/{conftest.py, test_briefs.py, test_submit.py, test_store.py, test_drafts.py, test_profile_entry.py, test_router.py, test_logs.py}`

**Interfaces:**

```text
GET   /projects?status=                       → list[ProjectSummary] (programme, semaine, rang)
GET   /projects/{id}                          → ProjectOut
POST  /projects/{id}/submit  (multipart : repo_url?, description?, screenshots[] ≤ 5)  → 202 {session_id}
      409 project_not_ready (énoncé absent) ; 409 review_in_progress (details.session_id) ;
      409 project_validated ; 422 fields (submission_problems, image non PNG/JPEG/WebP) ; 413
GET   /projects/{id}/screenshots/{n}          → image (type d'origine, no-store)
PATCH /projects/{id}/drafts/{kind}  {content: str ≤ 3 000 | entry: ProfileEntryIn}   → ProjectOut
POST  /projects/{id}/profile-entry  ProfileEntryIn {name, description, achievements}   → ProjectOut
      409 project_not_validated ; 409 entry_already_added ; 409 profile_required ; 409 profile_draft_pending ; 409 profile_projects_full
POST  /projects/{id}/brief                    → 202 {session_id} ; 409 brief_not_failed
```

```python
class ProjectOut(BaseModel): id; module_id; program_id; title; status: ProjectStatus; brief: ProjectBriefOut | None
    submissions: list[SubmissionOut]          # at, repo_url, description, screenshots: int (dernier d'abord)
    evaluation: EvaluationOut | None          # verdict, results [{index, criterion, met, comment}], feedback, repo_status
    drafts: list[DraftOut]                    # kind, status, content, entry, flags, edited (ordre fixe)
    validated_at; profile_version: int | None; session_id: str | None
@dataclass class ProjectsRuntime: session_factory; launcher; storage: FileStorage; memory: MemoryRuntime;
    cv: CvRuntime; research: ResearchRuntime; now; locks: KeyLocks
async def ensure_project_briefs(rt, now: datetime) -> int   # tâche planifiée
```

Règles :
1. **Énoncés** (`project_briefs`, 15 min, au démarrage) : pour chaque programme validé (lecture sans `user_id` de D91), modules non sautés dont la semaine a commencé (`week_started`) → projet créé (`ON CONFLICT (user_id, module_id) DO NOTHING`) et session `project_brief` lancée par l'inserteur ; `brief_pending` à session close sans énoncé → nouvel essai (3 au plus) puis `brief_failed`.
2. **Rendu** sous le verrou du projet : captures vérifiées par leurs octets de tête (signature PNG, JPEG, WebP), rangées (`storage.save(user_id, "projects", data, suffix)`), rendu ajouté à `submissions` ; `reviewing` + session `project_review` ; lancement refusé → rendu retiré, 503 lisible ; le statut suit la session (close sans évaluation → retour à `todo` ou `to_redo`).
3. **Port réel** : `repo_text` = `research.service.reading.read` (une page) ; `save_review` : `evaluation`, `drafts` ; validé → `validated_at`, `SkillsService.raise_levels(compétences du module, "prouve", evidence("project", id, "Projet « {titre} » validé ({jj/mm})", now))`, `reflect_skill_levels(…, author="practitioner")` hors transaction, journal `kind="project"` (`ref_key = f"project:{id}"`) ; rejoué : rien de plus.
4. **Brouillons** : `PATCH` → `edited = true` ; un brouillon `to_check` modifié est recontrôlé par `text_claims` (même référence) : `flags` mis à jour, `ready` si vide.
5. **Entrée au profil** : seulement par `POST /profile-entry` (texte de January, éventuellement modifié) : nouvelle version validée par `save_profile` avec un `Project(name, description, link=repo_url, achievements, sources=["january"])` ajouté ; `profile_version` posé ; jamais à la validation, jamais par le Praticien.
6. Source du fil : « Projet validé : {titre} » / « Projet à reprendre : {titre} » (lien `/competences/portfolio/{id}`).

- [ ] **Step 1: Write the failing tests**

```python
async def test_week_start_creates_project_and_brief_session(rt): ...   # deux passages : un projet, une session
async def test_skipped_module_gets_no_project(rt): ...
async def test_brief_failed_after_three_attempts_then_retry_route(client): ...
async def test_submit_202_and_review_in_progress_409(client): ...
async def test_submit_only_screenshots_is_422(client): ...      # fields ["repo_url", "description"], sans écho
async def test_fake_png_is_422(client): ...                     # extension .png, octets texte
async def test_validated_project_refuses_resubmit(client): ...
async def test_validation_raises_module_skills_to_prouve(rt):
    await store.save_review(user, sid, pid, validated_outcome())
    assert levels["python"] == "prouve" and evidence_kinds("python") >= {"project"}
async def test_failed_cards_do_not_demote_prouve(rt): ...       # deux échecs de fiches : prouve reste
async def test_save_review_replay_writes_once(rt): ...
async def test_patch_to_check_draft_rechecked(client): ...
async def test_profile_unchanged_until_explicit_entry(client):
    # projet validé : profil v3 inchangé ; POST profile-entry : v4 avec le projet, source january
async def test_entry_already_added_409(client): ...
async def test_screenshot_route_serves_image(client): ...
async def test_other_user_project_404(client): ...
async def test_projects_never_logged(caplog, ...): ...          # description, lien, critère, brouillon, nom de capture absents
```

- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-8): projets preuves, Portfolio et entrée au profil maître (8.10)` ; D166 (P1 à P3).

---

### Task 8.11 : Correctifs d'ouverture (front) — simple

**Zone : front (`applications`, `cv`).** Ne change pas le contrat.

**Files:**
- Modify: les pages et composants concernés de `frontend/src/features/applications/` (titres, `ReminderCard`, `KanbanBoard`, `NewApplication`, `IntakeRun`), `features/applications/components/VerdictPanel` (`ChangeList`), la règle ESLint `*Testkit` (`frontend/eslint.config.*`), `shared/i18n/messages/applications.ts`
- Test: les `*.test.tsx` voisins

Points : niveaux de titres cohérents (un `h1` par page, puis `h2`) ; boutons d'une relance désactivés pendant l'action (`aria-busy`) ; `ChangeList` redondant retiré ; cast qui contourne le typage remplacé par un garde de type ; `maxLength` 200 sur entreprise et intitulé ; clés React par identifiant, plus par texte ; exception ESLint `*Testkit` limitée aux fichiers de test ; Kanban sans défilement horizontal à 1 024 px (colonnes repliables ou défilement interne au tableau, la page ne défile pas) ; nom accessible de la pastille « Relances, 1 relance due » (sans espace avant la virgule) ; effet d'invalidation de `IntakeRun` sur une dépendance stable.

- [ ] **Step 1: Write the failing tests** — `one h1 per applications page`, `reminder buttons disabled while pending`, `company and title capped at 200`, `kanban fits 1024 px`, `badge accessible name`, `intake invalidation runs once per event`.
- [ ] **Step 2–4:** fail, implement, pass (`vitest`, `lint`, `typecheck`).
- [ ] **Step 5: Commit** `fix(phase-8): correctifs d'ouverture du front (8.11)` ; D167.

---

### Task 8.12 : Composants présentationnels du quotidien — simple

**Zone : front, présentationnel** (ni `schema.d.ts` ni `shared/api`).

**Files (un dossier par composant : `.tsx`, `.test.tsx`, `index.ts`):**
- Create: `frontend/src/features/home/components/{BriefHeader, BlockCard, ReviewsCard, RemindersCard, OffersCard, WeekCard, ResourceCard, AdviceCard, QuickActions, ActivityFeed, NoticeToasts}/`, `frontend/src/features/radar/components/{RadarSummary, SkillRanking, RadarAlerts, RadarOffers, RadarForm}/`, `frontend/src/features/projects/components/{ProjectCard, ProjectBriefView, CriteriaChecklist, SubmissionForm, EvaluationView, DraftCard, ProfileEntryForm}/`, `types.ts` de chaque feature (types de vue locaux), `frontend/src/shared/i18n/messages/{home.ts, radar.ts, projects.ts}`

Contrats des composants :
- `BlockCard({block, onStart})` : module, leçon, minutes, tâches ; sans bloc : « Rien de prévu aujourd'hui. » ; `ReviewsCard({queue, remaining, onReview})` ; `RemindersCard({due, items, onOpen})` : entreprise, poste, échéance ; `OffersCard({items})` : titre, entreprise, « score 78 sur 100 » écrit, lien externe (`rel="noopener noreferrer"`) ; `WeekCard({week})` : barre et texte « 3 h 10 sur 5 h prévues », tâches, série ; `ResourceCard({resource})` : titre, domaine, date, raison, lien ; `AdviceCard({sentences, status})` : « Le conseil » et ses deux phrases, `pending` « Le conseil se réunit… », `failed`/`unavailable` « Le conseil n'a rien pu dire ce matin. ».
- `QuickActions({onStart, onReview, onAddPosting, onCapture})` : quatre boutons dans l'ordre de F17, accessibles au clavier.
- `ActivityFeed({items, onMore, hasMore})` : liste datée (« il y a 5 min », date complète au survol et en texte masqué), icône par genre `aria-hidden` ; `NoticeToasts({notices, onDismiss})` : région `aria-live="polite"`, 3 au plus, bouton « Fermer ».
- `SkillRanking({ranking})` : rang, compétence, part (« 62 % » et barre), évolution écrite (« +8 pts », « −2 pts », « nouvelle », « premier relevé ») ; `RadarSummary({run})` : « 47 offres lues · 6 bloquées · 41 analysées », domaines bloqués dépliables, bandeau `low_sample` ; `RadarAlerts({alerts})` ; `RadarOffers({offers})` : score ≥ 70 mis en avant par un libellé « Bon match », pas seulement la couleur ; `RadarForm({role, zone, onRun, running})`.
- `ProjectCard({project})` : titre, statut écrit, heures ; `ProjectBriefView({brief})` ; `CriteriaChecklist({criteria, results})` : atteint / non atteint écrit ; `SubmissionForm({onSubmit, busy})` : lien, description (compteur 4 000), captures (5 au plus, aperçu, retrait), erreur de champ ; `EvaluationView({evaluation})` (mention « Captures non lues par le Praticien. » quand il y en a) ; `DraftCard({draft, onSave, onCopy})` : texte modifiable, Copier, « À vérifier : absent de ton profil et de ton rendu : … » ; `ProfileEntryForm({entry, added, onAdd})` : « Ajouter au profil maître » avec rappel « Rien n'entre dans ton profil sans ton accord. ».

- [ ] **Step 1–4:** tests (rendu, rôles, clavier, textes d'évolution sans couleur seule, compteur, limite de 5 captures, région `aria-live`), puis implémentation ; `vitest`, `lint`, `typecheck`.
- [ ] **Step 5: Commit** `feat(phase-8): composants du brief, du radar et des projets (8.12)` ; D168.

---

### Task 8.13 : Accueil : brief, actions rapides, fil d'activité, notifications de fond — simple

**Zone : front.** Lit le contrat de 8.6 et 8.7.

**Files:**
- Create: `frontend/src/features/home/{api.ts, queryKeys.ts, toView.ts}`, `hooks/{useBrief.ts, useActivity.ts, useBackgroundNotices.ts}`, `BackgroundNotices.tsx` (emplacement `overlay`), `frontend/src/shared/lib/captureRequest.ts`, `frontend/src/test/{homeApi.ts, homeHarness.tsx}`
- Modify: `frontend/src/features/home/{manifest.ts, pages/HomePage/}`, `frontend/src/features/capture/CaptureOverlay.tsx` (s'abonne à `useCaptureRequest`), `shared/i18n/messages/home.ts`

```ts
// shared/lib/captureRequest.ts
export const useCaptureRequest: UseBoundStore<StoreApi<{ count: number; request: () => void }>>;
```

Page `/` : `BriefHeader` (« Lundi 16 novembre »), rubriques dans l'ordre de F17 (bloc, révisions, relances, offres, avancement, ressource, conseil), `QuickActions` (P17), `ActivityFeed` en colonne (« Voir plus » par `before`). Conseil `pending` : la page suit `session_id` par `useRun` et relit le brief à la fin. Notifications : `useBackgroundNotices` relit `GET /activity?after=<dernier vu>` toutes les 60 s (`refetchIntervalInBackground: false`), garde les genres `lesson`, `radar`, `brief`, `project`, `job_failed`, montre 3 notices au plus, 8 s chacune (coupé par `prefers-reduced-motion` pour l'animation seulement), invalide le brief et le fil. États vide (aucun programme : « Commence par un objectif » vers `/apprendre/objectifs`), chargement, erreur avec « Réessayer ».

- [ ] **Step 1–4:** tests (brief rendu avec ses 7 rubriques depuis MSW, conseil en attente puis rempli après `run.completed` du faux socket, actions rapides : navigation et capture ouverte, fil paginé, notices après une relecture avec un nouvel élément, rien relu onglet caché, erreur et « Réessayer ») ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-8): accueil, brief du matin et fil d'activité (8.13)` ; D169 (P16, P17).

---

### Task 8.14 : Page du Radar — simple

**Zone : front.** Lit le contrat de 8.4.

**Files:** `frontend/src/features/radar/{api.ts, manifest.ts, queryKeys.ts, toView.ts}`, `hooks/{useRadar.ts, useRadarRun.ts, useStartRadar.ts}`, `pages/RadarPage/`, `frontend/src/app/registry.ts`, `frontend/src/test/radarApi.ts`, messages.

Routes `/carriere/radar` (navigation Carrière, ordre 5, « Radar ») et `/carriere/radar/:runId`. `RadarForm` prérempli par `defaults` ; « Lancer un relevé » → 202, suivi par `useRun` et `RunFeed` (phrases de l'Éclaireur et de l'Analyste) ; 409 `radar_in_progress` → suit le relevé en cours ; 409 `radar_role_required` → message sur le champ. Résultat : `RadarSummary`, `SkillRanking`, `RadarAlerts`, `RadarOffers` ; historique des relevés (`GET /radar/runs`) en liste ; dernier relevé `failed` dit pourquoi en clair.

- [ ] **Step 1–4:** tests (premier relevé, relevé en cours suivi puis résultat, évolution, alertes, échantillon réduit, rôle manquant, historique) ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-8): page du radar du marché (8.14)` ; D170.

---

### Task 8.15 : Portfolio et page d'un projet — simple

**Zone : front.** Lit le contrat de 8.10.

**Files:** `frontend/src/features/projects/{api.ts, manifest.ts, queryKeys.ts, toView.ts}`, `hooks/{useProjects.ts, useProject.ts, useSubmitProject.ts, useSaveDraft.ts, useAddToProfile.ts, useRetryBrief.ts}`, `pages/{PortfolioPage, ProjectPage}/`, `frontend/src/app/registry.ts`, `frontend/src/test/projectsApi.ts`, messages.

Routes `/competences/portfolio` (navigation Compétences, ordre 2, « Portfolio » : projets groupés par statut, état vide « Tes projets arrivent avec les semaines de ton programme. ») et `/competences/portfolio/:projectId` : énoncé (contexte, objectif, contraintes, critères, heures), `SubmissionForm` (multipart), suivi de l'évaluation (`useRun`, `RunFeed`, Praticien), `EvaluationView`, quatre `DraftCard`, `ProfileEntryForm`, historique des rendus avec miniatures des captures ; `brief_failed` → « Réessayer l'énoncé ». Après validation : lien vers la carte des compétences.

- [ ] **Step 1–4:** tests (liste, rendu envoyé et suivi, 422 rattachée au bon champ, à reprendre, validé avec brouillons, brouillon à vérifier modifié, ajout au profil puis bouton remplacé par « Ajouté au profil (version 4) », 409 `profile_draft_pending` lisible) ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-8): Portfolio et projets preuves (8.15)` ; D171.

---

### Task 8.16 : Parcours de bout en bout n° 4 (brief à l'ouverture et relevé du radar) — simple

**Zone : back (scripts e2e) et front (spec Playwright).**

**Files:**
- Create: `backend/tests/e2e/daily_script.py` (réponses scriptées : `ResourcePick`, `CouncilAdvice`, lots `RadarBatch` ; web factice : résultats de recherche, 8 pages d'offres fictives, 3 pages illisibles), `frontend/e2e/daily.spec.ts`
- Modify: `backend/tests/e2e/server.py` (scripts fusionnés par `merge_scripts`, web factice ajouté), `backend/tests/e2e/test_daily_script.py` (les scripts passent la validation réelle des schémas)

Parcours : (1) « le brief du jour existe à l'ouverture » : ouvrir `/` sur un serveur neuf → les 7 rubriques sont affichées (états vides compris), le conseil passe de « se réunit » à ses deux phrases, la ressource a son lien ; recharger → même brief (aucune seconde session : `GET /sessions?graph=daily_brief` en compte une) ; « Capturer » ouvre le dialogue de capture ; « Réviser » mène aux révisions. (2) « un relevé du radar » : `/carriere/radar`, poste et zone fictifs, « Lancer un relevé » → « 8 offres lues · 3 bloquées », bandeau « échantillon réduit », classement avec « premier relevé » ; l'accueil (fil d'activité) montre « Relevé du radar ».

- [ ] **Step 1–4:** script, spec, exécution locale (Edge par config temporaire retirée ensuite) ; `test_daily_script.py` vert ; les parcours n° 1 à 3 restent verts.
- [ ] **Step 5: Commit** `test(e2e): parcours n° 4, brief à l'ouverture et radar (8.16)` ; D172 (P18).

---

### Task 8.17 : Revue complète de la phase (contrôleur)

Revue finale sur **Opus high**, en zones parallèles en lecture seule (back : radar, brief, registre et planificateur ; back : projets, Praticien, honnêteté ; front), une vague de corrections (un test qui échoue avant chaque correction), une revérification sur Sonnet ; les résiduels sont parqués ou tranchés. D173 résume.

---

### Task 8.18 : Contrôle réel de fin de phase et bilan (contrôleur)

- [ ] **Step 1:** `check_phase8` gagne la partie `projets` (`scripts/phase8_projects.py` : un projet du programme fictif avec énoncé prêt, rendu fictif par description et lien d'un dépôt public sans donnée personnelle ; évaluation reçue ; si validé : 4 brouillons, compétences du module à `prouve`, profil inchangé avant `profile-entry`, puis version + 1 ; si à reprendre : critères non atteints nommés) et `tout` ; ses tests.
- [ ] **Step 2:** un jour sans ouverture préalable de l'accueil : `--part planifie` (le brief se génère seul) puis deux essais `--part tout` dans le conteneur jetable ; durées, coûts, offres lues et bloquées, journaux relus (aucun lien, domaine, titre, entreprise, poste visé, description, critère, brouillon, phrase du conseil).
- [ ] **Step 3:** navigateur sur la vraie pile à 1 024 px : accueil, radar, Portfolio, page d'un projet, sans défilement horizontal ni erreur de console ; parcours n° 1 à 4.
- [ ] **Step 4:** `docs/superpowers/bilans/phase-8.md`, D174, plan directeur, mémoire du projet ; tag `phase-8`, push `dev`.

---

## Auto-relecture (faite à l'écriture)

- **Couverture de la spec** : F11 (mini projet par module, 3 à 6 h, contexte, objectif, contraintes, critères ; lien ou description avec captures ; évaluation et retour écrit du Praticien ; `prouve` ; 4 brouillons ; rien au profil sans validation ; écran Portfolio) → 8.1, 8.9, 8.10, 8.12, 8.15 ; F12 (hebdomadaire et à la demande, 30 à 50 offres publiques, extraction de l'Analyste, classement, évolution, alertes « absente de ton programme », offres ≥ 70 dans le brief, offres lues et bloquées toujours dites) → 8.1, 8.3, 8.4, 8.6, 8.14 ; F15 (demande du marché sur la carte, référentiel enrichi) → 8.4 ; F17 (7 h réglable et à l'ouverture, 7 rubriques, 4 actions rapides, fil d'activité) → 8.5, 8.6, 8.7, 8.13 ; 9.6 (registre complet : brief 8.6, radar 8.4, bilan et relances et leçons existants, ATS 8.2) ; 13.2 `jobs` → 8.1, 8.2 ; 13.3 `projects`, 13.5 `radar_runs`, 13.6 `briefs` → 8.1 ; 14.2 « Radar et projets », « Accueil » (`GET /journal` existe depuis la phase 5) → 8.4, 8.6, 8.7, 8.10 ; 15.1 (Accueil, Portfolio sous Compétences, Radar sous Carrière) → 8.13 à 8.15 ; 18.1 « le brief du jour se génère seul et reprend toutes les rubriques » → 8.6, 8.8 (`planifie`), 8.18 ; 18.3 F11, F12, F17 → 8.10, 8.4, 8.6 et 8.16 ; bilan phase 7 (mineurs M1, M3, M5 à M8, mineurs de la revérification, mineurs front) → 8.0, 8.11 ; bilan phase 6 « Phase 8 » (ATS) → 8.2.
- **Écarts assumés (à écrire dans les décisions)** : graphe `project_brief` hors liste 9.2 ; routes hors 14.2 (P19) ; réglages `radar_role`, `radar_zone` ; projets hors calendrier ; captures non lues par le modèle ; brief instantané du jour ; `GET /brief/today` qui crée le brief manquant ; fil d'activité sans table ; parcours e2e n° 4 en plus des trois de 18.2.
- **Laissé aux phases suivantes** : alertes d'offres compatibles (13), lecture complète d'un dépôt (14), notifications du téléphone (19), site portfolio (20) : seuls les points d'accroche de P20 existent.
