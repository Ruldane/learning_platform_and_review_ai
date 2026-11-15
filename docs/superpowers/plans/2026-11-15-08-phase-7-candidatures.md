# Phase 7 — Candidatures : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mode d'exécution déjà choisi : **subagent-driven en mode économie** (voir « Déroulement »).

**Goal:** January suit chaque candidature (fiche, 8 statuts, Kanban et tableau, fil daté, indicateurs), créée automatiquement à la génération d'un CV ciblé, à la main ou en une phrase ; l'application propose les relances au bon moment avec un brouillon prêt à copier, bloque les doublons (certain, probable, possible) et informe d'une autre candidature dans la même entreprise depuis 30 jours ; un clic produit le kit de candidature (7 pièces en parallèle, modifiables, archive zip, jamais de prétentions salariales) ; l'Intervieweur fait passer un entretien blanc écrit avec débrief noté ; le comité de recrutement simulé (4 personas) rend votes, verdict et 3 changements, avec l'avant et l'après ; plus les correctifs d'ouverture laissés par la phase 6.

**Architecture:** Une feature back nouvelle, `applications`, contient les fiches, le fil, les contacts, les relances, le kit, les entretiens et le comité (un paquet `service/` par sous-domaine). Quatre parcours LangGraph nouveaux : `application_intake` (Assistant de suivi : une phrase devient une fiche montrée pour confirmation), `application_kit` (pièces en parallèle), `interview` (Intervieweur, une question par interruption) et `hiring_committee` (Modérateur, Lecteur ATS, Recruteur, Manager, Futur collègue). Quatre agents nouveaux : `tracker` (rapide), `interviewer` (fort), `manager` et `colleague` (standard, variantes de prompt du Recruteur par un bloc partagé). Les agents n'importent aucune feature (contrat 6) : quatre ports de plus dans `AgentPorts` (`applications`, `kit`, `interviews`, `committee`). Les règles pures (statuts, échéances des relances, doublons des candidatures, indicateurs, questions salariales, contrôle des faits d'un texte) sont des modules sans base ni modèle. Une tâche planifiée tient les relances à jour. Côté front : feature `applications/` (section « Candidatures » de la navigation, pastille des relances dues), `DuplicateAlert` partagé avec la page d'une offre, pages Kit, Entretien et Comité (réutilisent `shared/session-ui`), parcours Playwright n° 3.

**Tech Stack:** LangGraph (`Send` ou branches parallèles pour le kit), Pydantic v2 (`Prose`), SQLAlchemy 2 + Alembic, APScheduler 3.11 (existant), `zipfile` (bibliothèque standard) · React 19, TanStack Query, `@dnd-kit/core` (déjà là), Vitest, Testing Library, MSW, Playwright.

**Spec:** `SPEC.md` §1 (honnêteté, humain dans la boucle, « l'application n'envoie jamais rien »), §5.3 point 3 (contrôle doublon à l'entrée d'une offre), §6 entier (F5 : 6.1 à 6.4), §7 F10, §8 F16 (et le guide de style), F19, §9.1 (Assistant de suivi, Intervieweur, Modérateur, Lecteur ATS, Recruteur, Éclaireur, Vérificateur ; Manager et Futur collègue variantes du Recruteur), §9.2 à 9.6, §11.4 (délais de relance 7, 14 et 21 jours ; guide de style), §13.5 (`applications`, `application_events`, `contacts`, `reminders`, `kit_items`, `interviews`, `committee_runs`), §13.6 (index `reminders(due_at, status)`), §14.2 (« Candidatures »), §15.1 (« Candidatures »), §15.2 (comité avec les composants du conseil), §15.3 (`ReminderCard`, `DuplicateAlert`, Kanban, tiroir), §15.4, §17.2 à 17.4, §18.1 (phase 7), §18.2 (parcours n° 3 : cycle de candidature avec doublon et relance), §18.3 (F5, F10, F16, F19 ; critère transverse « aucun texte au nom de January avec un fait absent du profil maître »). Plan directeur : `docs/superpowers/plans/2026-11-11-00-plan-directeur.md` (§1, §3, §5 « Phase 7 »). Bilan : `docs/superpowers/bilans/phase-6.md` (« Phase 7 — correctifs d'ouverture (tâche 7.0) » et « Phase 7 »). Décisions : D121 (offres, doublons), D124 (profil maître, ré-import), D127 à D130 (validateur, revue, versions), D136.

## Global Constraints

Toutes celles du plan directeur et des plans des phases 4 à 6 s'appliquent. Rappel des plus exposées, puis celles de cette phase.

- **Séparation** : `frontend/` et `backend/` strictement séparés, seul lien le contrat `contracts/openapi.json` ; un dossier par feature des deux côtés ; **un dossier par composant front** (`.tsx`, `.test.tsx`, `index.ts`) ; `components/` présentationnel (ni `api.ts`, ni `hooks/`, ni store) ; une feature n'importe jamais une autre feature côté front (elle peut appeler une route d'une autre zone par son propre `api.ts`).
- **Extensibilité** : une feature = un dossier + une ligne dans `FEATURE_ROUTERS` / `app/registry.ts` ; un agent = un prompt `.md` + un nœud `.py` + une ligne dans `AGENTS` ; un graphe = un fichier + une ligne dans `GRAPHS` (+ `ROUTE_ONLY` s'il a sa route) ; un port = un champ d'`AgentPorts` + une ligne dans `bootstrap_agents.agent_ports` + un faux dans `tests/support/` ; une tâche planifiée = un fichier `scheduler/jobs/` + une ligne dans `JOBS`, sa logique dans un service de feature (contrat 8).
- **Contrôles** : mypy --strict, ruff (check et format, ligne de 100), import-linter : **8 contrats, inchangés** (la feature `applications` est couverte par les jokers ; elle peut importer `app.features.postings.service…`, `app.features.cv.service…`, `app.features.quiz.service.cards`, `app.features.settings.service`, **jamais** l'inverse : `postings`, `gap` et `cv` n'importent pas `applications`, ce qui évite tout cycle). ESLint boundaries, `tsc --noEmit`, Prettier.
- **Taille** : 300 lignes par fichier, 50 par fonction, des deux côtés. `app/main.py` est à 298 lignes : **sortir `_add_body_limits` dans un module avant d'y ajouter une ligne** (7.2).
- **Clés API** : jamais renvoyées au navigateur, jamais journalisées.
- **Erreurs** : `{error: {code, message, details}}`, message en français ; **une 422 ne renvoie jamais l'entrée** (ni phrase de January, ni nom d'entreprise, ni réponse d'entretien) : `details.fields` nomme les champs, sans valeur. Une 409 de doublon renvoie les fiches **existantes** (c'est l'alerte demandée), jamais l'entrée.
- **Journaux (17.2)** : identifiants seulement (utilisateur, session, candidature, offre, relance, pièce, entretien, comité, version de CV), des nombres et des codes. **Jamais** : un nom d'entreprise, un intitulé de poste, un nom ou un lien de contact, la phrase de création, un brouillon, une pièce du kit, une question ou une réponse d'entretien, un vote, un texte d'offre, un nom de fichier `CV_…`. Chaque nouvelle zone a son test `test_*_never_logged`.
- **Rien n'est envoyé** (1, 6.2) : aucune route, aucun nœud n'envoie d'email ni de message ; les brouillons se copient. Le seul lien sortant fabriqué est la recherche LinkedIn pré remplie, ouverte par January.
- **Honnêteté (1, 18.3, F16)** : aucun texte écrit au nom de January (pièces du kit, brouillons de relance, pitch, réponses de formulaire, réponse améliorée du débrief, changements du comité) ne contient un chiffre, un outil, un titre ou un nom propre absent du profil maître validé : contrôlé **par le code** (`text_claims`, 7.1), un nouvel essai avec les termes nommés, puis la pièce reste marquée « à vérifier » avec ses termes, jamais présentée comme prête à envoyer. **Les prétentions salariales ne sont jamais remplies par un agent** : une question salariale garde une réponse vide, imposée par le code.
- **Tests sans réseau ni LLM** : modèles scriptés par agent (`ScriptedModels`, `fake_llm`), faux ports (`tests/support/`), `RecordingLauncher` ; seuls les essais réels (7.7, 7.19) touchent GLM 5.3 flash (Z.ai) et la pile Docker.
- **Données de test** : aucune vraie candidature, aucune vraie entreprise. Identité fictive « Camille Exemple » (`camille.exemple@example.org`), entreprises « Société Fictive », « Autre SA », « Exemple Tech » ; offres de `backend/scripts/sample_posting.py` ; domaines `example.org` / `example.invalid`.
- **LangGraph (9.4)** : `interrupt()` **seul dans son nœud** (aucune écriture ni appel payant avant lui) ; chaque écriture d'un port est **idempotente** (clé : session + référence) ; une session survit à `docker compose restart backend`.
- **Sorties structurées (D97 n° 10, D115 n° 17)** : `structured_call` (2 nouveaux essais) ; tout texte libre à lire est un `Prose` ; échéance `LLM_CALL_DEADLINE_S`, `node_timeout` par nœud (120 s au plus, 9.6).
- **Contenu non fiable (17.4)** : texte d'offre, phrase de January, réponse d'entretien, page web, profil rendu à un agent : **toujours** dans `untrusted(…, label)`.
- **Coût** : l'Assistant de suivi (rapide) écrit les pièces courtes ; aucun appel LLM pour les relances (gabarits) ni pour le contrôle des faits (code) ; le comité tient en 17 appels au plus par exécution (4 impressions, 2 tours de 4, 4 votes, 1 synthèse).
- **Contrat front/back** : toute tâche back qui change l'API régénère `contracts/openapi.json` (`cd backend && uv run python -m scripts.export_openapi`) **et** `frontend/src/shared/api/schema.d.ts` (`node frontend/scripts/run-tool.mjs gen:api`, ou `pnpm --dir frontend gen:api` sur un poste où pnpm marche) dans le même commit ; aucune tâche front ne les touche.
- **Front (15.4)** : textes en français dans `frontend/src/shared/i18n/messages/<zone>.ts` ; jamais de `window.confirm` ; état vide avec action, chargement, erreur avec « Réessayer » ; couleur jamais seule ; animations < 300 ms coupées par `prefers-reduced-motion` ; contraste AA ; clavier (le Kanban se manipule aussi sans souris) ; utilisable à 1 024 px.
- **Environnement (poste Windows)** : Python et `uv` par le remplaçant Docker du scratchpad (`PATH` préfixé par `…/scratchpad/uv-shim`) ; `pnpm.exe` et le Chromium de Playwright bloqués par Device Guard : outils front par `node frontend/scripts/run-tool.mjs lint|typecheck`, Vitest par `node node_modules/vitest/vitest.mjs run`, Playwright avec Edge par un fichier de config temporaire (`channel: "msedge"`) retiré ensuite ; images par `docker build -t learning_career_platform-{backend,frontend}:latest`, pile par `docker compose up -d --no-build`. Ne jamais toucher aux conteneurs d'autres projets.

**À vérifier dans la documentation actuelle avant de coder (context7)**, écart suivi tel que la doc l'indique et noté dans la décision de la tâche : LangGraph `Send` et branches parallèles avec un réducteur sur une clé de l'état (`Annotated[list, operator.add]`), reprise après redémarrage au milieu d'une branche ; `@dnd-kit/core` (`KeyboardSensor`, `useDroppable`, annonces d'accessibilité) ; FastAPI `Response` binaire pour un zip (`media_type="application/zip"`, `Content-Disposition`).

## Review Focus

1. **Même offre qui revient par un autre chemin** (lien collé avec `?utm_source=…`, texte recopié dans le formulaire manuel, phrase « j'ai postulé chez Société Fictive pour Développeuse IA » alors que la fiche existe) : l'alerte apparaît avec la date et le statut, quel que soit l'écran, et « C'est un autre poste » ne la refait plus pour ce couple. → 7.1 `test_url_with_tracking_is_certain`, `test_title_similarity_probable`, 7.2 `test_manual_create_duplicate_is_409_with_existing`, `test_distinct_confirmation_silences_pair`, 7.4 `test_intake_duplicate_shows_alert_in_question`.
2. **Relances et changements de statut qui se croisent** (une réponse arrive le jour de la relance de 14 jours, entretien saisi puis annulé, délais changés dans les réglages, relance reportée deux fois) : une relance dont la condition ne tient plus disparaît, une faite ou ignorée reste dans le fil, jamais deux relances du même type pour la même ancre. → 7.1 `test_answer_removes_pending_followups`, `test_changed_delays_move_pending_only`, 7.3 `test_sync_is_idempotent`, `test_postpone_twice_adds_six_days`.
3. **Texte au nom de January qui invente** (lettre qui écrit « 5 ans d'expérience » ou « expert Kubernetes », question « Quelles sont vos prétentions salariales ? », réponse améliorée du débrief qui ajoute un chiffre) : la pièce passe « à vérifier » avec ses termes, la réponse salariale reste vide, rien n'est présenté comme prêt. → 7.1 `test_text_claims_number_and_tool`, `test_salary_questions_detected`, 7.5 `test_letter_with_unsupported_claim_retries_then_flags`, `test_salary_answer_forced_empty`, 7.8 `test_improved_answer_claims_flagged`.
4. **Redémarrage ou coupure en plein parcours** (back relancé entre deux pièces du kit, au milieu d'un entretien, pendant le second tour du comité ; réponse d'entretien envoyée deux fois) : aucune pièce en double, la même question attend, aucun vote compté deux fois. → 7.5 `test_kit_replay_saves_each_piece_once`, 7.8 `test_replay_at_question_keeps_question`, 7.10 `test_committee_replay_votes_once`.
5. **Fiche dont l'offre ou la version disparaît** (offre supprimée après la candidature, nouvelle version de CV générée après « J'ai postulé ») : la suppression de l'offre est refusée tant qu'une fiche la cite ; la version envoyée reste celle du jour de la candidature. → 7.2 `test_posting_delete_refused_with_application`, `test_version_frozen_after_applied`.

---

## Déroulement (mode économie)

- **Modèles** : implémentation par **Sonnet** ; revue par tâche par **Sonnet** pour les tâches moyennes ; **Opus high** pour : le contrat central (7.2), les graphes LangGraph (7.4, 7.5, 7.8, 7.10), l'honnêteté (7.0, 7.1 `text_claims`), la revue finale et la re-revue d'un correctif Critical. Jamais Fable.
- Les tâches marquées **⚠ revue par tâche** sont revues avant la suivante ; les autres sont couvertes par la revue finale.
- **Jamais deux implémenteurs back en même temps** ; au plus un back et un front ensemble. Une tâche back qui **change le contrat** ne tourne avec aucune tâche front qui lit `schema.d.ts`. Les tâches front présentationnelles (7.12) n'importent ni `schema.d.ts` ni `shared/api`.
- **Essai réel en milieu de phase (7.7)** : dès que fiches, relances, création en une phrase et kit existent côté back, avant les écrans, le contrôleur lance ces parcours contre GLM 5.3 flash dans la pile Docker ; ses correctifs sont faits dans 7.7.
- **Décisions** : une entrée par tâche, **D(137 + n)** pour la tâche 7.n (7.0 → D137 … 7.19 → D156). En vague parallèle, seule la tâche back écrit dans `DECISIONS.md` ; la tâche front met sa décision dans son rapport, le contrôleur la recopie. Format existant (Date, Sujet, Décision en points numérotés, Raison).
- Commits par chemins explicites (jamais `git add -A`), hooks jamais sautés ; aucun commit d'un agent pendant que les fichiers d'un autre ne sont pas commités.
- Heure vérifiée par `date` avant chaque lancement d'agent ; quota hebdomadaire demandé à l'utilisatrice en fin de phase.

| Vague | Zone : back | Zone : front |
| --- | --- | --- |
| 1 | 7.0 ⚠ (correctifs d'ouverture back) | 7.11 (correctifs d'ouverture front) |
| 2 | 7.1 ⚠ (tables, règles pures, `text_claims`) | 7.12 (présentationnel) |
| 3 | 7.2 ⚠ (contrat : fiches, fil, contacts, doublons, indicateurs) | — |
| 4 | 7.3 ⚠ (contrat : relances, tâche planifiée) | — |
| 5 | 7.4 ⚠ (Assistant de suivi, `application_intake`) | — |
| 6 | 7.5 ⚠ (`application_kit`) | 7.13 (contrat de 7.2 à 7.4) |
| 7 | 7.6 (contrat : kit, archive) | — |
| 8 | 7.7 essai réel (contrôleur, correctifs back) | — |
| 9 | 7.8 ⚠ (Intervieweur, `interview`) | 7.14 (kit, contrat de 7.6) |
| 10 | 7.9 (contrat : entretiens, fiches de révision) | — |
| 11 | 7.10 ⚠ (Manager, Futur collègue, `hiring_committee`, contrat du comité) | — |
| 12 | — | 7.15 (entretien, contrat de 7.9) |
| 13 | — | 7.16 (comité, contrat de 7.10) |
| 14 | 7.17 (parcours Playwright n° 3 : scripts e2e et spec) | |
| — | Revue complète, vague de corrections, re-revue | |
| 15 | 7.19 (contrôleur : `check_phase7`, essais réels, bilan) | |

(7.18 est la revue complète elle-même : aucune implémentation, D155 la résume.)

Commandes de contrôle d'une tâche back : `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run python -m mypy app && uv run python -c "from importlinter.cli import lint_imports_command; lint_imports_command()" && uv run python -m scripts.export_openapi --check && uv run python -m scripts.check_file_length`. Front : `node node_modules/vitest/vitest.mjs run` puis `node frontend/scripts/run-tool.mjs lint` et `node frontend/scripts/run-tool.mjs typecheck` (depuis `frontend/` pour Vitest).

## Interfaces consommées (phases 0 à 6)

- Cœur : `AppError(code, message, status_code, details)`, `app.core.deps` (`Db`, `CurrentUserDep`), `UserScopedMixin`, `UTCDateTime`, `new_id`, `UserScopedRepository[M]`, `core.clock` (`user_zone`, `local_today`, `DEFAULT_ZONE`), `KeyLocks`.
- Moteur : `AgentPorts` / `NO_PORTS` (`agents/runtime/ports.py`), `SessionLauncher.start(user_id, graph, input, *, subject_type, subject_id)` et `.resume(...)`, `GraphDeps` (`user_id`, `session_id`, `models.get_chat_model(user_id, tier, agent)`, `bus`, `settings: RunSettings` dont `style_guide`, `session_factory`, `ports`), `structured_call(model, schema, messages, *, agent, step, intent, retries=2)`, `Prose`, `speak(...)`, `emit(type, payload, *, agent)`, `node_timeout(seconds)`, `render_prompt(agent, **vars)` (Jinja strict, `{% include "_shared/…" %}`), `untrusted(text, label)`, `AGENTS` / `AgentSpec(name, tier)`, `GRAPHS` / `GraphSpec(name, input_model, build)`, `InterruptRequestedPayload(interrupt_id, kind, question, options, fields)`, `ArtifactReadyPayload(artifact_id, kind, title, url)`, `ROUTE_ONLY` (`features/sessions/service.py`), `make_company` (`agents/nodes/scout/company.py`), `web_search`, `web_read`, `review_common` (`review_inputs`), `agents/nodes/moderator.py`.
- Offres et CV : `JobPosting` (`url_norm`, `company`, `company_norm`, `title`, `text`, `analysis: PostingAnalysis` dont `language`, `duplicates`, `distinct_from`, `gap`), `Company` (`name_norm`, `brief: CompanyBrief`, `sources`, `ats`, `refreshed_at`), `postings.service.rules` (`posting_url_key`, `company_key`, `title_similarity`, `PROBABLE_TITLE = 0.85`), `postings.service.duplicates` (`shown_duplicates`, `zone_of`), `PostingRepository.same_company`, `cv.service.versions` (`list_versions`, `get_version`, `version_pdf`), `CvVersion` (`posting_id`, `number`, `status`, `content`, `filename`, `created_at`), `cv.service.naming.cv_filename`, `MasterProfileData` (`agents/tools/cv_schema.py`), `cv_lexicon` (`numbers_in`, `TECH_TERMS`, `TITLE_WORDS`), `cv_validator` (`normalize_term`, logique des titres et noms propres), `BRIEF_MAX_AGE_DAYS = 30`.
- Étude : `quiz.service.cards` (`NewCard`, `add_cards(db, user_id, cards, today)`), `CardSource`.
- Réglages : `SettingsService(db, user_id).get()` → `UserSettings.reminder_delays_days = [7, 14, 21]`, `style_guide = ""`, `timezone`.
- Planificateur : `JobSpec(name, every, run, at_startup)`, `JobContext`, `JOBS`, `bootstrap_agents.scheduler_context`.
- Tests back : `settings`, `db_session_factory`, `client`, `act_as`, `RecordingLauncher`, `ScriptedModels`, `fake_llm`, `FakeWebReader`, `all_events`, `final_state`, `tests/agents/graphs/conftest.py` (`FixedSettings`), `tests/e2e/server.py`, `scripts/phase4_steps.py` (`Run`, `CheckFailed`, `EventFeed`, `websocket_feed`), `scripts/sample_posting.py`, `scripts/sample_cv.py`.
- Front : `api`, `unwrap`, `errorMessage`, `t`, `FeatureManifest`, `NavEntry`, `FEATURES`, `useSessionStream`, `useSessionActions`, `DebateFeed(renderInterrupt)`, `InterruptCard`, `FreeTextAnswer`, `SessionStatusBar`, `SessionControls`, `CostBadge`, `agentIdentity`, `AGENT_COLORS` (slugs `tracker` et `interviewer` déjà réservés), `EmptyState`, `LoadingState`, `ErrorState`, `InlineError`, `Button`, `fieldClass` ; `features/cv/hooks/useRun.ts` et `features/cv/pages/RunFeed.tsx` (à remonter, voir 7.13) ; `features/gap/components/DuplicateNotice/` ; outillage `src/test/server.ts`, `fakeSocket.ts`, `queryWrapper.tsx`, `renderRoutes.tsx`, `streamHarness.ts`.

---

### Task 7.0 : Correctifs d'ouverture (back) ⚠ revue par tâche (Opus high : honnêteté du profil)

**Zone : back (CV, profil, validateur).** Change le contrat (description de `gap_terms`). Tourne avec 7.11.

**Files:**
- Modify: `backend/app/features/cv/service/profile_merge.py` (`_carried`, `_carry_lines` : docstring), `backend/app/features/cv/service/profile_facts.py` (`_SEP`, `_split_company`, `_write_language`, `_write_link`, `_valid_url`), `backend/app/agents/tools/cv_validator.py` et `agents/nodes/review_save.py` (`gap_terms`), `backend/app/features/cv/schemas_reviews.py` (`CvReviewOut.gap_terms`, description), `backend/app/agents/state/cv_review.py` (commentaire), `backend/app/agents/tools/cv_lexicon.py` (`numbers_in`), `backend/app/features/postings/service/delete.py` (ou le module de suppression existant) ; `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`, `DECISIONS.md` (D137 ; D124 complétée pour `_carry_lines`).
- Test: `backend/tests/features/cv/test_profile_merge.py`, `test_profile_facts.py`, `backend/tests/agents/tools/test_cv_validator.py`, `test_cv_lexicon.py`, `backend/tests/features/postings/test_delete.py`.

**Interfaces:**
- Produces : `CvReviewOut.gap_terms` reste `list[str]`, **sens arrêté** : « mots clés de l'offre que les faits cités ne portent pas : à appuyer par un fait ou à acquérir ». Le libellé front change en 7.11 (« À appuyer ou à acquérir »). Rien d'autre ne change de forme.

- [ ] **Step 1: Write the failing tests**

```python
# I-D : le fait de January qui remplace un brouillon équivalent prend les dates, le lieu et l'URL du brouillon
def test_replacement_keeps_draft_dates_place_url():
    previous = profile_with_job(role="Développeuse IA", company="Société Fictive", start="2023-01", end=None,
                                source="january")
    draft = profile_with_job(role="Développeuse IA", company="Société Fictive", start="2023-01", end="2025-06",
                             location="Lyon")
    merged = merge_draft(draft, previous)
    job = merged.experiences[0]
    assert (job.start, job.end, job.location) == ("2023-01", "2025-06", "Lyon") and "january" in job.sources
def test_replacement_keeps_january_value_when_draft_has_none(): ...   # brouillon sans lieu : celui de January reste
def test_replacement_takes_new_project_url(): ...                     # projet : URL du nouveau CV

# I-E : les trois tirets découpent rôle et entreprise ; sans séparateur, 422 sans écho
@pytest.mark.parametrize("dash", ["—", "–", "-"])
def test_experience_split_on_any_dash(dash):
    fact = confirm_experience(f"Développeuse {dash} Autre SA")
    assert (fact.role, fact.company) == ("Développeuse", "Autre SA")
def test_experience_without_separator_keeps_role_only_rule_documented(): ...  # rôle seul : entreprise gardée (D137 n° 2)
def test_hyphenated_role_is_not_split(): ...          # « Data-scientist — Autre SA » : seul « — » ou un tiret entouré d'espaces sépare
def test_language_parenthesis_before_colon():
    assert split_language("Anglais (TOEIC: 950)") == ("Anglais", "TOEIC: 950")
def test_url_with_angle_brackets_or_quote_is_invalid(): ...   # < > " dans l'URL → False

# Mineurs du validateur
def test_french_decimal_comma_is_one_number():
    assert numbers_in("1,500 M€") == {"1.5"} or numbers_in("1,500 M€") == numbers_in("1,5 M€")
def test_link_without_scheme_matches_profile_link(): ...  # « github.com/camille » = « https://github.com/camille »

# Suppression d'une offre : verrou de revue pris avant la vérification (course m-6)
async def test_delete_races_with_review_creation(...): ...   # une revue créée pendant la suppression : 409, rien de cascadé
```

- [ ] **Step 2: Run them, check they fail**

Run: `cd backend && uv run pytest tests/features/cv/test_profile_merge.py tests/features/cv/test_profile_facts.py tests/agents/tools/test_cv_lexicon.py tests/features/postings/test_delete.py -q`
Expected: FAIL (dates perdues, tiret court non découpé, « 1,500 » lu 1 500, course non couverte).

- [ ] **Step 3: Implement**
  - `_carried` : quand un candidat unique remplace le brouillon, copier du brouillon les champs non textuels **qu'il renseigne** (dates de début et de fin, lieu, URL) ; garder ceux de January quand le brouillon n'en a pas.
  - `_SEP` : séparateur rôle / entreprise = « — », ou « – » / « - » **entourés d'espaces** (un trait d'union collé n'est jamais un séparateur) ; même règle pour `_write_link`. Texte sans séparateur : comportement actuel gardé (rôle seul), écrit dans D137.
  - Langue : tenter la parenthèse avant le deux-points.
  - `_valid_url` : refuser `<`, `>`, `"` n'importe où.
  - `numbers_in` : « 1,500 » avec une virgule suivie de 3 chiffres et une unité monétaire ou « M », « k » lu comme décimal français (1,5) ; « 1,000 » sans unité garde la lecture D136.
  - Comparaison de liens : schéma ajouté avant comparaison, fin d'URL comparée en respectant la casse.
  - Suppression d'offre : prendre le verrou des revues de l'utilisatrice **avant** la vérification et le garder jusqu'au commit.
  - `gap_terms` : aucun changement de calcul ; description du contrat, docstring du validateur et commentaire d'état réécrits au sens arrêté ci-dessus ; `scripts/phase6_review_rules.py` inchangé (sa règle vise les termes absents de tout le profil).

- [ ] **Step 4: Run tests, then the full back check commands** — Expected: PASS.

- [ ] **Step 5: Commit** (chemins explicites ; message `fix(phase-7): correctifs d'ouverture du profil, des liens et des nombres (7.0)`).

---

### Task 7.1 : Tables, règles pures et contrôle des faits d'un texte ⚠ revue par tâche (Opus high)

**Zone : back (base, règles).** Ne change pas le contrat. Tourne avec 7.12.

**Files:**
- Create: `backend/app/db/models/applications.py`, `backend/alembic/versions/0011_applications.py`, `backend/app/features/applications/__init__.py`, `backend/app/features/applications/service/__init__.py`, `service/rules.py` (statuts, indicateurs), `service/schedule.py` (échéances des relances), `service/matching.py` (doublons des candidatures), `backend/app/agents/tools/text_claims.py`, `backend/app/agents/tools/salary.py`
- Modify: `backend/app/db/models/__init__.py`, `backend/app/db/models/study.py` (`CardSource` gagne `"interview"`), `backend/app/features/settings/schemas.py` (validation de `reminder_delays_days`)
- Test: `backend/tests/db/test_applications_migration.py`, `backend/tests/features/applications/test_rules.py`, `test_schedule.py`, `test_matching.py`, `backend/tests/agents/tools/test_text_claims.py`, `test_salary.py`, `backend/tests/features/settings/test_settings_service.py`

**Interfaces:**
- Produces:

```python
# db/models/applications.py (types partagés avec les agents : déclarés ici, contrat 6)
ApplicationStatus = Literal["to_apply", "applied", "followed_up", "interview", "offer", "rejected",
                            "no_answer", "withdrawn"]          # À postuler … Retirée (6.1), dans cet ordre
Channel = Literal["company_site", "job_board", "linkedin", "email", "referral", "other"]
EventKind = Literal["created", "status", "note", "reminder", "kit", "interview", "committee", "version"]
ReminderKind = Literal["linkedin_7", "email_14", "close_21", "thanks", "news_7"]
ReminderStatus = Literal["pending", "done", "ignored"]
KitKind = Literal["cv", "letter", "linkedin", "followups", "form_answers", "company_brief", "pitch"]
KitStatus = Literal["pending", "ready", "to_check", "failed"]
InterviewMode = Literal["behavioral", "technical", "case", "mixed"]
RunStatus = Literal["running", "done", "failed", "stopped"]

class Application(UserScopedMixin, Base):      # table applications
    posting_id: str | None            # String(36), sans FK (comme cv_versions) ; la fiche garde sa copie figée
    company: str; company_norm: str; title: str          # ≤ 200
    url: str | None; url_norm: str | None
    posting_text: str | None          # copie figée prise à la création (6.1)
    channel: Channel | None
    status: ApplicationStatus         # défaut "to_apply"
    applied_on: date | None; interview_on: date | None; answered_on: date | None  # première réponse
    cv_version_id: str | None         # figée au passage à "applied"
    letter: str | None; notes: str | None                 # ≤ 20 000
    next_action: str | None; next_action_on: date | None  # ≤ 200
    distinct_from: list[str]          # ids de fiches confirmées « autre poste » (dans les deux sens)
    # index : (user_id, url_norm), (user_id, company_norm), (user_id, posting_id)
class ApplicationEvent(UserScopedMixin, Base):   # application_id FK cascade ; kind ; at: UTCDateTime ;
    status_from / status_to: ApplicationStatus | None ; text: str | None (≤ 2 000) ; ref_id: str | None
class Contact(UserScopedMixin, Base):            # application_id FK cascade ; name ≤ 120 ; role ≤ 120 ; url ≤ 500
class Reminder(UserScopedMixin, Base):           # application_id FK cascade ; kind ; anchor_on: date ;
    due_on: date ; status: ReminderStatus ; done_at: datetime | None
    # unique (application_id, kind, anchor_on) ; index (due_on, status) (13.6 « reminders(due_at, status) »)
class KitItem(UserScopedMixin, Base):            # application_id FK cascade ; kind ; status ; content: str ;
    meta: dict (flags, sources, words, language) ; edited: bool ; session_id: str | None ; unique (application_id, kind)
class Interview(UserScopedMixin, Base):          # application_id | None (sans FK) ; posting_id | None ; role: str | None ;
    mode ; duration_min: int (15 | 30 | 45) ; language: "fr" | "en" ; session_id ; status: RunStatus ;
    exchanges: list[dict] ; debrief: dict | None
class CommitteeRun(UserScopedMixin, Base):       # cv_version_id ; posting_id ; application_id | None ; session_id ;
    status: RunStatus ; votes: list[dict] ; verdict: str | None ; objections: list[dict] ; changes: list[dict] ;
    previous_id: str | None
# Company gagne : dossier: dict | None ; dossier_sources: list[dict] ; dossier_at: datetime | None
# flashcards.source : String(8) → String(16) (batch_alter_table) pour "interview"

# features/applications/service/rules.py
STATUS_ORDER: tuple[ApplicationStatus, ...]           # ordre des colonnes du Kanban (6.1)
ANSWERED: frozenset[ApplicationStatus] = {"interview", "offer", "rejected"}
WAITING: frozenset[ApplicationStatus] = {"applied", "followed_up"}
def on_status(app: ApplicationView, new: ApplicationStatus, day: date) -> StatusEffects
    # applied : applied_on = day si vide ; interview : interview_on = day si non donné ; première entrée dans
    # ANSWERED : answered_on = day ; to_apply ← tout statut permis (January corrige) ; renvoie les champs posés
def stats(apps: Sequence[ApplicationView], due_reminders: int) -> Stats
    # by_status (8 clés, 0 compris) ; response_rate = répondues / postulées (applied_on non nul), None si 0 ;
    # mean_response_days = moyenne (answered_on − applied_on) des répondues, arrondie à 0,1, None si aucune ; due

# service/schedule.py
POST_INTERVIEW = (1, 7)          # lendemain : remerciement ; 7 jours : demande de nouvelles (fixes, 6.2)
def expected_reminders(app: ApplicationView, delays: tuple[int, int, int]) -> list[Expected]
    # Expected(kind, anchor_on, due_on) ; en attente de réponse (WAITING et applied_on) : linkedin_7, email_14,
    # close_21 aux délais ; statut "interview" et interview_on : thanks (+1), news_7 (+7) ; sinon : aucune
def validated_delays(raw: Sequence[int]) -> tuple[int, int, int]   # 3 entiers strictement croissants de 1 à 90,
    # sinon (7, 14, 21)

# service/matching.py
DuplicateLevel = Literal["certain", "probable", "possible"]
@dataclass(frozen=True) class Incoming: url_norm: str | None; company_norm: str; title: str;
    posting_id: str | None; possible_posting_ids: frozenset[str]   # offres « possibles » de l'offre (D121)
@dataclass(frozen=True) class Hit: level: DuplicateLevel | Literal["info"]; application_id: str
def match(incoming: Incoming, apps: Sequence[ApplicationView], today: date) -> list[Hit]
    # même posting_id : jamais un doublon (c'est la fiche elle-même, rendue à part) ; url_norm égal : certain ;
    # même company_norm et title_similarity ≥ PROBABLE_TITLE : probable ; même entreprise et posting_id dans
    # possible_posting_ids : possible ; sinon même entreprise et (applied_on ou création) dans les 30 derniers
    # jours : info ; une fiche dont distinct_from contient la fiche entrante (ou l'inverse) : écartée ;
    # un seul niveau par fiche (le plus fort), triées certain > probable > possible > info puis date décroissante
INFO_DAYS = 30
def alert_message(level, company, title, status, day: date | None, today: date) -> str
    # « Attention, tu as déjà postulé chez {company} pour le poste {title} le 3 novembre (statut : Postulée). »
    # fiche à postuler : « … tu as déjà une fiche chez {company} pour le poste {title}, créée le … (statut : À postuler). »
    # info : « Pour info : tu as postulé chez {company} il y a {n} jours, pour le poste {title}. »
    # année ajoutée quand elle diffère de celle d'aujourd'hui ; mois en toutes lettres

# agents/tools/text_claims.py (contrôle des textes écrits au nom de January)
@dataclass(frozen=True) class Claim: kind: Literal["number", "tool", "title", "name"]; term: str
def text_claims(text: str, profile: MasterProfileData, *, allowed: Sequence[str] = ()) -> list[Claim]
    # référence : tout le profil validé (faits, compétences, langues, liens) + `allowed` (entreprise, intitulé et
    # mots de l'offre quand le texte les cite comme ceux de l'offre : « votre poste de Développeuse IA ») ;
    # mêmes lectures que le validateur (cv_lexicon.numbers_in, TECH_TERMS sous forme de produit, TITLE_WORDS,
    # noms propres) ; un nombre de l'offre (« 3 ans requis ») cité comme exigence n'est pas dans `allowed` :
    # les phrases doivent parler de January ; sans doublon, dans l'ordre du texte

# agents/tools/salary.py
def is_salary_question(question: str) -> bool  # salaire, rémunération, prétentions, package, TJM, salary,
    # compensation, expected pay, pay range… (insensible à la casse et aux accents)
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_migration_creates_tables_and_widens_card_source(alembic_db): ...
    # les 7 tables, l'index reminders (due_on, status), companies.dossier, flashcards.source accepte "interview"
def test_on_status_applied_sets_date_once(): ...
def test_first_answer_sets_answered_on(): ...        # interview puis rejected : answered_on reste la 1re date
def test_stats_rates_and_delays():
    s = stats([applied(d(1, 11), answered=d(8, 11)), applied(d(3, 11)), to_apply()], due_reminders=2)
    assert s.by_status["applied"] == 1 and s.response_rate == 0.5 and s.mean_response_days == 7.0 and s.due == 2
def test_stats_empty_is_none_not_zero_division(): ...
def test_expected_waiting_reminders(): ...           # applied le 1/11 : linkedin_7 le 8, email_14 le 15, close_21 le 22
def test_answer_removes_pending_followups(): ...     # statut "rejected" : aucune relance attendue
def test_interview_reminders(): ...                  # interview_on 10/11 : thanks le 11, news_7 le 17
def test_changed_delays_move_pending_only(): ...     # (5, 10, 15) : échéances recalculées
def test_invalid_delays_fall_back(): ...             # (14, 7, 21), (0, 7, 14), (7, 14) → (7, 14, 21)
def test_url_with_tracking_is_certain(): ...         # url_norm (posting_url_key) des deux côtés : certain
def test_title_similarity_probable(): ...            # « Développeuse IA (H/F) » / « Développeuse IA » : probable
def test_other_title_same_company_within_30_days_is_info(): ...   # 29 jours : info ; 31 jours : rien
def test_distinct_pair_is_silent(): ...
def test_same_posting_is_not_a_duplicate(): ...
def test_alert_message_wording(): ...   # date « le 3 novembre », statut « Postulée », année si différente
def test_text_claims_number_and_tool():
    claims = text_claims("Avec 5 ans d'expérience sur Kubernetes, je…", profile_without_k8s())
    assert {c.term for c in claims} >= {"5", "Kubernetes"}
def test_text_claims_accepts_profile_facts(): ...    # chiffres et outils du profil : aucun claim
def test_text_claims_allowed_posting_title(): ...    # « votre poste de Lead Data » cité : pas de titre revendiqué
def test_text_claims_title_claimed(): ...            # « en tant que Lead Data » absent du profil : title
@pytest.mark.parametrize("q", ["Quelles sont vos prétentions salariales ?", "Expected salary", "Votre TJM ?",
                               "Rémunération souhaitée"])
def test_salary_questions_detected(q): assert is_salary_question(q)
def test_non_salary_question(): assert not is_salary_question("Êtes-vous disponible sous 3 mois ?")
```

- [ ] **Step 2: Run, check they fail** — `uv run pytest tests/features/applications tests/agents/tools/test_text_claims.py tests/agents/tools/test_salary.py tests/db/test_applications_migration.py -q` → FAIL (modules absents).

- [ ] **Step 3: Implement** the models, migration `0011` (`down_revision = "0010"`, `batch_alter_table` pour `flashcards` et `companies`), the pure modules above and `validated_delays` branché dans la validation de `UserSettings.reminder_delays_days` (valeur invalide → défaut, comme les autres champs). `ApplicationView` : dataclass figée (id, status, company_norm, title, url_norm, posting_id, applied_on, interview_on, answered_on, created_on, distinct_from), construite par le service en 7.2 ; aucun module pur n'importe la base.

- [ ] **Step 4: Run tests and full back checks** — PASS.

- [ ] **Step 5: Commit** `feat(phase-7): tables des candidatures et règles pures (7.1)` ; D138.

---

### Task 7.2 : Fiches, fil, contacts, doublons et indicateurs (contrat) ⚠ revue par tâche (Opus high : contrat central)

**Zone : back (feature `applications`).** Change le contrat. Tourne seule.

**Files:**
- Create: `backend/app/features/applications/{repository.py, schemas.py, router.py}`, `service/{runtime.py, views.py, create.py, update.py, events.py, check.py, adopt.py, queries.py}`, `backend/app/core/body_limits.py` (sorti de `main.py`)
- Modify: `backend/app/features/registry.py`, `backend/app/bootstrap_career.py` (`CareerRuntimes.applications`), `backend/app/main.py` (`_add_body_limits` déplacé), `backend/app/features/postings/repository.py` (requête `has_application(posting_id)` sur le modèle `Application`), le service de suppression des offres (409), `backend/app/features/cv/service/versions.py` (`ready_versions_without(...)`, lecture seule)
- Test: `backend/tests/features/applications/{conftest.py, test_create.py, test_update.py, test_events.py, test_check.py, test_adopt.py, test_router.py, test_logs.py}`, `backend/tests/features/postings/test_delete.py`

**Interfaces:**
- Produces (routes sous `/api/v1`, toutes au nom de l'utilisatrice courante) :

```text
GET    /applications?status=&posting_id=        → list[ApplicationOut] (création décroissante) ; adopte d'abord les versions (ci-dessous)
POST   /applications  ApplicationIn              → 201 CreatedOut {application, info: list[AlertOut]}
                                                   409 application_duplicate details.alerts: list[AlertOut] (fiches existantes)
GET    /applications/{id}                         → ApplicationDetail (fiche + contacts + events + reminders)
PATCH  /applications/{id}  ApplicationPatch       → ApplicationDetail (champs ; contacts remplacés si fournis, ≤ 10)
POST   /applications/{id}/events  EventIn         → ApplicationDetail
GET    /applications/check?posting_id= | ?url=    → CheckOut {own: ApplicationRef | None, alerts, info}
GET    /applications/stats                        → StatsOut {by_status, response_rate, mean_response_days, due_reminders}
```

```python
class ApplicationIn(BaseModel):   # création manuelle ou depuis une offre
    posting_id: str | None = None          # fournie : entreprise, intitulé, lien et texte figé repris de l'offre
    company: str | None; title: str | None; url: HttpUrl | None; posting_text: str | None  # ≤ 200 / 2 000 / 60 000
    channel: Channel | None = None; status: ApplicationStatus = "to_apply"; applied_on: date | None = None
    notes: str | None = None; contacts: list[ContactIn] = []          # ≤ 10
    distinct_from: list[str] = []          # « C'est un autre poste » : ids des fiches de l'alerte
    # sans posting_id : company et title obligatoires (422 fields) ; posting_id inconnu : 404 posting_not_found
class EventIn(BaseModel):
    kind: Literal["status", "note"]; status: ApplicationStatus | None; text: str | None  # ≤ 2 000
    on: date | None = None                 # date de l'événement (défaut : aujourd'hui, fuseau de January)
    interview_on: date | None = None       # pour status "interview" (défaut : on)
class AlertOut(BaseModel):
    level: Literal["certain", "probable", "possible", "info"]; application_id: str; company: str; title: str
    status: ApplicationStatus; applied_on: date | None; created_on: date; message: str
class ApplicationOut(BaseModel): id, posting_id, company, title, url, channel, status, applied_on, interview_on,
    cv_version_id, cv_version_number: int | None, next_action, next_action_on, due_reminders: int, created_at, updated_at
class ApplicationDetail(ApplicationOut): posting_text, letter, notes, contacts: list[ContactOut],
    events: list[EventOut] (chronologique), reminders: list[ReminderOut] (7.3 ; vide jusque-là)

# service/runtime.py
@dataclass class ApplicationsRuntime: session_factory; launcher; now: Callable[[], datetime]; locks: KeyLocks
async def views_of(db, user_id) -> list[ApplicationView]            # pour matching et stats (7.1)
async def check_incoming(db, user_id, incoming: Incoming, today) -> list[Hit]
async def create_application(rt, user_id, body: ApplicationIn) -> CreatedOut
async def add_event(rt, user_id, application_id, body: EventIn) -> ApplicationDetail
async def adopt_versions(db, user_id) -> int    # fiches créées
```

Règles :
1. **Création** sous le verrou des candidatures de l'utilisatrice : `check_incoming` → une alerte `certain`, `probable` ou `possible` non couverte par `distinct_from` → 409 `application_duplicate` (message « Cette offre ressemble à une candidature existante. ») ; sinon fiche créée, événement `created`, `distinct_from` posé dans les deux sens ; les `info` partent dans la réponse 201. Entrée par `posting_id` : copie figée du texte et lien de l'offre ; une fiche existe déjà pour cette offre → 409 `application_exists` (`details.application_id`).
2. **Statut** par `POST /events {kind: "status"}` seulement (PATCH refuse `status` : 422 `fields: ["status"]`) : `on_status` (7.1), événement `status` avec `status_from` / `status_to` ; passage à `applied` : `cv_version_id` figé à la version prête la plus récente de l'offre (si aucune n'est figée), événement `version`. Après `applied`, une nouvelle version ne remplace plus la version envoyée.
3. **Création automatique (6.1 n° 1)** : `adopt_versions` crée au statut `to_apply` la fiche d'une offre qui a une version `ready` et aucune fiche (lien version ↔ candidature) ; tant que la fiche est `to_apply`, `cv_version_id` suit la version prête la plus récente. Appelée en tête de `GET /applications`, `GET /applications/stats` et par la tâche planifiée (7.3) ; idempotente ; une offre dont la fiche a été retirée n'en reçoit pas une seconde. **Pas d'import de `applications` par `cv`** (sens unique, voir Global Constraints).
4. **Contrôle à l'entrée d'une offre (5.3, 6.3)** : `GET /applications/check?posting_id=` construit `Incoming` depuis l'offre (lien normalisé, entreprise de l'offre ou de l'analyse, intitulé, ids des offres « possibles » de `posting.duplicates`) ; `own` = la fiche de cette offre si elle existe ; `?url=` sert avant analyse (niveau certain seulement). Le front l'appelle sur la page d'une offre.
5. **Offre supprimée** : refus 409 `posting_has_application` (`details.application_id`) tant qu'une fiche cite l'offre (requête dans `PostingRepository`, sur le modèle seul : aucun import de feature).
6. **Journaux** : identifiants et codes seulement (`test_application_data_never_logged` : entreprise, intitulé, contact, notes absents des journaux).

- [ ] **Step 1: Write the failing tests**

```python
async def test_manual_create_then_detail(client): ...                 # 201, événement created, contacts
async def test_create_from_posting_freezes_text(client, posting): ...  # posting_text = texte de l'offre ; lien repris
async def test_manual_create_duplicate_is_409_with_existing(client):
    await create(client, company="Société Fictive", title="Développeuse IA", status="applied", applied_on="2026-11-03")
    r = await create(client, company="société fictive", title="Développeuse IA (H/F)")
    assert r.status_code == 409 and r.json()["error"]["code"] == "application_duplicate"
    alert = r.json()["error"]["details"]["alerts"][0]
    assert alert["level"] == "probable" and "le 3 novembre" in alert["message"] and "Postulée" in alert["message"]
async def test_distinct_confirmation_silences_pair(client): ...       # renvoi avec distinct_from : 201, plus d'alerte ensuite
async def test_same_company_info_is_201_with_info(client): ...
async def test_status_via_patch_is_422(client): ...
async def test_applied_freezes_version(client, ready_version): ...
async def test_version_frozen_after_applied(client, ready_version): ...  # nouvelle version : cv_version_id inchangé
async def test_adopt_creates_to_apply_once(client, ready_version): ...   # deux GET : une fiche
async def test_adopt_follows_latest_version_while_to_apply(...): ...
async def test_check_by_posting_returns_own_and_alerts(...): ...
async def test_check_by_url_before_analysis_is_certain_only(...): ...
async def test_posting_delete_refused_with_application(...): ...
async def test_stats_route(...): ...
async def test_422_never_echoes_input(client): ...      # entreprise de 500 caractères : details.fields seulement
async def test_other_user_sees_nothing(...): ...       # 404 sur la fiche d'un autre utilisateur
async def test_application_data_never_logged(caplog, ...): ...
```

- [ ] **Step 2: Run, check they fail.**
- [ ] **Step 3: Implement** (repository `UserScopedRepository[Application]` + requêtes, services ci-dessus, router mince, `ApplicationsRuntime` dans `career_runtimes`, ligne `FEATURE_ROUTERS`) ; exporter le contrat et régénérer `schema.d.ts`.
- [ ] **Step 4: Run tests and full back checks** — PASS.
- [ ] **Step 5: Commit** `feat(phase-7): fiches de candidature, fil, doublons et indicateurs (7.2)` ; D139.

---

### Task 7.3 : Relances et tâche planifiée (contrat) ⚠ revue par tâche (Sonnet)

**Zone : back.** Change le contrat. Tourne seule.

**Files:**
- Create: `backend/app/features/applications/service/{reminders.py, drafts.py}`, `backend/app/features/applications/router_reminders.py` (ou routes dans `router.py` si la taille le permet), `backend/app/scheduler/jobs/reminders_due.py`
- Modify: `backend/app/scheduler/{registry.py, base.py}` (`JobContext.applications`), `backend/app/bootstrap_agents.py` (`scheduler_context`), `backend/app/features/applications/schemas.py`, `service/views.py` (`due_reminders`)
- Test: `backend/tests/features/applications/{test_reminders.py, test_drafts.py, test_reminders_router.py}`, `backend/tests/scheduler/test_reminders_due.py`

**Interfaces:**

```text
GET   /reminders?due=true|false               → list[ReminderOut] ; synchronise d'abord ; due=true (défaut) : pending et due_on ≤ aujourd'hui
PATCH /reminders/{id}  {action: "done" | "postpone" | "ignore"}  → ReminderOut
```

```python
class ReminderOut(BaseModel):
    id; application_id; kind: ReminderKind; due_on: date; status: ReminderStatus
    company: str; title: str
    contact: ContactOut | None            # le premier contact de la fiche (recruteur d'abord si un rôle le dit)
    linkedin_search_url: str | None       # sans contact : https://www.linkedin.com/search/results/people/?keywords=<entreprise + rôle visé>
    channel: Literal["linkedin", "email", "none"]   # close_21 : "none" (proposition de classer)
    draft: str                            # prêt à copier ; close_21 : la phrase de proposition
async def sync_reminders(db, user_id, today: date, delays: tuple[int, int, int]) -> None
    # attendues (expected_reminders) moins existantes : créées pending ; pending non attendues : supprimées ;
    # done et ignored jamais touchées ; idempotente
def draft_for(kind, *, language: Literal["fr", "en"], company, title, contact_name, applied_on,
              interview_on, kit_followup: str | None) -> str
    # gabarits fixes (aucun appel LLM) ; langue de l'offre (analysis.language, défaut fr) ; brouillon du kit
    # pour linkedin_7 (relance de 7 jours) et email_14 (14 jours) quand la pièce `followups` est prête et non
    # « à vérifier » ; aucun fait inventé : seuls entreprise, poste, dates et prénom du contact
async def run_reminders(session_factory, now) -> None   # pour la tâche planifiée : adopt_versions puis sync_reminders, par utilisatrice
```

Actions : `done` → statut `done`, événement `reminder` ; `linkedin_7` ou `email_14` faite sur une fiche `applied` → statut `followed_up` (Relancée) ; `close_21` faite → statut `no_answer` (Sans réponse) ; `postpone` → `due_on = max(due_on, aujourd'hui) + 3` (reste pending) ; `ignore` → `ignored`, événement `reminder`. Relance déjà faite ou ignorée : 409 `reminder_closed`. Tâche planifiée `reminders_due` toutes les heures, `at_startup=True`. `ApplicationOut.due_reminders` et `StatsOut.due_reminders` comptent les relances dues.

- [ ] **Step 1: Write the failing tests**

```python
async def test_seven_days_without_answer_shows_reminder_with_draft(client):   # critère F5
    app = await create(client, company="Société Fictive", title="Développeuse IA", status="applied",
                       applied_on=str(today - timedelta(days=7)))
    [r] = (await client.get("/api/v1/reminders")).json()
    assert r["kind"] == "linkedin_7" and "Développeuse IA" in r["draft"] and r["linkedin_search_url"]
async def test_sync_is_idempotent(...): ...
async def test_done_followup_sets_followed_up(...): ...
async def test_close_21_done_sets_no_answer(...): ...
async def test_postpone_twice_adds_six_days(...): ...
async def test_closed_reminder_is_409(...): ...
async def test_contact_replaces_search_link(...): ...
async def test_english_posting_gives_english_draft(...): ...
async def test_kit_followup_used_when_ready(...): ...     # pièce followups prête : son texte de 7 jours
async def test_job_runs_for_each_user(...): ...           # deux utilisatrices, chacune ses relances
async def test_reminder_data_never_logged(...): ...
```

- [ ] **Step 2–4:** fail, implement, pass (avec contrat et `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-7): relances suggérées et tâche planifiée (7.3)` ; D140.

---

### Task 7.4 : Assistant de suivi et création en une phrase (`application_intake`) ⚠ revue par tâche (Opus high : graphe)

**Zone : back (agent, graphe, port, route).** Change le contrat. Tourne avec 7.13.

**Files:**
- Create: `backend/app/agents/prompts/tracker.md`, `backend/app/agents/nodes/tracker/{__init__.py, intake.py}`, `backend/app/agents/state/application_intake.py`, `backend/app/agents/graphs/application_intake.py`, `backend/app/agents/tools/applications_port.py` (`ApplicationStore`, `NO_APPLICATIONS`, `IntakeDraft`), `backend/app/features/applications/service/agent_store.py` (`AgentApplicationStore`), `backend/tests/support/applications.py` (`FakeApplicationStore`), `backend/tests/agents/graphs/intake_support.py`
- Modify: `agents/registry.py` (`tracker` rapide), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`applications`), `bootstrap_agents.agent_ports`, `app/main.py` (argument), `features/sessions/service.py` (`ROUTE_ONLY["application_intake"] = "POST /applications/intake"`), `features/applications/router.py`, `schemas.py`
- Test: `backend/tests/agents/graphs/test_application_intake.py`, `backend/tests/features/applications/test_intake_router.py`, `test_agent_store.py`

**Interfaces:**

```python
# agents/tools/applications_port.py
class IntakeDraft(BaseModel):                 # sortie structurée de l'Assistant de suivi
    company: str = Field(min_length=1, max_length=200); title: str = Field(min_length=1, max_length=200)
    status: ApplicationStatus = "applied"; applied_on: date | None   # « hier » résolu par rapport à `today`
    channel: Channel | None = None; contact_name: str | None = None; contact_role: str | None = None
    notes: str | None = Field(default=None, max_length=500)
class ApplicationStore(Protocol):
    async def intake_context(self, user_id: str) -> IntakeContext            # today (fuseau), langue d'interface
    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]   # matching (7.1) sur les fiches
    async def save_intake(self, user_id: str, session_id: str, draft: IntakeDraft,
                          distinct_from: list[str]) -> str                   # idempotent par session ; renvoie l'id
```

Graphe : `load` → `parse` (Assistant de suivi : `structured_call(IntakeDraft)`, phrase dans `untrusted(…, "phrase de January")`, date du jour et jours de la semaine fournis ; date future refusée et redemandée ; aucun champ inventé : entreprise ou poste absents de la phrase → `run.failed` « Je n'ai pas trouvé l'entreprise ou le poste dans ta phrase. ») → `alerts` (port, lecture) → `ask` (`interrupt` seul : `kind = "application_confirm"`, question « Je crée cette fiche ? » plus le message de l'alerte la plus forte s'il y en a une, `fields` pré remplis : company, title, status, applied_on, channel, contact ; options `create`, `distinct` (seulement avec une alerte : « C'est un autre poste »), `open` (avec une alerte : « Ouvrir la fiche existante », renvoie son id), `cancel`) → `save` (création par le port avec les champs relus de la réponse, revalidés ; `distinct` → `distinct_from` = fiches de l'alerte) → `artifact.ready` (`kind = "application"`, `url = "/candidatures/<id>"`) ou fin sans fiche (`cancel`, `open`).

Route : `POST /applications/intake {text: str (1 à 1 000)}` → 202 `{session_id}` (session `application_intake`, sujet `application_intake`). Une session d'intake ouverte de l'utilisatrice → 409 `intake_in_progress` (`details.session_id`).

- [ ] **Step 1: Write the failing tests**

```python
async def test_sentence_becomes_confirmed_application(intake_runner):
    st = await run_until_question(intake_runner, "j'ai postulé hier chez Société Fictive pour le poste Développeuse IA",
                                  today=date(2026, 11, 15), tracker=[draft_json(applied_on="2026-11-14")])
    assert st.question.kind == "application_confirm" and field(st, "applied_on") == "2026-11-14"
    final = await answer(intake_runner, {"choice": "create", "fields": st.fields})
    assert store.saved == [("Société Fictive", "Développeuse IA", "applied", date(2026, 11, 14))]
async def test_intake_duplicate_shows_alert_in_question(...): ...  # message « tu as déjà postulé … le 3 novembre »
async def test_intake_distinct_creates_with_distinct_from(...): ...
async def test_intake_cancel_saves_nothing(...): ...
async def test_future_date_is_asked_again(...): ...
async def test_missing_company_fails_cleanly(...): ...
async def test_sentence_is_untrusted(...): ...          # la phrase est encadrée dans le prompt
async def test_replay_at_question_keeps_question(...): ...   # redémarrage : même question, rien d'écrit
async def test_save_is_idempotent(...): ...
async def test_intake_route_202_and_409(...): ...
async def test_intake_text_never_logged(...): ...
```

- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-7): Assistant de suivi, fiche créée en une phrase (7.4)` ; D141.

---

### Task 7.5 : Kit de candidature (`application_kit`) ⚠ revue par tâche (Opus high : graphe parallèle, honnêteté)

**Zone : back (agents, graphe, port).** Ne change pas le contrat (le port réel et les routes sont en 7.6). Tourne seule.

**Files:**
- Create: `backend/app/agents/graphs/application_kit.py`, `backend/app/agents/state/application_kit.py`, `backend/app/agents/nodes/tracker/{pieces.py, honesty.py}`, `backend/app/agents/nodes/scout/dossier.py`, `backend/app/agents/tools/kit_schema.py`, `backend/app/agents/tools/kit_port.py` (`KitStore`, `NO_KIT`), `backend/app/agents/prompts/_shared/kit.md`, `backend/tests/support/kit.py` (`FakeKitStore`), `backend/tests/agents/graphs/kit_support.py`
- Modify: `agents/prompts/tracker.md` (modes `letter`, `linkedin`, `followups`, `form_answers`, `pitch`), `agents/prompts/scout.md` (mode `dossier`), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`kit`), `bootstrap_agents.agent_ports`, `features/sessions/service.py` (`ROUTE_ONLY["application_kit"] = "POST /applications/{id}/kit"`)
- Test: `backend/tests/agents/graphs/test_application_kit.py`, `backend/tests/agents/nodes/test_kit_pieces.py`, `test_dossier.py`

**Interfaces:**

```python
# agents/tools/kit_schema.py
class Letter(BaseModel): text: Prose   # 250 à 350 mots, langue de l'offre (analysis.language) ; compté par le code
class LinkedInMessages(BaseModel): invitation: str = Field(max_length=300); message: Prose  # message ≤ 150 mots
class Followups(BaseModel): day_7: Prose; day_14: Prose      # emails de relance, ≤ 120 mots chacun
class FormAnswer(BaseModel): question: str = Field(max_length=300); answer: str = Field(max_length=800)
    fact_ids: list[str]                                      # faits du profil qui appuient la réponse
class FormAnswers(BaseModel): items: list[FormAnswer] = Field(max_length=10)  # questions éliminatoires repérées dans l'offre
class Pitch(BaseModel): text: Prose                          # « Parle-moi de toi », 130 à 170 mots (60 s)
class CompanyDossier(BaseModel):                             # une page sourcée (F16)
    activity: Prose; product: Prose; stack: list[str]; news: list[NewsItem]  # actualité ≤ 6 mois, datée, citée
    culture: Prose; interview_process: Prose; questions: list[str] = Field(min_length=5, max_length=5)
    watch_points: list[str]; size: Literal["startup", "pme", "grand_groupe", "inconnu"]
    # chaque texte cite ses sources par [n] ; une citation [n] sans source lue est retirée par le code
class KitContext(BaseModel): application_id; language: Literal["fr", "en"]; posting_text; analysis: PostingAnalysis;
    company: str; title: str; profile: MasterProfileData; company_dossier: CompanyDossier | None (≤ 30 jours);
    cv_version: CvVersionRef | None; style_guide: str; keep: list[KitKind]   # pièces modifiées par January : jamais refaites
class KitStore(Protocol):
    async def context(self, user_id: str, application_id: str) -> KitContext
    async def save_piece(self, user_id: str, session_id: str, application_id: str, kind: KitKind,
                         status: KitStatus, content: str, meta: dict[str, Any]) -> str   # idempotent (application, kind, session)
    async def save_dossier(self, user_id: str, session_id: str, company: str, dossier: CompanyDossier,
                           sources: list[SourceRef]) -> None                             # companies.dossier, idempotent
```

Graphe : `load` → branches parallèles (une par pièce non gardée) → `close`. Pièces :
- `cv` (sans LLM) : la version prête la plus récente de l'offre → `ready`, contenu « CV ciblé : version n° N » et son id en `meta` ; aucune → `to_check` « Lance la revue de CV de cette offre pour obtenir ton CV ciblé. ».
- `letter`, `linkedin`, `followups`, `pitch` (Assistant de suivi, rapide) : profil, offre et guide de style dans `untrusted` ; puis `text_claims(texte, profil, allowed=[entreprise, intitulé, termes de l'offre])` ; des claims → **un** nouvel essai avec les termes nommés (« n'écris rien qui ne soit pas dans le profil : … ») ; encore des claims → `to_check`, `meta.flags = [termes]` ; lettre hors 250–350 mots après l'essai → `to_check` avec `meta.words`.
- `form_answers` (Assistant de suivi) : questions éliminatoires repérées dans l'offre (permis, mobilité, disponibilité, autorisation de travail, langue, diplôme, salaire…), réponse tirée du profil seulement ; `is_salary_question` → réponse **vidée par le code**, `meta.salary = true` (« À remplir par toi ») ; réponse sans `fact_ids` valides → vidée, « À compléter ».
- `company_brief` (Éclaireur, mode `dossier`) : réutilise le dossier de `companies` s'il a moins de 30 jours ; sinon recherche web (`web_search` / `web_read`, 4 lectures au plus), `CompanyDossier`, citations vérifiées par le code (rôle du Vérificateur tenu par le code : aucune affirmation sans source lue, actualité datée de moins de 6 mois), rendu Markdown avec la liste des sources ; aucune page lue → `to_check` « Aucune source lisible : dossier non produit. ».
- Chaque pièce enregistrée émet `artifact.ready` (`kind = "kit_item"`, `artifact_id` = id de la pièce, titre de la pièce) **dès qu'elle est prête** ; une pièce en échec (`failed`, message lisible) n'arrête pas les autres ; `close` publie `run.completed` avec le compte des pièces.
- Le guide de style (`deps.settings.style_guide`) entre dans chaque prompt de pièce (`_shared/kit.md`), encadré `untrusted`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_kit_produces_seven_pieces(kit_runner): ...     # critère F16 : 7 pièces enregistrées, 7 artifact.ready
async def test_pieces_are_announced_as_they_finish(...): ...  # ordre des artifact.ready ≠ ordre fixe quand les délais diffèrent
async def test_letter_with_unsupported_claim_retries_then_flags(...):
    # 1er essai « 5 ans sur Kubernetes », 2e essai pareil → to_check, flags {"5", "Kubernetes"}, 2 appels
async def test_letter_fixed_on_retry_is_ready(...): ...
async def test_letter_word_count_enforced(...): ...
async def test_letter_in_posting_language(...): ...           # offre en anglais : prompt « en »
async def test_salary_answer_forced_empty(...): ...
async def test_answer_without_fact_is_emptied(...): ...
async def test_dossier_reused_when_fresh(...): ...            # < 30 jours : aucun appel de l'Éclaireur
async def test_dossier_citation_without_source_removed(...): ...
async def test_style_guide_reaches_every_piece_prompt(...): ...
async def test_kept_piece_is_not_regenerated(...): ...
async def test_failed_piece_does_not_stop_others(...): ...
async def test_kit_replay_saves_each_piece_once(...): ...     # redémarrage après 3 pièces : 7 lignes, pas 10
async def test_posting_and_profile_untrusted(...): ...
```

- [ ] **Step 2–4:** fail, implement, pass.
- [ ] **Step 5: Commit** `feat(phase-7): kit de candidature en parallèle, contrôle des faits (7.5)` ; D142.

---

### Task 7.6 : Kit : port réel, routes et archive (contrat)

**Zone : back.** Change le contrat. Tourne seule.

**Files:**
- Create: `backend/app/features/applications/service/{kit.py, kit_store.py, kit_zip.py}`, `backend/app/features/applications/router_kit.py`
- Modify: `bootstrap_career.py` / `app/main.py` (port `kit`), `features/registry.py` si un routeur de plus, `schemas.py`
- Test: `backend/tests/features/applications/{test_kit_store.py, test_kit_router.py, test_kit_zip.py}`

**Interfaces:**

```text
POST  /applications/{id}/kit                 → 202 {session_id} ; 409 kit_in_progress (details.session_id) ;
                                               409 posting_required (fiche sans offre ni texte figé) ; 409 profile_required
GET   /applications/{id}/kit                 → KitOut {session_id, running: bool, items: list[KitItemOut]} (7 kinds, ordre fixe)
PATCH /applications/{id}/kit/{kind}  {content: str ≤ 20 000}  → KitItemOut (edited = true ; une pièce to_check
                                               modifiée est recontrôlée par text_claims : flags mis à jour, ready si vide)
GET   /applications/{id}/kit.zip             → application/zip ; Content-Disposition "Kit_<Entreprise>_<Poste>.zip" (ASCII)
```

`KitItemOut` : `kind, status, content, flags: list[str], salary_fields: int, words: int | None, sources: list[SourceOut], edited, updated_at`. Archive : un fichier Markdown par pièce (`01_cv.md` … `07_pitch.md`, ordre de 6 F16), le PDF de la version prête si la pièce `cv` en a une (nom `cv_filename`), un `LISEZMOI.txt` qui nomme les pièces « à vérifier » ; pièce absente ou `failed` : omise et nommée dans `LISEZMOI.txt`. Événement `kit` dans le fil de la fiche au lancement et à la fin. Relancer le kit refait les pièces non modifiées seulement (`keep`). Le port réel lit le profil validé, l'offre (ou la copie figée de la fiche), le dossier de `companies` et `UserSettings.style_guide`.

- [ ] **Step 1: Write the failing tests** — `test_kit_launch_202_then_409`, `test_get_kit_lists_seven_kinds`, `test_patch_marks_edited_and_rechecks`, `test_zip_contains_pieces_and_pdf`, `test_zip_names_to_check_pieces`, `test_relaunch_keeps_edited`, `test_kit_never_logged`, `test_other_user_kit_404`.
- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-7): routes et archive du kit de candidature (7.6)` ; D143.

---

### Task 7.7 : Essai réel en milieu de phase (contrôleur)

**Zone : contrôleur (pile Docker, GLM 5.3 flash).** Aucun écran. Correctifs back faits dans cette tâche.

- [ ] **Step 1:** reconstruire l'image du back, `docker compose up -d --no-build backend frontend`, `date` vérifiée.
- [ ] **Step 2:** écrire `backend/scripts/check_phase7.py` partie `suivi` (étapes : `fiche depuis offre` (adoption d'une version prête ou création par `posting_id`), `doublon` (même lien → 409 certain ; intitulé « (H/F) » → probable ; autre poste même entreprise → info), `une phrase` (intake réel : fiche montrée, champs justes, création), `relance` (fiche postulée il y a 8 jours → relance `linkedin_7` avec brouillon ; `postpone` ; `done` → Relancée), `indicateurs`, `journaux`) et partie `kit` (`kit` : 7 pièces, lettre 250–350 mots dans la langue de l'offre, aucune réponse salariale remplie, pièces « à vérifier » nommées avec leurs termes et ces termes réellement absents du profil, dossier avec au moins une source, `kit.zip` téléchargé et lisible) ; même forme que `check_phase6` (`Run`, `CheckFailed`, une ligne par étape, aucune donnée imprimée), ses tests dans `backend/tests/scripts/test_check_phase7.py` ; lancé dans le conteneur jetable `learning_career_platform-check7` (`--api http://backend:8000 --part suivi|kit --logs-file -`).
- [ ] **Step 3:** deux essais réels de chaque partie ; noter durées, coûts (`llm_calls`), pièces « à vérifier » et leurs termes.
- [ ] **Step 4:** correctifs back éventuels (un test qui échoue avant), contrôles back complets.
- [ ] **Step 5: Commit** `feat(scripts): contrôle réel de la phase 7, suivi et kit (7.7)` ; D144 (résultats chiffrés).

---

### Task 7.8 : Intervieweur et entretien blanc (`interview`) ⚠ revue par tâche (Opus high : graphe à boucle d'interruptions)

**Zone : back (agent, graphe, port).** Ne change pas le contrat. Tourne avec 7.14.

**Files:**
- Create: `backend/app/agents/prompts/interviewer.md`, `backend/app/agents/nodes/interviewer/{__init__.py, plan.py, turn.py, debrief.py}`, `backend/app/agents/state/interview.py`, `backend/app/agents/graphs/interview.py`, `backend/app/agents/tools/interview_schema.py`, `backend/app/agents/tools/interview_port.py` (`InterviewStore`, `NO_INTERVIEWS`), `backend/tests/support/interviews.py`, `backend/tests/agents/graphs/interview_support.py`
- Modify: `agents/registry.py` (`interviewer` fort), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`interviews`), `bootstrap_agents.agent_ports`, `features/sessions/service.py` (`ROUTE_ONLY["interview"] = "POST /applications/{id}/interviews"`)
- Test: `backend/tests/agents/graphs/test_interview.py`, `backend/tests/agents/nodes/test_interviewer.py`

**Interfaces:**

```python
QUESTIONS_BY_DURATION = {15: 4, 30: 7, 45: 10}   # questions principales ; au plus une relance par question
class PlannedQuestion(BaseModel): text: str (≤ 400); criterion: Literal["clarte", "structure", "profondeur", "adequation"];
    source: Literal["offre", "dossier", "cv", "ecart", "general"]
class InterviewPlan(BaseModel): questions: list[PlannedQuestion]        # exactement N (redemandé sinon)
class TurnDecision(BaseModel): follow_up: str | None (≤ 300); note: int = Field(ge=1, le=5)   # note interne de la réponse
class Debrief(BaseModel):
    scores: dict[Literal["clarte", "structure", "profondeur_technique", "adequation"], int]  # 1 à 5, les 4 clés
    strengths: list[str] = Field(min_length=3, max_length=3); fixes: list[str] = Field(min_length=3, max_length=3)
    weakest_index: int; improved_answer: Prose            # version améliorée de la réponse la plus faible
    missed: list[int]                                     # indices des questions ratées (note ≤ 2)
class InterviewContext(BaseModel): mode; duration_min; language; role: str; posting_text: str | None;
    analysis: PostingAnalysis | None; dossier: CompanyDossier | None; cv_content: CvContent | None;
    gaps: list[str]; profile: MasterProfileData
class InterviewStore(Protocol):
    async def context(self, user_id: str, interview_id: str) -> InterviewContext
    async def save_result(self, user_id: str, session_id: str, interview_id: str, exchanges: list[Exchange],
                          debrief: Debrief, flags: list[str], cards: list[CardDraft]) -> None   # idempotent par session
```

Graphe : `load` → `plan` (Intervieweur, `InterviewPlan` selon le mode, la langue et les sources : offre, dossier, version du CV envoyée, écarts connus) → boucle `ask` (`interrupt` seul : `kind = "interview_answer"`, la question, un champ texte, option `stop` « Terminer l'entretien ») → `turn` (réponse dans `untrusted`, `TurnDecision` : une relance au plus par question, la relance repasse par `ask`) → … → `debrief` (`Debrief` sur les échanges ; `text_claims` sur `improved_answer` : des claims → `meta.flags`, la réponse est montrée « à vérifier ») → `save` (échanges, débrief, fiches de révision des questions ratées : recto = question, verso = points de la réponse attendue tirés du débrief) → fin. `stop` avant toute réponse → `stopped`, rien d'autre ; `stop` après au moins une réponse → débrief sur les questions répondues. Les échanges vivent dans l'état (checkpointer) jusqu'à `save`.

- [ ] **Step 1: Write the failing tests** — `test_fifteen_minutes_asks_four_questions_and_debriefs` (critère F10 : questions liées à l'offre, débrief noté sur les 4 critères, 3 forces, 3 corrections), `test_one_follow_up_at_most`, `test_stop_early_debriefs_answered_only`, `test_stop_before_any_answer_saves_stopped`, `test_english_mode_prompt`, `test_answers_are_untrusted`, `test_improved_answer_claims_flagged`, `test_missed_questions_become_cards`, `test_replay_at_question_keeps_question`, `test_double_answer_counts_once`, `test_save_idempotent`.
- [ ] **Step 2–4:** fail, implement, pass.
- [ ] **Step 5: Commit** `feat(phase-7): Intervieweur et entretien blanc (7.8)` ; D145.

---

### Task 7.9 : Entretiens : port réel, routes et fiches de révision (contrat)

**Zone : back.** Change le contrat. Tourne seule.

**Files:**
- Create: `backend/app/features/applications/service/{interviews.py, interview_store.py}`, `backend/app/features/applications/router_interviews.py`
- Modify: `bootstrap_career.py` / `app/main.py` (port `interviews`), `schemas.py`
- Test: `backend/tests/features/applications/{test_interview_store.py, test_interviews_router.py}`

**Interfaces:**

```text
POST /applications/{id}/interviews  InterviewIn       → 202 {interview_id, session_id}
POST /interviews  InterviewIn & {posting_id | role}   → 202 (entretien libre sur un poste : offre ou intitulé seul)
GET  /interviews?application_id=                      → list[InterviewOut] (récent d'abord)
GET  /interviews/{id}                                 → InterviewOut {mode, duration_min, language, status, exchanges, debrief, flags, cards_created}
InterviewIn: mode: InterviewMode; duration_min: Literal[15, 30, 45]; language: Literal["fr", "en"] = "fr"
```

Un entretien `running` de l'utilisatrice → 409 `interview_in_progress` (`details.interview_id`) ; le statut suit la session (comme D129 n° 5 : session close sans résultat → `failed` à la lecture). `save_result` : entretien `done`, événement `interview` sur la fiche (débrief rattaché), cartes par `quiz.service.cards.add_cards` (`source = "interview"`, `source_id` = id de l'entretien). Entretien libre sans fiche : aucune écriture dans le fil.

- [ ] **Step 1: Write the failing tests** — `test_launch_from_application`, `test_free_interview_on_role`, `test_second_running_is_409`, `test_result_attached_to_application_timeline`, `test_cards_created_due_tomorrow`, `test_dead_session_marks_failed`, `test_interview_never_logged`, `test_422_no_echo`.
- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-7): routes des entretiens et fiches de révision (7.9)` ; D146.

---

### Task 7.10 : Comité de recrutement simulé (`hiring_committee`), port et routes ⚠ revue par tâche (Opus high : graphe à débat)

**Zone : back.** Change le contrat. Tourne avec 7.15.

**Files:**
- Create: `backend/app/agents/prompts/{manager.md, colleague.md, _shared/committee.md}`, `backend/app/agents/nodes/committee/{__init__.py, impressions.py, debate.py, votes.py, synthesis.py}`, `backend/app/agents/state/hiring_committee.py`, `backend/app/agents/graphs/hiring_committee.py`, `backend/app/agents/tools/committee_schema.py`, `backend/app/agents/tools/committee_port.py`, `backend/app/features/applications/service/{committee.py, committee_store.py, committee_diff.py}`, `backend/app/features/applications/router_committee.py`, `backend/tests/support/committee.py`, `backend/tests/agents/graphs/committee_support.py`
- Modify: `agents/registry.py` (`manager`, `colleague` standard), `agents/prompts/{ats_reader.md, recruiter.md, moderator.md}` (mode `committee`), `agents/graphs/registry.py`, `agents/runtime/ports.py` (`committee`), `bootstrap_agents.agent_ports`, `bootstrap_career.py` / `app/main.py`, `features/sessions/service.py` (`ROUTE_ONLY["hiring_committee"] = "POST /committee"`), `features/registry.py`
- Test: `backend/tests/agents/graphs/test_hiring_committee.py`, `backend/tests/features/applications/{test_committee_router.py, test_committee_diff.py}`

**Interfaces:**

```python
PERSONAS = ("ats_reader", "recruiter", "manager", "colleague")   # filtre machine, recruteuse RH, manager, futur collègue
class Impression(BaseModel): text: Prose                          # ≤ 150 mots (9.3)
class Vote(BaseModel): vote: Literal["oui", "non", "peut_etre"]; objection: str (≤ 300); reason: Prose
class Synthesis(BaseModel): verdict: Literal["oui", "non", "peut_etre"]; objections: list[RankedObjection] (≤ 6);
    changes: list[Change] = Field(min_length=3, max_length=3)    # les 3 changements qui feraient basculer un vote
class Change(BaseModel): text: str (≤ 300); persona: str; fact_ids: list[str]   # faits du profil à mettre en avant
    # un changement qui demande un terme absent du profil (text_claims) → `needs_skill = true` (« à acquérir »), jamais « ajoute X »
class CommitteeContext(BaseModel): cv_text: str; posting_text: str; analysis: PostingAnalysis; dossier: CompanyDossier | None;
    size: Literal["startup", "pme", "grand_groupe", "inconnu"]; ats_terms: AtsTermsView   # recherches qui feraient remonter le CV
```

Graphe : `load` → `impressions` (4 appels, chacun ne voit que le CV et l'offre) → `round_1`, `round_2` (le Modérateur fixe l'ordre de parole ; chaque persona voit tous les tours précédents, répond nommément à au moins un autre dès le tour 2, 150 mots au plus : réutiliser `speak` et les règles du débat du conseil) → `votes` (4 `Vote`) → `synthesis` (Modérateur : verdict à la majorité calculée **par le code** sur les votes, le modèle classe objections et changements) → `save` → fin. Les personas s'adaptent par `size` du dossier (`_shared/committee.md`) ; Manager et Futur collègue incluent le bloc commun du Recruteur (variantes de prompt, 9.1). Au plus 17 appels.

```text
POST /committee  {cv_version_id}      → 202 {run_id, session_id} ; 404 version_not_found ; 409 version_not_ready ;
                                        409 committee_in_progress (details.run_id)
GET  /committee?posting_id=           → list[CommitteeRunOut] (récent d'abord)
GET  /committee/{id}                  → CommitteeRunOut {status, votes, verdict, objections, changes, previous: CommitteeDiff | None}
CommitteeDiff: previous_id; votes: list[{persona, before, after}]; objections_resolved: list[str]; objections_new: list[str]
```

`previous` = la dernière exécution `done` de la même offre avant celle-ci (« avant et après », F19) ; diff calculé par `committee_diff` (pur : objections comparées après normalisation, similarité ≥ 0,85 = même objection). Événement `committee` sur la fiche de l'offre quand elle existe.

- [ ] **Step 1: Write the failing tests** — `test_committee_gives_four_votes_and_three_changes` (critère F19), `test_second_round_names_another_persona`, `test_verdict_is_majority_by_code`, `test_change_with_absent_term_marked_needs_skill`, `test_personas_adapt_to_company_size`, `test_committee_replay_votes_once`, `test_second_run_shows_diff`, `test_committee_routes_202_409`, `test_committee_never_logged`, `test_at_most_seventeen_calls`.
- [ ] **Step 2–4:** fail, implement, pass (contrat, `schema.d.ts`).
- [ ] **Step 5: Commit** `feat(phase-7): comité de recrutement simulé (7.10)` ; D147.

---

### Task 7.11 : Correctifs d'ouverture (front)

**Zone : front (`cv`, `gap`).** Ne change pas le contrat. Tourne avec 7.0.

**Files:**
- Modify: `frontend/src/features/cv/pages/TemplatePage/{TemplateBody.tsx, TemplateRun.tsx}` (ou `RunFeed` par un paramètre), `frontend/src/features/cv/components/ReviewReportView/ReviewReportView.tsx`, `frontend/src/shared/i18n/messages/cvReview.ts`, la page d'une offre (titre en double), le bouton « Voir le rapport » (focus), le formulaire du profil (indices d'un 422)
- Test: les `*.test.tsx` voisins

Points : la carte « Tu valides ? » n'est plus rendue quand le modèle est `ready` ou la session finie ; libellé de `gap_terms` : « À appuyer par un fait ou à acquérir » (sens arrêté en 7.0) ; « Voir le rapport » déplace le focus sur le titre du rapport ; titre de l'offre affiché une fois ; erreurs d'un 422 du profil rattachées au bon champ malgré le nettoyage des lignes vides ; comparaison d'espaces en bord alignée entre `useEditing` et `EditField`.

- [ ] **Step 1: Write the failing tests** — `hides answered template question when ready`, `gap terms label`, `report button moves focus`, `posting title rendered once`, `profile 422 index mapping after empty rows`.
- [ ] **Step 2–4:** fail, implement, pass (`vitest`, `lint`, `typecheck`).
- [ ] **Step 5: Commit** `fix(phase-7): correctifs d'ouverture du front (7.11)` ; décision dans le rapport, recopiée en D148.

---

### Task 7.12 : Composants présentationnels des candidatures

**Zone : front, présentationnel** (ni `schema.d.ts` ni `shared/api`). Tourne avec 7.1.

**Files (un dossier par composant : `.tsx`, `.test.tsx`, `index.ts`):**
- Create: `frontend/src/features/applications/components/{StatusBadge, ApplicationCard, KanbanBoard, ApplicationTable, EventTimeline, ReminderCard, StatsBar, ContactList}/`, `frontend/src/shared/ui/DuplicateAlert/`, `frontend/src/features/applications/types.ts` (types de vue locaux), `frontend/src/shared/i18n/messages/applications.ts`
- Modify: `frontend/src/shared/session-ui/agentColors.ts` (slugs `manager`, `colleague`, contraste testé), `frontend/src/shared/i18n/messages/agents.ts` (`tracker` : « Assistant de suivi » ; `manager` : « Manager » ; `colleague` : « Futur collègue »)

Contrats des composants :
- `KanbanBoard({applications, onMove})` : 8 colonnes dans l'ordre de `STATUS_ORDER` (À postuler, Postulée, Relancée, Entretien, Offre, Refus, Sans réponse, Retirée) avec leur compte ; glisser-déposer `@dnd-kit/core` **et** menu « Déplacer vers… » sur chaque carte (clavier) ; annonce du déplacement ; `onMove(id, status)`.
- `ApplicationTable({applications, onOpen})` : colonnes entreprise, poste, statut, date de candidature, prochaine action, relances dues ; tri par clic sur l'en-tête (`aria-sort`).
- `ReminderCard({reminder, onCopy, onDone, onPostpone, onIgnore})` : qui contacter (nom et rôle, ou lien « Chercher sur LinkedIn » qui s'ouvre dans un nouvel onglet), échéance, brouillon dans un bloc lisible, boutons **Copier**, **Fait**, **Reporter de 3 jours**, **Ignorer** ; `close_21` : « Classer en Sans réponse » au lieu de Fait ; mention « Rien n'est envoyé par l'application : copie et envoie toi-même. ».
- `DuplicateAlert({alerts, onOpen, onDistinct, onCancel})` : le `message` du serveur pour l'alerte la plus forte, la liste des autres ; trois choix (6.3) ; niveau dit en texte (« certain », « probable », « possible ») et pas seulement par la couleur ; `info` rendu en simple note sans choix.
- `EventTimeline({events})` : fil chronologique daté ; `StatsBar({stats})` : compte par statut, taux de réponse (« — » si aucun), délai moyen, relances dues ; `StatusBadge`, `ApplicationCard`, `ContactList` (édition de 10 contacts au plus).

- [ ] **Step 1–4:** tests (rendu, rôles, clavier : déplacer une carte au clavier appelle `onMove`, tri, boutons de la relance, message de l'alerte, contraste des nouvelles couleurs), puis implémentation ; `vitest`, `lint`, `typecheck`.
- [ ] **Step 5: Commit** `feat(phase-7): composants des candidatures (7.12)` ; D149 recopiée.

---

### Task 7.13 : Pages des candidatures, relances et alerte doublon

**Zone : front.** Lit le contrat de 7.2 à 7.4.

**Files:**
- Create: `frontend/src/features/applications/{api.ts, manifest.ts, queryKeys.ts, toView.ts, urls.ts, errors.ts}`, `hooks/{useApplications.ts, useApplication.ts, useReminders.ts, useDueCount.ts, useIntake.ts}`, `pages/{BoardPage, ApplicationDrawer, RemindersPage, NewApplication}/`, `frontend/src/shared/realtime/useRun.ts` et `frontend/src/shared/session-ui/RunFeed/` (remontés de `features/cv`, la feature `cv` les importe d'ici, sans changement de comportement)
- Modify: `frontend/src/app/registry.ts`, `frontend/src/shared/lib/feature.ts` (`NavEntry.useBadge?: () => number | undefined`), le rendu de la navigation (`buildNav` / l'élément de nav : pastille quand le compte est > 0, texte accessible « 3 relances dues »), `frontend/src/features/gap/` (page d'une offre : appel `GET /applications/check` par son propre `api.ts`, `DuplicateAlert` partagé, bouton « Créer la candidature » quand `own` est vide), `frontend/src/test/` (harnais `applicationsHarness.tsx`, `applicationsApi.ts`)

Routes et navigation (section « Candidatures ») : `/candidatures` (Kanban, ordre 1, avec bascule Kanban / Tableau et `StatsBar`), `/candidatures/relances` (ordre 2, pastille = relances dues par `useBadge`), `/candidatures/:id` (tiroir de fiche au-dessus du tableau). Tiroir : champs modifiables (PATCH), contacts, « J'ai postulé » (événement `applied` avec date, défaut aujourd'hui), changement de statut avec date (et date d'entretien pour Entretien), version du CV envoyée (lien vers la version), relances de la fiche, fil, liens vers Kit, Entretien et Comité (7.14 à 7.16). Nouvelle fiche : formulaire manuel (409 `application_duplicate` → `DuplicateAlert` : « Ouvrir » navigue vers la fiche, « C'est un autre poste » renvoie avec `distinct_from`, « Annuler » ferme) ; « En une phrase » : champ de texte → `POST /applications/intake` → carte de confirmation (`InterruptCard` avec champs pré remplis, options du serveur) dans le fil de la session ; `artifact.ready` → ouvre la fiche. Info « même entreprise » affichée après création.

- [ ] **Step 1–4:** tests (Kanban avec données MSW, déplacement → `POST /events`, tableau trié, tiroir, « J'ai postulé », 409 doublon → alerte et ses 3 choix, phrase → confirmation → fiche ouverte, relances : copier (presse-papiers simulé), fait, reporter, ignorer ; pastille de nav ; page d'une offre : alerte du check et création ; états vide, chargement, erreur ; `cv` toujours vert après le déplacement de `useRun`) ; `vitest`, `lint`, `typecheck`.
- [ ] **Step 5: Commit** `feat(phase-7): pages des candidatures, relances et alerte doublon (7.13)` ; D150 recopiée.

---

### Task 7.14 : Page du kit

**Zone : front.** Lit le contrat de 7.6.

**Files:** `frontend/src/features/applications/pages/KitPage/`, `components/KitPiece/`, hooks `useKit.ts`, messages.

Route `/candidatures/:id/kit`. « Générer le kit » → 202 ; les pièces apparaissent **dès qu'elles sont prêtes** (`artifact.ready` du flux, puis relecture du kit) ; chaque pièce : titre, statut (prête, à vérifier avec ses termes « Absent de ton profil : … », échec), texte modifiable (sauvegarde explicite), Copier ; réponses salariales : champ vide marqué « À remplir par toi » ; dossier entreprise avec ses sources cliquables ; « Télécharger l'archive » (`kit.zip`) ; relancer le kit dit que les pièces modifiées sont gardées.

- [ ] **Step 1–4:** tests (apparition progressive avec le faux socket, pièce à vérifier, édition, copie, archive, 409 en cours) ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-7): page du kit de candidature (7.14)` ; D151 recopiée.

---

### Task 7.15 : Pages de l'entretien blanc

**Zone : front.** Lit le contrat de 7.9.

**Files:** `frontend/src/features/applications/pages/{InterviewSetup, InterviewPage}/`, `components/DebriefView/`, hooks `useInterview.ts`, messages.

Routes `/candidatures/:id/entretien` (depuis une fiche) et `/candidatures/entretien` (libre : choisir une offre ou saisir un intitulé). Réglages : mode (4), durée (15, 30, 45), langue (FR, EN). Échange écrit : une question à la fois dans le fil (`DebateFeed` / `RunFeed`), réponse par `FreeTextAnswer`, bouton « Terminer l'entretien ». Débrief : 4 notes sur 5 (texte et barre, jamais la couleur seule), 3 points forts, 3 points à corriger, réponse améliorée (« à vérifier » avec ses termes si besoin), nombre de fiches de révision créées avec un lien vers Révisions. Liste des entretiens passés sur la fiche.

- [ ] **Step 1–4:** tests (réglages, une question, réponse, terminer, débrief, entretien libre) ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-7): entretien blanc (7.15)` ; D152 recopiée.

---

### Task 7.16 : Page du comité

**Zone : front.** Lit le contrat de 7.10.

**Files:** `frontend/src/features/applications/pages/CommitteePage/`, `components/{VotesPanel, CommitteeDiffView}/`, hooks `useCommittee.ts`, messages.

Route `/candidatures/:id/comite` (choix d'une version prête du CV de l'offre). Mise en page du conseil (15.2) : fil du débat à gauche (`DebateFeed`, bulles des 4 personas et du Modérateur), à droite onglets Votes (4 votes motivés avec l'objection principale), Verdict (verdict, objections classées, 3 changements ; « à acquérir » pour un changement qui demande une compétence absente), Avant / après (diff de la précédente exécution). Bandeau permanent : « Simulation, pas une prédiction. ». « Relancer le comité » après une nouvelle version.

- [ ] **Step 1–4:** tests (fil, votes, verdict, diff, bandeau, relance) ; contrôles front.
- [ ] **Step 5: Commit** `feat(phase-7): comité de recrutement simulé (7.16)` ; D153 recopiée.

---

### Task 7.17 : Parcours de bout en bout n° 3 (cycle de candidature avec doublon et relance)

**Zone : back (scripts e2e) et front (spec Playwright).**

**Files:**
- Create: `backend/tests/e2e/applications_script.py` (réponses scriptées de l'Assistant de suivi : une `IntakeDraft`), `frontend/e2e/applications.spec.ts`
- Modify: `backend/tests/e2e/server.py` (script ajouté), `backend/tests/e2e/test_*_script.py` (le script passe la validation réelle de `IntakeDraft`)

Parcours (un test, « une candidature suit son cycle, du doublon à la relance ») : offre fictive collée (texte) → fiche créée depuis la page de l'offre → « J'ai postulé » avec une date 8 jours avant aujourd'hui → la même offre recollée par le lien de l'offre puis vue sur sa page : alerte « tu as déjà postulé … » avec la date → phrase « j'ai postulé hier chez Société Fictive pour le poste Développeuse IA » → la carte de confirmation montre l'alerte, « Annuler » → la page Relances montre la relance de 7 jours avec son brouillon, la pastille de nav vaut 1 → Copier, Fait → la fiche passe Relancée, le fil montre la relance. Aucune horloge truquée : la date de candidature fait le délai.

- [ ] **Step 1–4:** script, spec, exécution locale (Edge par config temporaire retirée ensuite) ; `test_applications_script.py` vert.
- [ ] **Step 5: Commit** `test(e2e): parcours n° 3, cycle de candidature (7.17)` ; D154.

---

### Task 7.18 : Revue complète de la phase (contrôleur)

Revue finale sur Opus high, en zones (back : fiches et relances ; back : graphes et agents ; front), une vague de corrections (un test qui échoue avant chaque correction), une re-revue ; les résiduels sont parqués ou tranchés. D155 résume.

---

### Task 7.19 : Contrôle réel de fin de phase et bilan (contrôleur)

- [ ] **Step 1:** `check_phase7` gagne les parties `entretien` (entretien réel de 15 minutes, réponses données par le script : 4 questions liées à l'offre, débrief noté, fiches de révision créées), `comite` (4 votes motivés, 3 changements, seconde exécution avec un diff) et `tout` ; ses tests.
- [ ] **Step 2:** deux essais réels `--part tout` dans le conteneur jetable ; durées, coûts, journaux relus (aucun nom d'entreprise, intitulé, contact, phrase, brouillon, réponse).
- [ ] **Step 3:** navigateur : parcours n° 1, 2 et 3 ; pages Candidatures sur la vraie pile à 1 024 px, sans défilement horizontal ni erreur de console.
- [ ] **Step 4:** `docs/superpowers/bilans/phase-7.md`, D156, plan directeur, mémoire du projet ; tag `phase-7`, push `dev`.

---

## Auto-relecture (faite à l'écriture)

- **Couverture de la spec** : 6.1 (champs, statuts, vues, copie figée, trois créations) → 7.1, 7.2, 7.4, 7.12, 7.13 ; 6.2 (5 déclencheurs, délais réglables, qui contacter, brouillon, 3 boutons, recherche LinkedIn, rien envoyé, pastille) → 7.1, 7.3, 7.12, 7.13 (brief du matin : phase 8) ; 6.3 (3 niveaux, message, 3 choix, info 30 jours, « quel que soit l'écran ») → 7.1, 7.2, 7.4, 7.13 ; 6.4 → 7.1, 7.2, 7.12 ; F10 → 7.8, 7.9, 7.15 ; F16 (7 pièces en parallèle, modifiables, archive, guide de style, jamais de salaire) → 7.5, 7.6, 7.14 ; F19 → 7.10, 7.16 ; 13.5 et 13.6 → 7.1 ; 14.2 → 7.2 à 7.10 ; 18.2 parcours n° 3 → 7.17 ; bilan phase 6 (7.0, lien version ↔ candidature, 30 jours) → 7.0, 7.11, 7.2.
- **Écarts assumés (à écrire dans les décisions)** : routes ajoutées hors de la liste 14.2 (`GET /applications/check`, `GET /applications/stats`, `POST /applications/intake`, `PATCH /applications/{id}/kit/{kind}`, `POST /interviews`, `GET /interviews…`, `GET /committee…`) ; graphe `application_intake` en plus des 16 de 9.2 (comme `web_research` et `learned_document` déjà) ; durée d'un entretien tenue par un nombre de questions ; rôle du Vérificateur dans le kit tenu par le code (aucun appel de plus) ; relances par gabarits sans LLM.
