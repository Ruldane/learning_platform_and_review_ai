# Phase 4 — Conseil et programme : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mode d'exécution déjà choisi : **subagent-driven allégé** (voir « Déroulement » ci-dessous).

**Goal:** Un objectif saisi par January passe par le Conseil (cadrage, recherche, débat de quatre agents sur 3 tours, tableau animé, 2 à 3 propositions, choix), puis le Stratège bâtit un programme semaine par semaine qui respecte 85 % du budget ; une fois le programme validé, les leçons PDF et les 3 à 6 ressources de chaque module des semaines 1 et 2 sont produites en tâche de fond, les suivantes 7 jours avant leur début ; plus le reliquat de la phase 3.

**Architecture:** Trois parcours LangGraph (`learning_council`, `program_builder`, `lesson_factory`) et sept nouveaux agents (Modérateur, Stratège, Praticien, Sceptique, Scribe, Rédacteur, Vérificateur ; l'Éclaireur de la phase 3 est réutilisé nœud pour nœud). Les agents n'importent aucune feature (contrat 6) : ils passent par trois nouveaux ports (`CouncilStore`, `ProgramStore`, `LessonStore`) regroupés avec la mémoire et le web dans un seul `AgentPorts`, branché par `app/bootstrap.py` ; un `SessionLauncher` lié après le moteur permet à un port ou à la tâche planifiée de lancer une session. Côté back, quatre features : `learning` (objectifs, propositions, tableaux), `program` (programmes, semaines, modules, tâches, versions, règles de planification, exports), `lessons` (leçons, ressources, bibliothèque, production), `skills` (référentiel, sans routeur en phase 4) ; un fournisseur `HtmlPdfRenderer` (Gotenberg `convert/html`) et des gabarits dans `backend/app/templates/` ; un paquet `app/scheduler/` (APScheduler, registre `JOBS`, tâche « leçons à J-7 »). Côté front : `Board` (Excalidraw) et les ajouts de session dans `shared/session-ui/`, features `learning/`, `program/`, `lessons/`, puis le parcours Playwright n°1.

**Tech Stack:** LangGraph, Pydantic v2, SQLAlchemy 2 + Alembic, `markdown-it-py`, `nh3`, `icalendar`, `apscheduler`, Gotenberg 8 (`convert/html`), Mermaid (fichier figé côté gabarit PDF) · React, TanStack Query, `@excalidraw/excalidraw`, `@excalidraw/mermaid-to-excalidraw`, `mermaid`, `@dnd-kit/core`, `react-markdown` + `remark-gfm`, Vitest, Testing Library, MSW, `@playwright/test`.

**Spec:** `SPEC.md` §3 (3.1 à 3.6), §4.2 et 4.5 (`lecon`, `source`, acquis `en_cours`), §9.1 à 9.6, §10.3 (praticiens, seuil 60), §11.4 (disponibilité, tours, plafond), §12.3, §13.3, §13.4, §14.1, §14.2 (« Objectifs et programme », « Leçons et ressources »), §15.1 à 15.4, §17.2 à 17.4, §18.1 (phase 4), §18.2 (parcours n°1), §18.3 (F1, F2, F3 « sujet acquis sauté »). Plan directeur : `docs/superpowers/plans/2026-11-11-00-plan-directeur.md` (§1, §2, §3, §5 « Phase 4 »). Bilans : `docs/superpowers/bilans/phase-3.md` (« Points laissés pour plus tard → Phase 4 »), `phase-2.md`. Décisions : D4, D6, D7, D9, D14, D46, D53, D57, D68, D71, D72, D77.

## Global Constraints

Toutes celles du plan directeur s'appliquent : 300 lignes par fichier et 50 par fonction ; couches router → service → repository ; filtre `user_id` partout ; mypy --strict, ruff, import-linter (7 contrats aujourd'hui, 8 après 4.10) ; eslint boundaries ; textes front centralisés ; un dossier par composant front ; features extensibles par registres et manifestes. Propres à cette phase :

- **Conseil (3.1, 3.2)** : cadrage par le Modérateur après lecture de la mémoire, **5 questions au maximum** ; recherche par l'Éclaireur (sources retenues en direct, auteur, date, langue) ; tour 1 : chaque agent publie sa position en **150 mots au maximum**, le Scribe dessine la carte du domaine ; tours suivants : **3 par défaut, réglable de 1 à 5** (`debate_rounds`) ; **2 à 3 propositions** (nom, promesse, durée en semaines, charge hebdomadaire, compétences couvertes, projet final, compromis, schéma au tableau) ; choix : un parcours, un mélange de deux, ou un nouveau tour (retour au débat).
- **Points d'arrêt** : exactement trois, rien n'avance sans January : **fin du cadrage**, **choix du parcours**, **validation du programme** ; `interrupt()` avec une charge `kind`, `question`, `options` (D14) ; **aucun effet de bord avant `interrupt()` dans un même nœud** (9.4) ; une session reprend exactement où elle s'est arrêtée, même après `docker compose restart backend`.
- **Débat (9.3)** : le Modérateur fixe l'ordre de parole ; chaque agent voit tous les tours précédents ; 150 mots au maximum ; toute affirmation sur le domaine cite une source récupérée ou un élément de la mémoire (pastilles numérotées) ; **dès le tour 2, chaque agent répond nommément à au moins un autre** ; le **Sceptique formule au moins une objection par tour** ; les messages de January sont traités **en priorité au tour suivant** et les agents y répondent nommément ; le Modérateur arrête plus tôt si les positions ne bougent plus ; plafond de tokens par session (**300 000** par défaut) et coût en direct (existants).
- **Commandes permanentes (3.2)** : Pause, Relancer un tour, Passer aux propositions, Plus concret, Plus court ; toute action passe par REST (14.1), jamais par le WebSocket.
- **Tableau (3.3)** : canevas Excalidraw ; le Scribe émet du **Mermaid `flowchart`**, jamais de coordonnées ; le front convertit avec `@excalidraw/mermaid-to-excalidraw` ; éléments un par un, **150 à 300 ms** entre deux, dans l'ordre du raisonnement ; **quatre types** : carte du domaine, graphe de prérequis, frise du parcours, comparaison des propositions ; January déplace, annote, corrige et ses modifications sont renvoyées aux agents comme un message ; **chaque état est enregistré** ; export **PNG, SVG, `.excalidraw`** ; repli : SVG Mermaid simple et erreur journalisée.
- **Programme (3.4)** : Programme → Semaine (thème, objectif mesurable, charge en heures, livrable) → Module (titre, compétences visées, prérequis, leçon liée, ressources liées) → Tâche (titre avec verbe d'action, type `lire` / `regarder` / `pratiquer` / `quiz` / `projet`, **15 à 120 minutes**, critère de fin, jour planifié). Règles : disponibilité par défaut **2 h du lundi au vendredi et un bloc de 3 à 4 h le week-end** (`Availability` existant : 120 / 180 / 240 min) ; **charge planifiée ≤ 85 % du budget** ; un sujet acquis selon la mémoire est **sauté, ou réduit à une révision de 20 minutes étiquetée « déjà acquis »** ; **chaque semaine a au moins une tâche de pratique et se termine par un quiz** ; vues semaine en calendrier, liste complète, avancement global ; export **PDF** et **`.ics`**.
- **Leçons (3.5)** : une par module, en Markdown, lisible dans l'application et en PDF ; **1 200 à 2 500 mots** ; structure fixe : objectifs (3 au maximum), prérequis, l'essentiel en 5 lignes, explication, schémas, exemple travaillé, erreurs fréquentes, exercice avec corrigé séparé, sources, auto-évaluation de 5 questions ; le Rédacteur écrit, le Vérificateur contrôle faits sourcés, liens qui répondent, absence de recopie (citations courtes et attribuées) ; PDF **A4**, gabarit HTML et CSS unique : sommaire, encadrés, schémas Mermaid en SVG, numéros de page, thème clair. Leçons et ressources en tâche de fond : **semaines 1 et 2 tout de suite, les suivantes 7 jours avant leur début**.
- **Ressources (3.6)** : **3 à 6 par module** ; type (documentation officielle, cours, vidéo, article, dépôt, papier), langue, durée, niveau, auteur, date, raison du choix en une phrase ; PDF librement téléchargeable → copie locale, sinon lien et fiche de lecture ; Bibliothèque filtrable par programme, type, langue et statut (à lire, lue). Source admise dans une leçon : **note ≥ 60** (10.3).
- **Praticiens (10.3)** : l'Éclaireur repère **5 à 10 praticiens** par objectif (nom, rôle, où ils publient) ; seules des informations professionnelles publiques sont conservées.
- **Sécurité** (17.2, 17.4) : page web, document importé, sortie d'agent relue par un autre agent et saisie de January rendue à un agent comme donnée (texte de page, titre, extrait) passent par `untrusted()` ; **le HTML de contenu envoyé à Gotenberg est nettoyé de tout script** (seuls nos fichiers figés s'exécutent, voir D89) ; Mermaid côté front rendu en `securityLevel: "strict"` ; **journaux : identifiants seulement** (utilisateur, session, objectif, programme, module, leçon), **jamais** un texte d'objectif, une réponse de cadrage, un message de January, une URL, un titre ni un extrait ; **une 422 ne renvoie jamais l'entrée** (chemins de champs seulement) ; erreurs levées `from None` quand le message d'origine pourrait citer une donnée.
- **Tests sans réseau ni LLM** : faux fournisseur LLM (`fake_llm`, ou modèles scriptés par agent), `FakeSearch`, `FakeWebReader`, `FakeHtmlRenderer`, `httpx.MockTransport` ; seuls les tests marqués `live` (désélectionnés) touchent Gotenberg. Le modèle réel de l'utilisatrice (GLM 5.3 flash, Z.ai) ne sert qu'au contrôle de fin de phase.
- Contrat front/back : toute tâche back qui change l'API régénère `contracts/openapi.json` (`cd backend && uv run python -m scripts.export_openapi`) **et** `frontend/src/shared/api/schema.d.ts` (`pnpm --dir frontend gen:api`) dans le même commit ; aucune tâche front ne modifie ces deux fichiers à la main.
- Front : textes dans `frontend/src/shared/i18n/messages/<zone>.ts` agrégés par `fr.ts` (D60) ; composants de `components/` présentationnels avec types de vue locaux (D34) ; jamais de `window.confirm` ; chaque écran a un état vide avec action, un chargement et une erreur avec « Réessayer » (15.4) ; animations < 300 ms coupées par `prefers-reduced-motion` ; colonne de lecture des leçons limitée à 72 caractères, corps 18 px ; utilisable à 1 024 px.

**À vérifier dans la documentation actuelle avant de coder (context7)**, écart suivi tel que la doc l'indique et noté dans la décision de la tâche : Gotenberg 8.40 `POST /forms/chromium/convert/html` (fichier `index.html`, ressources jointes dans le même multipart, `footer.html` et ses classes `pageNumber` / `totalPages`, champs `paperWidth`, `paperHeight`, `marginTop`…, `printBackground`, `waitForExpression`, JavaScript actif par défaut) ; `markdown-it-py` (`MarkdownIt("commonmark", {"html": False})`, tables) ; `nh3.clean` (`tags`, `attributes`, `url_schemes`, `link_rel`) ; `icalendar` (`Calendar`, `Event`, `to_ical`, `PRODID`, `VERSION`, `DTSTART;VALUE=DATE`) ; APScheduler (dernière version stable : `AsyncIOScheduler` de la 3.x ou `AsyncScheduler` de la 4.x, `max_instances=1`, `coalesce`, arrêt dans le lifespan) ; `@excalidraw/excalidraw` (compatibilité React 19, CSS à importer, `excalidrawAPI`, `updateScene`, `convertToExcalidrawElements`, `exportToBlob`, `exportToSvg`, `serializeAsJSON`, polices servies en local via `EXCALIDRAW_ASSET_PATH`) ; `@excalidraw/mermaid-to-excalidraw` (`parseMermaidToExcalidraw(definition, config)` → `{ elements, files }`, diagrammes non `flowchart` rendus en image) ; `mermaid` (`initialize({ startOnLoad: false, securityLevel: "strict" })`, `render(id, code)`, `parse`) ; `@dnd-kit/core` (`DndContext`, `useDraggable`, `useDroppable`, `KeyboardSensor`, annonces en français) ; `react-markdown` + `remark-gfm` (`skipHtml`, `urlTransform`, rendu des blocs `mermaid`) ; `@playwright/test` (`webServer` multiple, `reuseExistingServer`, installation de Chromium). LangGraph : aucun nouvel usage (boucles par arêtes conditionnelles et `interrupt()` dans un nœud dédié, comme `demo_debate`).

## Review Focus

1. **Nœud rejoué après un redémarrage pendant le Conseil** (tour de parole, Scribe, propositions, cadrage déjà répondu) : aucun tableau, lot de propositions, ligne `sources` ni réponse de cadrage en double, et la question en attente reste la même. → Tâche 4.4 `test_council_replay_does_not_duplicate_boards_or_proposals` ; tâche 4.3 `test_framing_answer_saved_once_after_replay`.
2. **« Choisir » cliqué deux fois, ou en même temps qu'une reprise par `/sessions/{id}/resume`** : un seul `program_builder` lancé, une seule proposition marquée choisie par lot, la seconde requête rend le même état. → Tâche 4.6 `test_concurrent_choose_starts_one_program_session`, `test_choose_after_generic_resume_is_idempotent`.
3. **Contenu non fiable jusqu'au PDF et au tableau** (page piégée : `<script>`, `<img onerror>`, lien `javascript:`, Mermaid avec `click` ou `%%{init}`) : HTML nettoyé, aucun script de contenu dans `index.html`, Mermaid refusé ou neutralisé, rendu strict côté front. → Tâche 4.8 `test_lesson_html_has_no_content_script`, `test_mermaid_directives_are_removed` ; tâche 4.4 `test_scribe_rejects_click_and_init_directives` ; tâche 4.11 `it("renders the fallback with strict security")`.
4. **Deux déplacements de tâches simultanés qui tiennent chacun mais pas ensemble** (ou un ajout) : la semaine ne dépasse jamais 85 %, la seconde requête reçoit une 422 lisible qui ne recopie pas la saisie. → Tâche 4.7 `test_concurrent_moves_never_exceed_85_percent`, `test_add_task_over_budget_is_refused_without_echo`.
5. **Validation du programme pendant que la tâche « J-7 » tourne, plus la fin d'une leçon qui lance la suivante** : une seule chaîne `lesson_factory` par programme, jamais deux leçons pour un module, une leçon en échec relancée au plus 3 fois. → Tâche 4.10 `test_scheduler_and_validation_start_one_chain`, `test_failed_lesson_is_retried_at_most_three_times`.

---

## Déroulement (mode allégé)

- Les tâches s'enchaînent **sans revue par tâche**, **sauf** celles marquées **⚠ revue par tâche** (Opus high) : contrat du moteur et points d'arrêt, concurrence, sécurité du PDF. Une **revue complète de la phase** (back puis front) clôt la phase avant 4.16, suivie **d'une vague de corrections** puis **d'une re-revue**.
- Chaque tâche est marquée **Zone : back** ou **Zone : front**. **Jamais deux implémenteurs back en même temps** (hook mypy et index git partagés) : au plus un back et un front ensemble. Une tâche back qui change le contrat OpenAPI (4.1, 4.6, 4.7, 4.8, 4.10) ne tourne **jamais** en parallèle d'une tâche front qui consomme ce contrat ; les tâches front présentationnelles (4.11, 4.13) n'importent ni `schema.d.ts` ni `shared/api`.
- En vague parallèle, seule la tâche back écrit dans `DECISIONS.md` ; la tâche front met sa décision dans son rapport, le contrôleur la recopie sous son numéro. Numéros réservés, une entrée par tâche : **D82** (4.1), **D83** (4.2), **D84** (4.3), **D85** (4.4), **D86** (4.5), **D87** (4.6), **D88** (4.7), **D89** (4.8), **D90** (4.9), **D91** (4.10), **D92** (4.11), **D93** (4.12), **D94** (4.13), **D95** (4.14), **D96** (4.15), **D97** (4.16). Format existant (Date, Sujet, Décision en points numérotés, Raison).
- Commits par chemins explicites (jamais `git add -A`), hooks jamais sautés ; pas de `pre-commit run --all-files` pendant qu'un autre agent écrit.

| Vague | Zone : back | Zone : front |
| --- | --- | --- |
| 1 | 4.1 ⚠ (contrat) | 4.11 (présentationnel, sans contrat) |
| 2 | 4.2 | 4.12 (consomme le contrat de 4.1) |
| 3 | 4.3 ⚠ | 4.13 (présentationnel) |
| 4 | 4.4 ⚠ | — |
| 5 | 4.5 ⚠ | — |
| 6 | 4.6 ⚠ (contrat) | — |
| 7 | 4.7 ⚠ (contrat) | 4.14 (contrat de 4.1 et 4.6 seulement) |
| 8 | 4.8 ⚠ (contrat) | — |
| 9 | 4.9 | — |
| 10 | 4.10 ⚠ (contrat) | — |
| 11 | — | 4.15 (contrat de 4.7, 4.8, 4.10) |
| — | Revue complète, vague de corrections, re-revue | |
| 12 | 4.16 (contrôleur) | |

Commandes de contrôle d'une tâche back : `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run python -m mypy app && uv run python -c "from importlinter.cli import lint_imports_command; lint_imports_command()" && uv run python -m scripts.export_openapi --check` (la longueur des fichiers est contrôlée par le hook de pre-commit au commit). Front : `cd frontend && pnpm vitest run && pnpm lint && pnpm typecheck`.

## Interfaces consommées (phases 0 à 3)

- Configuration et cœur : `app.config.Settings` (`gotenberg_url`, `data_dir`, `storage_dir`) ; `AppError(code, message, status_code=400, details=None)` ; `app.core.deps` (`Db`, `CurrentUserDep`, `RuntimeDep`, `get_providers`) ; `app.core.limits.BodySizeLimit(path=, max_bytes=)` ; `app.core.logging._QUIET_LOGGERS`.
- Composition : `app.bootstrap` (`build_providers`, `memory_providers`, `research_providers`, `open_memory_runtime`, `open_research_runtime`, `memory_gateway`, `web_gateway`, `run_settings_source`, `model_prices`, `_render_http`) ; `app.main.create_app(settings, *, memory_providers=None, research_providers=None)` et `_lifespan` ; `app.core.providers` (`Providers`, `MemoryProviders`, `ResearchProviders`).
- Moteur : `GraphDeps(user_id, session_id, models, bus, settings, session_factory, memory, web)` et `user_messages_since(seq)` ; `RunContext`, `SessionRunner(..., memory=, web=)`, `SessionRunner.start(user_id, graph, input, subject_type, subject_id)`, `agent_runtime(..., *, memory=, web=)`, `AgentRuntime(bus, runner)` ; `RunSettings(session_token_cap, debate_rounds, lesson_language, search_languages, style_guide)` ; `emit(type, payload, agent=)` ; `structured_call(model, schema, messages, *, agent, step, intent, retries=2)` ; `invoke_agent`, `call_with_retries(model, messages, *, agent, allow_empty=False, stream=True)`, `message_text`, `node_timeout(seconds)` ; `render_prompt(agent, **vars)`, `untrusted(text, label)`, `_shared/untrusted.md` ; `AGENTS` / `AgentSpec(name, tier)`, `GRAPHS` / `GraphSpec(name, input_model, build)` ; événements (`EventType`, `Citation(index, title, url, memory_item_id)`, `AgentMessagePayload.citations`, `BoardUpdatePayload(mermaid, step)`, `InterruptRequestedPayload(interrupt_id, kind, question, options)`, `ProposalReadyPayload(proposal_id, title)`, `ArtifactReadyPayload(artifact_id, kind, title, url)`, `SourceFoundPayload`, `UserMessagePayload(text)`) ; `features.sessions.service.find_active_session(db, user_id, *, graph, subject_type, subject_id)`, `SessionsService.resume/message`, `MessageRequest`, `SessionView`.
- Mémoire : `app.agents.tools.memory_port` (`MemoryGateway`, `AgentWrite(kind, title, text, reason, tags, evidence, level, source_id)`, `SkillsSummary`, `NO_MEMORY`) ; `memory_tools.memory_write`, `memory_get_skills`, `memory_search` ; `nodes/memory_context.load_memory_context(deps, *, objective, agent)` ; `MemoryRuntime`, `features.memory.service.items.MemoryService`, `AgentMemoryGateway`.
- Recherche : `app.agents.tools.web_port` (`WebGateway`, `PageRead`, `SourceVerdictView`, `WebLimits`, `KEEP_THRESHOLD = 60`, `QUOTA_CODE`, `SEARCH_UNAVAILABLE_CODE`, `NO_WEB`) ; `web_tools.web_search`, `web_read` ; nœuds de l'Éclaireur `make_plan`, `make_search`, `make_read`, `make_judge`, `make_remember` (`nodes/scout/`), `WebResearchState` ; `features.research.service` (`reading.read`, `record_verdict`, `list_sources`, `chain._release`, `gateway.AgentWebGateway`) ; `db.models.research.Source` (`kind` `page` / `person`).
- PDF et fichiers : `app.providers.pdf.base` (`RenderFailed`, `RENDER_MAX_BYTES`, `PageRenderer`), `GotenbergRenderer`, liste de refus Chromium qui laisse `file:///tmp/` (D72) ; `FileStorage.save/read/delete` (catégorie `[a-z_]{1,32}`, suffixe `.pdf`) ; `WebFetcher.fetch(url, *, content_types, headers)` ; `scripts.sample_pdf.make_pdf(lines)`.
- Réglages : `UserSettings.availability` (`Availability(weekday_minutes=120, weekend_block_min_minutes=180, weekend_block_max_minutes=240)`, `weekly_budget_minutes`), `debate_rounds`, `lesson_language`, `SettingsService(db, user_id).get()`.
- Tests back : fixtures `settings`, `db_session_factory`, `app`, `client`, `memory_providers`, `research_providers` ; `fake_memory_providers(tmp_path)`, `FakeWebReader`, `FakeRenderer` (`tests/support/memory.py`) ; `fake_research_providers` ; `FakeSearch` ; `act_as(app, user_id)`, `use_test_runtime(monkeypatch)`, `wait_status` (`tests/sessions_support.py`) ; `fake_llm(replies)`, `wait_status`, `all_events`, `final_state` (`tests/agents/runtime/runner_helpers.py`) ; `make_web_runner`, `web_support.score(...)`, `GatedModels` (`tests/agents/graphs/`).
- Front : `api`, `unwrap`, `errorMessage`, `t`, `MessageKey`, `FeatureManifest`, `NavEntry` (section `learn` déjà déclarée), `FEATURES`, `useSessionStream(sessionId, options)`, `useSessionActions(sessionId)` (`resume`, `sendMessage`, `pause`, `cancel`), `startSession`, `postResume`, `postMessage`, `SessionEvent`, `EventOf<T>`, `FeedItem`, `AgentTurn.citations`, `registerEventRenderer`, `agentIdentity` (slugs `moderator`, `strategist`, `practitioner`, `scout`, `skeptic`, `scribe`, `writer`, `verifier` déjà déclarés, noms dans `messages/agents.ts`), `AgentBubble`, `DebateFeed`, `InterruptCard`, `MessageComposer`, `SessionControls(extraActions)`, `SessionStatusBar`, `CostBadge`, `SourcesPanel`, `SourceCard`, `sourcesFromEvents`, `EmptyState`, `LoadingState`, `ErrorState`, `InlineError`, `Button`, `fieldClass` ; outillage de test `src/test/server.ts` (MSW), `fakeSocket.ts`, `queryWrapper.tsx`, `renderRoutes.tsx`, `streamHarness.ts`.

---

### Task 4.1 : Back — reliquat de la phase 3 et moteur prêt pour le Conseil ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI (`MessageRequest`, `UserMessagePayload`, `InterruptRequestedPayload`, `BoardUpdatePayload`, `SourceFoundPayload`, `SourceOut`). Risque : contrat du moteur et points d'arrêt (tous les parcours existants en dépendent).

**Files:**
- Create: `backend/app/agents/runtime/ports.py`, `backend/app/agents/runtime/launcher.py`, `backend/app/agents/runtime/speech.py`, `backend/app/agents/runtime/user_input.py`
- Modify: `backend/app/agents/runtime/events.py`, `deps.py`, `execution.py`, `runner.py`, `lifespan.py` ; `backend/app/agents/tools/web_port.py` (`PageRead.verdict`), `backend/app/agents/nodes/scout/assess.py` (rejeu de `judge`, délai par page) ; `backend/app/features/research/service/reading.py`, `gateway.py`, `chain.py`, `schemas.py` ; `backend/app/features/sessions/schemas.py`, `service.py` ; `backend/app/core/logging.py` (`httpx2`) ; `backend/app/bootstrap.py` (`agent_ports`), `backend/app/main.py` (lien du lanceur) ; tests qui passaient `memory=` / `web=` au runner (mécanique) ; `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/agents/runtime/test_ports.py`, `test_launcher.py`, `test_speech.py`, `test_user_input.py`, `test_events.py` ; `backend/tests/agents/graphs/test_web_research_nodes.py` ; `backend/tests/features/research/test_searching.py`, `test_router.py` ; `backend/tests/features/sessions/test_router.py` ; `backend/tests/core/test_logging.py`

**Interfaces:**
- Produces:

```python
# runtime/ports.py — un port de plus = un champ ici + une ligne dans bootstrap.agent_ports
@dataclass(frozen=True)
class AgentPorts:
    memory: MemoryGateway = NO_MEMORY
    web: WebGateway = NO_WEB
NO_PORTS = AgentPorts()
# GraphDeps : champ `ports: AgentPorts = NO_PORTS` ; `memory` et `web` deviennent des propriétés
#   en lecture (deps.memory is deps.ports.memory) : aucun appelant existant ne change.
# RunContext(..., ports), SessionRunner(..., ports: AgentPorts = NO_PORTS),
# agent_runtime(..., *, ports: AgentPorts = NO_PORTS) : remplacent `memory=` et `web=`.

# runtime/launcher.py — lancer une session hors requête (port, tâche planifiée)
class SessionLauncher:
    def bind(self, runner: SessionRunner) -> None
    async def start(self, user_id: str, graph: str, input: dict[str, Any], *,
                    subject_type: str | None = None, subject_id: str | None = None) -> str
#   non lié ou serveur qui s'arrête → AppError("engine_unavailable", « Le moteur d'agents n'est
#   pas prêt. », 503) ; lié par main._lifespan juste après agent_runtime

# events.py
UserCommand = Literal["another_round", "to_proposals", "more_concrete", "shorter"]
class UserMessagePayload(BaseModel): text: str = ""; command: UserCommand | None = None
class InterruptField(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]{1,32}$"); label: str; required: bool = False
    max_length: int = Field(default=2000, ge=1, le=4000)
class InterruptRequestedPayload(...): ... ; fields: list[InterruptField] = Field(default_factory=list)
BoardKind = Literal["domain_map", "prerequisites", "timeline", "comparison"]
class BoardUpdatePayload(BaseModel): mermaid: str; step: int
    board_id: str | None = None; kind: BoardKind | None = None; title: str | None = None
class SourceFoundPayload(...): ... ; kind: Literal["page", "person"] = "page"; role: str | None = None

# runtime/user_input.py
@dataclass(frozen=True)
class UserInput: seq: int; text: str; command: UserCommand | None
# GraphDeps.user_inputs_since(seq: int) -> list[UserInput]   (user_messages_since reste, pour la démo)

# runtime/speech.py — prise de parole citée et bornée (débat)
@dataclass(frozen=True)
class CitationEntry: index: int; title: str; url: str | None = None; memory_item_id: str | None = None
@dataclass(frozen=True)
class Spoken: text: str; citations: list[Citation]; words: int
def cap_words(text: str, limit: int) -> str
#   ≤ limit mots : inchangé ; sinon coupé après la dernière phrase complète (., !, ?) tenant dans
#   limit mots, à défaut les limit premiers mots suivis de « … »
def extract_citations(text: str, catalog: Sequence[CitationEntry]) -> list[Citation]
#   marqueurs [n] (et [n, m]) connus du catalogue, ordre d'apparition, sans doublon ; inconnus ignorés
async def speak(model: BaseChatModel, messages: list[BaseMessage], *, agent: str, step: str,
                intent: str, catalog: Sequence[CitationEntry], max_words: int) -> Spoken
#   agent.started, tokens en direct (call_with_retries), puis agent.message avec le texte coupé
#   et ses citations (même message_id que les tokens : la bulle est remplacée, D57)

# sessions/schemas.py
class MessageRequest(BaseModel):
    text: str = Field(default="", max_length=4000); command: UserCommand | None = None
#   texte vide ET aucune commande → 422 `invalid_input` (chemin `text`, sans recopie)

# web_port.py — PageRead gagne `verdict: SourceVerdictView | None = None` (source déjà notée)
# research/schemas.py — SourceOut gagne `kind: Literal["page", "person"]`
```

- Reliquat de la phase 3 :
  - `core/logging.py` : `"httpx2": logging.WARNING` (SDK Z.ai, URL fixe de l'API en INFO).
  - `judge` rejoué : `reading.read` rend, pour une source déjà jugée de la session, son verdict (score, verdict, raison) ; la passerelle le pose sur `PageRead.verdict` et `read` le garde dans la page de l'état ; `judge` n'appelle pas le modèle pour une page qui a déjà un verdict (il réémet `source.found` à l'identique). Délai par page `PAGE_JUDGE_TIMEOUT_S = 90` (`asyncio.timeout` autour de `_score`) : dépassé → page écartée sans note (« Note impossible à établir. »), la session continue.
  - `chain._release` : une erreur de base pendant le rendu d'une réservation Brave est avalée et journalisée par type (`SQLAlchemyError`, `OSError`) ; `SearchNotServed` est relevée telle quelle et la chaîne passe au fournisseur suivant.

- [ ] **Step 1: Write the failing tests**

```python
async def test_graph_deps_memory_and_web_come_from_ports(): ...   # deps.memory is ports.memory
async def test_runner_passes_ports_to_graphs(test_runtime): ...    # graphe de test qui lit deps.ports.web

async def test_launcher_unbound_is_engine_unavailable():
    with pytest.raises(AppError) as e: await SessionLauncher().start("u", "demo_debate", {"topic": "abc"})
    assert e.value.code == "engine_unavailable" and e.value.status_code == 503
async def test_launcher_starts_session_with_subject(test_runner): ...  # subject_type/subject_id écrits

@pytest.mark.parametrize("text,limit,expected", [
    ("Un. Deux trois. Quatre cinq six.", 3, "Un. Deux trois."),
    ("un deux trois quatre", 2, "un deux …"),
    ("court", 150, "court")])
def test_cap_words(text, limit, expected): assert cap_words(text, limit) == expected
def test_extract_citations_keeps_known_markers_in_order():
    cat = [CitationEntry(1, "A", "https://a.org"), CitationEntry(2, "Mémoire", memory_item_id="m1")]
    assert [c.index for c in extract_citations("Voir [2] puis [1], [9] et [2].", cat)] == [2, 1]
async def test_speak_emits_capped_message_with_citations(emitted, fake_model): ...  # 151 mots → 150 au plus

async def test_user_inputs_since_returns_commands(deps, bus): ...  # user.message {"text": "", "command": "shorter"}
async def test_message_without_text_or_command_is_422_without_echo(client, running_session):
    r = await client.post(f"/api/v1/sessions/{sid}/message", json={"text": "  "})
    assert r.status_code == 422 and "  " not in r.text
async def test_message_command_is_published(client, running_session): ...   # payload.command == "to_proposals"
def test_old_events_still_validate():   # charges stockées avant la phase 4 (sans fields/kind/board_id)
    assert validate_payload("board.update", {"mermaid": "flowchart TD", "step": 1})

async def test_replayed_judge_does_not_call_model_again(make_web_runner): ...  # arrêt après judge, reprise
async def test_slow_page_score_is_rejected_without_failing_session(...): ...  # PAGE_JUDGE_TIMEOUT_S=0.05
async def test_release_db_error_still_falls_back_to_next_provider(...): ...  # _release lève OperationalError
def test_httpx2_logger_is_quiet(): assert logging.getLogger("httpx2").level == logging.WARNING  # après configure_logging
async def test_sources_route_exposes_kind(client): ...
```

- [ ] **Step 2: Run** — `cd backend && uv run pytest tests/agents tests/features/research tests/features/sessions tests/core -v` → les nouveaux tests FAIL.
- [ ] **Step 3: Implement** ports, lanceur (`bootstrap.agent_ports(memory_runtime, research_runtime) -> AgentPorts`, lien dans `_lifespan` : `launcher.bind(app.state.runtime.runner)`, lanceur posé sur `app.state.launcher`), entrées de l'utilisatrice, `speech`, champs d'événements, reliquat ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; `cd frontend && pnpm typecheck` → PASS (champs ajoutés avec défaut).
- [ ] **Step 5: Décision D82** : (1) `AgentPorts` : un seul objet de ports, un port de plus = un champ + une ligne de composition (plan directeur §1) ; `memory` / `web` gardés en propriétés ; (2) `SessionLauncher` lié après le moteur (un port ou une tâche planifiée lance une session sans cycle de composition) ; (3) commandes du débat = `user.message` avec `command` (D4 étendue), texte facultatif ; (4) `InterruptRequestedPayload.fields` (cadrage à plusieurs questions, D14 gardée), `BoardUpdatePayload.board_id/kind/title`, `SourceFoundPayload.kind/role`, tous avec défaut (événements stockés compatibles) ; (5) 150 mots imposés par le code après le flux (la bulle finale remplace celle des tokens) ; citations extraites des marqueurs `[n]` d'un catalogue numéroté ; (6) reliquat phase 3 : `httpx2`, `judge` sans rappel au rejeu et délai par page de 90 s, rendu Brave qui n'arrête plus la chaîne.
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): ports regroupés, lanceur de sessions, commandes du débat ; fix(research): reliquat de la phase 3"`

---

### Task 4.2 : Back — tables de l'apprentissage et règles de planification

**Zone : back.** Ne change pas le contrat OpenAPI (aucune route).

**Files:**
- Create: `backend/app/db/models/learning.py`, `program.py`, `lessons.py`, `skills.py` ; `backend/alembic/versions/0005_learning.py` ; `backend/app/core/skills.py` ; `backend/app/agents/tools/plan_schema.py` ; `backend/app/features/program/__init__.py`, `service/__init__.py`, `service/budget.py`, `service/planning.py`, `service/packing.py`, `service/diff.py`
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/db/test_learning_migration.py`, `backend/tests/core/test_skills.py`, `backend/tests/features/program/test_budget.py`, `test_planning.py`, `test_packing.py`, `test_diff.py`

**Interfaces:**
- Produces (modèles ; types partagés avec `app.agents`, contrat 6, comme `research.py`) :

```python
# db/models/learning.py
GoalStatus = Literal["council", "chosen", "planned"]
class Goal:      # goals : text Text ; target_role String(120)|None ; deadline Date|None ;
                 # weekly_minutes Integer|None ; status String(16)="council" ; framing JSON={} ;
                 # minutes Text|None (compte rendu du Scribe) ; council_session_id String(36)|None
class Proposal:  # proposals : goal_id FK goals CASCADE ; session_id String(36) ; batch, rank Integer ;
                 # name String(120) ; promise Text ; duration_weeks, weekly_hours Integer ;
                 # skills JSON list ; final_project Text ; tradeoffs JSON list ;
                 # board_id FK boards SET NULL|None ; chosen Boolean=False
                 # unique (session_id, batch, rank) ; index (user_id, goal_id)
class Board:     # boards : goal_id FK CASCADE ; session_id String(36)|None ; step Integer ;
                 # kind String(16) (BoardKind) ; title String(200) ; mermaid Text ; scene JSON|None ;
                 # author String(16)="scribe" ; parent_id String(36)|None ;
                 # scribe_key String(80)|None, unique (user_id, scribe_key) — « session:step » du Scribe
# db/models/program.py
TaskType = Literal["lire", "regarder", "pratiquer", "quiz", "projet"]
TaskStatus = Literal["todo", "done"]; ProgramStatus = Literal["draft", "validated"]
class Program:     # goal_id FK CASCADE ; title String(200) ; version Integer=1 ; status String(16)="draft" ;
                   # start_date Date ; weekly_minutes, cap_minutes Integer ; session_id String(36)|None ;
                   # validated_at UTCDateTime|None
class Week:        # program_id FK CASCADE ; rank ; theme String(200) ; objective, deliverable Text ;
                   # start_date Date ; unique (program_id, rank)
class Module:      # week_id FK CASCADE ; program_id String(36) ; rank ; title String(200) ;
                   # skills, prerequisites JSON list ; skipped Boolean=False ; unique (week_id, rank)
class Task:        # module_id FK CASCADE ; program_id String(36) ; rank ; title String(200) ; type String(16) ;
                   # minutes Integer ; done_criterion Text ; planned_date Date ; status String(8)="todo" ;
                   # already_known Boolean=False ; index (user_id, planned_date) ; index (program_id)
class PlanVersion: # program_id FK CASCADE ; version ; snapshot JSON ; diff JSON|None ; reason String(300) ;
                   # session_id String(36)|None ; revision Integer|None ; accepted_at UTCDateTime|None ;
                   # unique (program_id, version) ; unique (user_id, session_id, revision)
# db/models/lessons.py
LessonStatus = Literal["pending", "generating", "ready", "failed"]
ResourceType = Literal["documentation", "cours", "video", "article", "depot", "papier"]
ResourceLevel = Literal["debutant", "intermediaire", "avance"]; ResourceStatus = Literal["to_read", "read"]
class Lesson:   # module_id FK modules CASCADE, unique ; program_id ; title ; markdown Text="" ;
                # word_count=0 ; status String(16)="pending" ; pdf_key String(200)|None ; attempts=0 ;
                # failure_reason String(300)|None ; session_id String(36)|None ; report JSON|None
class Resource: # module_id FK CASCADE ; program_id ; source_id String(36)|None ; type String(16) ;
                # title, url Text ; url_hash String(64) ; author Text|None ; published String(32)|None ;
                # lang String(8)|None ; duration_minutes Integer|None ; level String(16)|None ;
                # reason String(300) ; score Integer|None ; local_key String(200)|None ; note Text|None ;
                # status String(8)="to_read" ; unique (module_id, url_hash) ; index (user_id, program_id)
# db/models/skills.py
SkillLevel = Literal["declare", "en_cours", "valide", "prouve"]; LEVEL_ORDER = ("declare", "en_cours", "valide", "prouve")
class Skill:     # name String(120) ; norm_name String(120) ; domain String(120)|None ; synonyms JSON list ;
                 # unique (user_id, norm_name)
class SkillEdge: # before_id, after_id FK skills CASCADE ; unique (before_id, after_id) — before précède after
class UserSkill: # skill_id FK skills CASCADE ; level String(16)="declare" ; evidence JSON list ;
                 # unique (user_id, skill_id)
```

```python
# core/skills.py
def normalize_skill_name(name: str) -> str   # NFKD sans accents, casefold, espaces ramassés, ponctuation de bord retirée

# agents/tools/plan_schema.py — sortie structurée du Stratège (bornes = règles de 3.4)
class TaskDraft(BaseModel): title: str = Field(min_length=3, max_length=120); type: TaskType
    minutes: int = Field(ge=15, le=120); done_criterion: str = Field(min_length=3, max_length=200)
class ModuleDraft(BaseModel): title: str (3..120); skills: list[str] (1..8); prerequisites: list[str] (0..8)
    tasks: list[TaskDraft] (1..12)
class WeekDraft(BaseModel): theme: str (3..120); objective: str (3..300); deliverable: str (3..300)
    modules: list[ModuleDraft] (1..4)
class SkillDraft(BaseModel): name: str (2..120); domain: str (2..120); synonyms: list[str] (0..5)
class EdgeDraft(BaseModel): before: str; after: str
class PlanDraft(BaseModel): title: str (3..200); weeks: list[WeekDraft] (1..52)
    skills: list[SkillDraft] (1..60); edges: list[EdgeDraft] (0..120)
KnownSkills = Mapping[str, SkillLevel]   # clé : normalize_skill_name

# features/program/service/budget.py
@dataclass(frozen=True)
class Budget: weekday_minutes: int; weekend_minutes: int
    @property weekly_minutes -> int      # 5 × weekday + weekend (samedi)
    @property cap_minutes -> int         # floor(0,85 × weekly_minutes)
    def day_capacity(self, day: date) -> int   # lun-ven weekday, samedi weekend, dimanche 0
def budget_for(availability: Availability, goal_weekly_minutes: int | None) -> Budget
#   sans objectif chiffré : weekday_minutes et weekend_block_max_minutes ; sinon les deux
#   mis à l'échelle (floor) par goal_weekly_minutes / availability.weekly_budget_minutes

# features/program/service/planning.py
REVIEW_MINUTES = 20; PRACTICE_MINUTES = 45; QUIZ_MINUTES = 20; MAX_WEEKS = 52
class PlanningImpossible(AppError)   # "planning_impossible", 422, « Budget hebdomadaire trop faible pour une pratique et un quiz. »
def check_draft(draft: PlanDraft, budget: Budget) -> list[str]
#   problèmes en français pour re-demander au Stratège : semaine au-delà de cap_minutes
#   (« Semaine 3 : 760 min prévues, 714 au plus. »), semaine sans pratique ni quiz, titre de
#   tâche sans verbe d'action (premier mot finissant par -er, -ir, -re, -oir ou dans ACTION_VERBS)
def apply_known(draft: PlanDraft, known: KnownSkills) -> tuple[PlanDraft, list[str]]
#   module dont TOUTES les compétences sont connues : niveau valide ou prouve → sauté (titre rendu
#   dans la liste) ; sinon (declare, en_cours) → une seule tâche « Réviser : {titre} », lire,
#   20 min, critère « Relire la fiche et répondre aux questions d'auto-évaluation », marquée déjà acquise
def ensure_week_rules(week: WeekDraft, rank: int) -> WeekDraft
#   ajoute « Pratiquer : {thème} » (pratiquer, 45 min) si aucune pratique ; ajoute « Faire le quiz
#   de la semaine {rank} » (quiz, 20 min) si aucun quiz ; les quiz passent en dernier
def schedule(draft: PlanDraft, budget: Budget, known: KnownSkills, start: date) -> ScheduledPlan
@dataclass(frozen=True)
class ScheduledTask: title; type; minutes; done_criterion; planned_date: date; already_known: bool; module_index: int
@dataclass(frozen=True)
class ScheduledWeek: rank; theme; objective; deliverable; start_date: date; modules: list[ModuleDraft]
    tasks: list[ScheduledTask]; load_minutes: int
@dataclass(frozen=True)
class ScheduledPlan: weeks: list[ScheduledWeek]; skipped_modules: list[str]; moved_tasks: int
def next_monday(today: date) -> date   # today si lundi
def week_problems(tasks: Sequence[tuple[date, int, TaskType]], week_start: date, budget: Budget) -> list[str]
#   règles vérifiées à chaque modification (4.7) : charge ≤ cap, au moins une pratique, au moins un quiz

# features/program/service/diff.py
@dataclass(frozen=True)
class PlanDiff: added: list[str]; removed: list[str]; moved: list[tuple[str, str, str]]
    weeks_before: int; weeks_after: int   # moved : (tâche, date avant, date après)
def snapshot(plan: ScheduledPlan | ProgramRows) -> dict[str, Any]   # forme JSON de plan_versions.snapshot
def diff_plans(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> PlanDiff
#   clé d'une tâche : « {module} / {tâche} » ; before None → tout est ajouté
```

Algorithme de `schedule` (les signatures et les tests ne le déterminent pas seuls) :

```text
1. draft, skipped = apply_known(draft, known) ; chaque semaine passe par ensure_week_rules.
2. réserve = minutes du dernier quiz + minutes de la première pratique ; réserve > cap → PlanningImpossible.
3. report = []  (tâches reportées, dans l'ordre)
   pour chaque semaine i (jours = start + 7·i … +6) :
     file = report + tâches de la semaine (quiz exclus, pratique réservée exclue) ; report = []
     charge = 0 ; curseur = lundi
     pour chaque tâche t de file :
        jour = premier jour d ≥ curseur tel que reste(d) ≥ t.minutes et charge + t.minutes ≤ cap − réserve
        trouvé → placer, charge += t.minutes, curseur = d ; sinon → report.append(t)
     placer la pratique réservée (premier jour avec la place, depuis lundi), puis le quiz sur le
     dernier jour de la semaine qui a la place (samedi d'abord)
   tant que report n'est pas vide : ajouter une semaine « Suite : {thème} » (objectif et livrable
   repris, suffixe « (suite) »), avec ses propres pratique et quiz ; au-delà de MAX_WEEKS → PlanningImpossible
4. moved_tasks = nombre de tâches placées hors de leur semaine d'origine.
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_migration_0005_creates_learning_tables(alembic_db):
    assert {"goals", "proposals", "boards", "programs", "weeks", "modules", "tasks", "lessons", "resources",
            "plan_versions", "skills", "skill_edges", "user_skills"} <= tables
    assert "ix_tasks_user_planned" in indexes("tasks")
async def test_migration_0005_downgrade_drops_tables(alembic_db): ...
async def test_goal_delete_cascades_to_program_tasks(db): ...

@pytest.mark.parametrize("raw,norm", [("  Réseaux de Neurones ", "reseaux de neurones"), ("PyTorch.", "pytorch")])
def test_normalize_skill_name(raw, norm): ...

def test_default_budget_is_840_with_cap_714():
    b = budget_for(Availability(), None); assert (b.weekly_minutes, b.cap_minutes) == (840, 714)
def test_goal_hours_scale_the_budget(): ...          # 420 min voulues → weekday 60, weekend 120, cap 357
def test_sunday_has_no_capacity(): ...

def test_check_draft_reports_week_over_cap(): assert "Semaine 1 : 760 min prévues, 714 au plus." in check_draft(d760, b)
def test_valide_module_is_skipped_declare_is_reduced_to_review():
    draft, skipped = apply_known(d, {"python": "valide", "pandas": "declare"})
    assert skipped == ["Bases de Python"]
    review = draft.weeks[0].modules[0].tasks
    assert [(t.title, t.minutes, t.type) for t in review] == [("Réviser : Manipuler des données avec pandas", 20, "lire")]
def test_week_gets_practice_and_ends_with_quiz(): ...
def test_schedule_never_exceeds_85_percent(any_draft):   # plusieurs brouillons, dont 120 min × 8
    assert all(w.load_minutes <= 714 for w in schedule(any_draft, b, {}, MONDAY).weeks)
def test_overflow_moves_tasks_to_next_week_and_appends_a_week(): ...   # moved_tasks > 0, « Suite : … »
def test_quiz_is_last_task_of_each_week(): ...
def test_tasks_never_planned_on_sunday(): ...
def test_tiny_budget_is_planning_impossible(): ...      # 30 min par semaine
def test_next_monday(): assert next_monday(date(2026, 11, 12)) == date(2026, 11, 16)
def test_diff_plans_lists_added_removed_moved(): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/db tests/core tests/features/program -v` → FAIL.
- [ ] **Step 3: Implement** modèles, migration (index `(user_id, planned_date)` sur `tasks` créé ici, D5), `normalize_skill_name`, `plan_schema`, budget, règles, ordonnancement, diff.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; `alembic upgrade head` puis `downgrade -1` sur une base vide → OK.
- [ ] **Step 5: Décision D83** : (1) schéma des 13 tables (dont `scribe_key` pour l'idempotence du Scribe, `plan_versions(session_id, revision)` pour celle du Stratège, `modules.skipped`, `tasks.already_known`, `resources.note` = fiche de lecture, `lessons.attempts`) ; index `tasks(user_id, planned_date)` (13.6, préfixé par l'utilisateur) ; (2) budget : semaine = 5 jours + samedi (borne haute du bloc), dimanche libre ; heures d'objectif = mise à l'échelle ; (3) acquis valide / prouvé → sauté ; déclaré / en cours → révision de 20 min « déjà acquis » ; (4) 85 % tenus par construction (report en semaine suivante, semaine « Suite » ajoutée) après deux re-demandes au Stratège (4.5) ; (5) pratique 45 min et quiz 20 min ajoutés s'ils manquent, quiz en dernier ; (6) « verbe d'action » vérifié par une règle simple (terminaisons, liste) ; (7) début du programme au prochain lundi par défaut.
- [ ] **Step 6: Commit** — `git commit -m "feat(program): tables de l'apprentissage, budget, règles de planification et diff"`

---

### Task 4.3 : Back — Conseil (1) : port, cadrage, recherche et praticiens ⚠ revue par tâche

**Zone : back.** Ne change pas le contrat OpenAPI (le nom d'un parcours n'y figure pas). Risque : point d'arrêt n° 1 (fin du cadrage) et rejeu.

**Files:**
- Create: `backend/app/agents/tools/council_port.py` ; `backend/app/agents/prompts/moderator.md`, `backend/app/agents/prompts/_shared/council.md` ; `backend/app/agents/nodes/moderator.py` ; `backend/app/agents/nodes/scout/people.py` ; `backend/app/agents/state/learning_council.py` ; `backend/app/agents/graphs/learning_council.py` ; `backend/app/features/research/service/people.py` ; `backend/tests/support/council.py` (`FakeCouncilStore`)
- Modify: `backend/app/agents/runtime/ports.py` (`council`), `backend/app/agents/registry.py` (`moderator`), `backend/app/agents/graphs/registry.py`, `backend/app/agents/prompts/scout.md` (mode `people`), `backend/app/agents/tools/web_port.py` (`add_person`), `backend/app/features/research/service/gateway.py`
- Test: `backend/tests/agents/graphs/test_council_framing.py`, `backend/tests/agents/graphs/council_support.py`, `backend/tests/features/research/test_people.py`

**Interfaces:**
- Consumes: `AgentPorts`, `UserInput`, `InterruptField` (4.1) ; nœuds de l'Éclaireur (phase 3) ; `load_memory_context`.
- Produces:

```python
# tools/council_port.py
@dataclass(frozen=True)
class GoalBrief: goal_id: str; text: str; target_role: str | None; deadline: date | None
    weekly_minutes: int | None; framing: Mapping[str, str]
@dataclass(frozen=True)
class FramingQuestion: id: str; question: str
class ProposalDraft(BaseModel):   # sortie structurée du Stratège (4.4) ; bornes de 3.1
    name: str (3..80); promise: str (10..300); duration_weeks: int (1..52); weekly_hours: int (1..40)
    skills: list[str] (1..15); final_project: str (10..400); tradeoffs: list[str] (1..5)
@dataclass(frozen=True)
class ProposalRef: proposal_id: str; rank: int; name: str
@dataclass(frozen=True)
class Choice: action: Literal["choose", "mix"]; proposal_ids: tuple[str, ...]; start_date: date | None = None
class CouncilStore(Protocol):
    async def goal(self, user_id: str, goal_id: str) -> GoalBrief
    async def save_framing(self, user_id: str, goal_id: str, questions: Sequence[FramingQuestion],
                           answers: Mapping[str, str]) -> None                       # écrase, idempotent
    async def save_board(self, user_id: str, session_id: str, goal_id: str, *, step: int, kind: BoardKind,
                         title: str, mermaid: str) -> str                            # idempotent (session, step)
    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None
    async def save_proposals(self, user_id: str, session_id: str, goal_id: str, *, batch: int,
                             proposals: Sequence[ProposalDraft]) -> list[ProposalRef]  # idempotent (session, batch)
    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None
    async def record_choice(self, user_id: str, session_id: str, goal_id: str, choice: Choice) -> None  # idempotent
    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str  # session program_builder, idempotent
NO_COUNCIL: CouncilStore   # lève AppError("council_unavailable", …, 503)

# web_port.py
@dataclass(frozen=True)
class PersonFound: name: str; role: str; url: str; where: tuple[str, ...]
# WebGateway.add_person(user_id, session_id, person: PersonFound) -> str   (ligne `sources` kind person)
# research/service/people.py
async def record_person(db, user_id: str, session_id: str, person: PersonFound) -> Source
#   unique par (session, url_hash) ; title = nom, author = rôle, summary = « ; ».join(where),
#   status ok, verdict kept, score None ; seules ces données professionnelles publiques sont gardées

# nodes/moderator.py
AGENT = "moderator"; MAX_FRAMING_QUESTIONS = 5
class FramingPlan(BaseModel): questions: list[FramingQuestionModel] = Field(max_length=5)
def make_context(deps) -> Node      # GoalBrief + contexte mémoire (load_memory_context, objectif = texte du but)
def make_frame(deps) -> Node        # structured_call FramingPlan ; ids q1…q5 imposés par le code
def ask_framing(state) -> CouncilState       # interrupt SEUL (aucun effet avant)
def make_apply_framing(deps) -> Node         # lit la réponse, save_framing, construit `query`
# nodes/scout/people.py
MAX_PEOPLE = 10
class PeopleFound(BaseModel): people: list[PersonModel] = Field(max_length=10)   # name, role, urls (1..3)
def make_spot_people(deps) -> Node
#   à partir des pages retenues (titre, auteur, adresse encadrés par untrusted) ; une personne dont
#   aucune adresse n'est une page lue ou un résultat de la session est écartée (jamais inventée) ;
#   chaque personne gardée : add_person puis `source.found` kind person (title = nom, role, url)

# state/learning_council.py
class CouncilState(WebResearchState, total=False):   # clés de l'Éclaireur réutilisées telles quelles
    goal_id: str; goal: dict[str, Any]; context: str
    framing_questions: list[dict[str, str]]; framing_answers: dict[str, str]
    people: list[dict[str, Any]]; catalog: list[dict[str, Any]]
    round: int; rounds_target: int; order: list[str]; turn_index: int
    turns: Annotated[list[dict[str, Any]], operator.add]; last_input_seq: int
    notes: Annotated[list[str], operator.add]; angle: str | None; stop: bool
    batch: int; proposals: list[dict[str, Any]]; choice: dict[str, Any] | None; summary: str

# graphs/learning_council.py
class LearningCouncilInput(BaseModel): goal_id: str = Field(min_length=36, max_length=36)
# 4.3 : START → context → frame → ask_framing → apply_framing → plan → search → read → judge →
#       remember → spot_people → END (4.4 remplace END par le débat)
```

- Interruption n° 1 : `{"kind": "framing", "question": "Réponds aux questions de cadrage (facultatif), puis lance la recherche.", "options": [{"value": "go", "label": "Lancer la recherche"}], "fields": [{"id": "q1", "label": <question>}, …]}`. Réponse acceptée : `"go"` ou `{"answers": {"q1": "…"}}` (réponses de 2 000 caractères au plus, ids inconnus ignorés) ; toute autre forme vaut « aucune réponse ». Zéro question : l'arrêt a lieu quand même (point d'arrêt obligatoire).
- `query` de l'Éclaireur = texte de l'objectif, poste visé, puis réponses de cadrage, sur une ligne, 300 caractères au plus ; `urls` = [].
- Prompts : `moderator.md` (modes `frame`, `round`, `review` — les deux derniers remplis en 4.4) ; `_shared/council.md` : règles 9.3 recopiées, encadrement des contenus non fiables, mémoire comme source citable ; `scout.md` gagne le mode `people` (informations professionnelles publiques seulement, jamais inventer une personne). Objectif, poste et réponses de cadrage viennent de January : non encadrés (comme les remarques de D53 §5) mais jamais journalisés.
- Agent `AgentSpec(name="moderator", tier="rapide")`.

- [ ] **Step 1: Write the failing tests** (`council_support.py` : `make_council_runner` sur `fake_llm`, `FakeCouncilStore`, faux web de la phase 3)

```python
async def test_council_stops_at_framing_with_fields(make_council_runner):
    c = await make_council_runner(framing_replies(3) + [])
    view = await c.wait_status("waiting_user")
    assert view.pending_interrupt["kind"] == "framing" and [f["id"] for f in view.pending_interrupt["fields"]] == ["q1", "q2", "q3"]
    assert c.store.framing_saved == [] and c.web.search_calls == []      # rien avant la réponse
async def test_framing_never_more_than_five_questions(...): ...           # le modèle en rend 7 → schéma refusé, 2 essais
async def test_zero_question_still_stops(...): ...
async def test_answers_are_saved_and_feed_the_research_query(...):
    await c.resume({"answers": {"q1": "Je vise un poste en startup"}})
    assert c.store.framing_saved[-1][1] == {"q1": "Je vise un poste en startup"}
    assert "startup" in c.search_queries_prompt()                          # prompt de `plan`
async def test_framing_answer_saved_once_after_replay(...): ...            # arrêt dans apply_framing, reprise
async def test_research_scores_sources_and_spots_people(...):
    found = await c.source_found()
    assert sum(1 for f in found if f["kind"] == "page" and f["score"] is not None) >= 8
    assert {f["title"] for f in found if f["kind"] == "person"} == {"Ada Lovelace"}
async def test_person_without_read_url_is_dropped(...): ...                # adresse inventée → écartée
async def test_people_prompt_frames_page_metadata_as_untrusted(...): ...
async def test_record_person_is_idempotent_and_isolated(db): ...           # tests/features/research/test_people.py
async def test_logs_never_contain_goal_text_or_answers(caplog, ...): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/agents tests/features/research -v` → FAIL.
- [ ] **Step 3: Implement** le port (et son `NO_COUNCIL`, champ `council` de `AgentPorts`), `FakeCouncilStore` (en mémoire, idempotent comme le contrat), les nœuds, le prompt, le graphe partiel, `add_person` et `record_person`.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D84** : (1) port `CouncilStore` (contrat 6) ; (2) l'Éclaireur entre dans le Conseil nœud pour nœud (`CouncilState` hérite de `WebResearchState`), pas en sous-graphe : rejeu et points de contrôle identiques à la phase 3 ; (3) interruption de cadrage à champs (`fields`), arrêt même sans question, réponses enregistrées dans le nœud suivant (9.4) ; (4) praticiens : 10 au plus, une personne n'est gardée que si une adresse vient d'une page lue ou d'un résultat (« 5 à 10 » visés, jamais inventés) ; stockés dans `sources` (kind `person`) ; (5) textes de January non encadrés mais hors journaux.
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): Conseil, cadrage du Modérateur, recherche et praticiens de l'Éclaireur"`

---

### Task 4.4 : Back — Conseil (2) : débat, tableau, propositions et choix ⚠ revue par tâche

**Zone : back.** Ne change pas le contrat OpenAPI. Risque : point d'arrêt n° 2, boucles du débat, rejeu, Mermaid non fiable.

**Files:**
- Create: `backend/app/agents/prompts/strategist.md`, `practitioner.md`, `skeptic.md`, `scribe.md` ; `backend/app/agents/nodes/debate_turn.py`, `backend/app/agents/nodes/scribe.py`, `backend/app/agents/nodes/mermaid_rules.py`, `backend/app/agents/nodes/strategist/__init__.py`, `strategist/propose.py`, `backend/app/agents/nodes/council_choice.py`
- Modify: `backend/app/agents/nodes/moderator.py` (`round_start`, `round_end`), `backend/app/agents/prompts/moderator.md`, `scout.md` (mode `debate`), `backend/app/agents/graphs/learning_council.py`, `backend/app/agents/registry.py` (`strategist`, `practitioner`, `skeptic`, `scribe`)
- Test: `backend/tests/agents/graphs/test_council_debate.py`, `test_council_choice.py`, `backend/tests/agents/nodes/test_mermaid_rules.py`

**Interfaces:**
- Consumes: `speak`, `cap_words`, `CitationEntry`, `user_inputs_since`, `BoardKind` (4.1) ; `CouncilStore`, `CouncilState` (4.3).
- Produces:

```python
DEBATERS = ("strategist", "practitioner", "scout", "skeptic")   # les quatre qui débattent (9.1)
MAX_WORDS = 150; SHORT_WORDS = 80; MAX_ROUNDS = 8
# nodes/moderator.py
class RoundPlan(BaseModel): order: list[Literal[*DEBATERS]] (4, sans doublon); intent: str (≤200)
class RoundReview(BaseModel): stable: bool; summary: str = Field(min_length=1, max_length=400)
def make_round_start(deps) -> Node
#   lit user_inputs_since(last_input_seq) : messages → `notes` du tour ; commandes :
#   another_round → rounds_target + 1 (≤ MAX_ROUNDS), to_proposals → stop, more_concrete /
#   shorter → angle ; ordre de parole (structured_call RoundPlan) ; agent.message du Modérateur
#   « Tour {n} : {ordre} » ; au tour 1, construit `catalog` : sources retenues puis éléments mémoire
def make_round_end(deps) -> Node
#   tour ≥ 2 et < rounds_target : RoundReview ; stable → stop ; agent.message du résumé
# nodes/debate_turn.py — un tour de parole, commun aux quatre (comme demo_turn, D53)
def make_turn(deps) -> Node
#   agent = order[turn_index] ; regarde (sans les consommer) les commandes to_proposals arrivées ;
#   prompt : règles, catalogue numéroté (titres et résumés encadrés), tous les tours précédents,
#   notes de January (« réponds-lui nommément »), angle ; speak(max_words = 80 si angle court sinon 150)
#   contrôles du code, une nouvelle demande au plus chacun : tour ≥ 2 sans nommer un autre débatteur ;
#   Sceptique sans ligne commençant par « Objection : » ; premier orateur d'un tour avec note sans « January »
def names_other_debater(text: str, agent: str) -> bool
# nodes/mermaid_rules.py
MAX_MERMAID_LINES = 80; MAX_NODES = 40; MAX_LABEL_CHARS = 80
def mermaid_problems(code: str) -> list[str]
#   première ligne `flowchart TD|LR|TB|RL` (ou `graph …`) ; refuse `click`, `%%{`, `<script`,
#   `javascript:`, `href`, `style`/`classDef` avec `url(` ; lignes, nœuds, libellés bornés
# nodes/scribe.py
AGENT = "scribe"
class BoardDraft(BaseModel): title: str (3..120); mermaid: str (10..6000)
async def draw(deps, state, *, kind: BoardKind, step: int, brief: str) -> str | None
#   structured_call BoardDraft ; mermaid_problems non vide → une nouvelle demande ; encore invalide →
#   aucun tableau (avertissement en journal, par identifiants), le Conseil continue ;
#   sinon save_board (idempotent) puis board.update {mermaid, step, board_id, kind, title}
def make_domain_map(deps) -> Node        # après le tour 1, step 1
def make_prerequisites(deps) -> Node     # fin du débat
def make_minutes(deps) -> Node           # compte rendu ≤ 200 mots (agent.message) → save_minutes
def make_proposal_boards(deps) -> Node   # une frise par proposition (attach_board) + une comparaison
# nodes/strategist/propose.py
class ProposalSet(BaseModel): proposals: list[ProposalDraft] = Field(min_length=2, max_length=3)
def make_propose(deps) -> Node   # batch + 1 ; save_proposals ; proposal.ready par proposition
# nodes/council_choice.py
class ChoiceAnswer(BaseModel): action: Literal["choose", "mix", "another_round"]
    proposal_ids: list[str] = Field(default_factory=list, max_length=2); start_date: date | None = None
def ask_choice(state) -> CouncilState      # interrupt SEUL
def parse_choice(value: Any, batch_ids: Sequence[str]) -> ChoiceAnswer | None
#   "another_round" → another_round ; choose : 1 id du dernier lot ; mix : 2 ids distincts du lot ; sinon None
def make_finalize(deps) -> Node   # record_choice puis start_program (idempotents), résumé
```

Graphe complet (4.3 + 4.4) :

```text
… spot_people → round_start → turn ⟲ (turn_index < 4) → round_end
round_end : round == 1 → domain_map → (suite) ; stop ou round ≥ rounds_target → prerequisites
            sinon → round_start
prerequisites → minutes → propose → proposal_boards → ask_choice → route_choice
route_choice : another_round → round_start (rounds_target = round + 1) ; choix invalide → ask_choice ;
               choose / mix → finalize → END
```

- Interruption n° 2 : `{"kind": "choose_path", "question": "Choisis un parcours dans l'onglet Propositions, mélange-en deux, ou demande un autre tour.", "options": [{"value": "another_round", "label": "Demander un autre tour"}]}`.
- Prompts : `strategist.md` (modes `debate`, `propose` ; `plan` en 4.5), `practitioner.md`, `skeptic.md` (« au moins une objection, ligne « Objection : … » »), `scribe.md` (modes `board` par type, `minutes`), `scout.md` mode `debate` ; tous incluent `_shared/council.md` et `_shared/untrusted.md`.
- Agents : `strategist` (`fort`), `practitioner` (`standard`), `skeptic` (`standard`), `scribe` (`rapide`).

- [ ] **Step 1: Write the failing tests**

```python
async def test_four_agents_debate_three_rounds(make_council_runner):   # debate_rounds = 3
    msgs = await c.agent_messages(step_prefix="tour-")
    assert Counter(m.agent for m in msgs) == {a: 3 for a in DEBATERS}
    assert all(len(m.payload["text"].split()) <= 150 for m in msgs)
async def test_turn_cites_catalog_entries(...): ...           # « [1] » → citations[0].url == URL_A
async def test_round_two_reply_must_name_another_agent(...): ...   # 1re réponse sans nom → 2e demande
async def test_skeptic_raises_an_objection_each_round(...): ...
async def test_message_during_round_one_is_answered_by_name_in_round_two(...):
    await c.post_message("Je préfère les projets pratiques")   # pendant le tour 1
    first = (await c.agent_messages(step_prefix="tour-2"))[0]
    assert "January" in first.payload["text"] and "projets pratiques" in c.prompt_of(first)
async def test_shorter_command_caps_turns_at_80_words(...): ...
async def test_to_proposals_command_skips_remaining_rounds(...): ...
async def test_moderator_stops_early_when_positions_are_stable(...): ...
async def test_scribe_draws_domain_map_after_round_one(...):
    b = await c.events("board.update"); assert b[0].payload["kind"] == "domain_map" and b[0].payload["board_id"]
@pytest.mark.parametrize("code", ["flowchart TD\nA-->B\nclick A \"https://x\"", "%%{init: {}}%%\nflowchart TD\nA-->B",
                                  "flowchart TD\nA[\"<script>x</script>\"]-->B", "sequenceDiagram\nA->>B: x"])
def test_scribe_rejects_click_and_init_directives(code): assert mermaid_problems(code)
async def test_invalid_board_twice_is_skipped_without_failing(...): ...
async def test_two_to_three_proposals_then_choice_interrupt(...):
    assert len(await c.events("proposal.ready")) in (2, 3) and c.pending["kind"] == "choose_path"
async def test_another_round_returns_to_debate_then_new_batch(...): ...   # batch 2, nouvelles propositions
async def test_invalid_choice_asks_again(...): ...
async def test_mix_records_two_proposals_and_starts_program(...):
    assert c.store.choices[-1].proposal_ids == (p1, p2) and c.store.programs_started == 1
async def test_council_replay_does_not_duplicate_boards_or_proposals(...):
    # arrêt pendant proposal_boards (recover_on_startup) puis reprise
    assert len(c.store.boards) == boards_before_restart + expected_rest and len(c.store.batches) == 1
async def test_token_cap_fails_council_readably(...): ...       # session_token_cap bas → run.failed lisible
```

- [ ] **Step 2: Run** — `uv run pytest tests/agents -v` → FAIL.
- [ ] **Step 3: Implement** nœuds, prompts, graphe complet ; registre des agents.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D85** : (1) un nœud `turn` commun aux quatre débatteurs, une exécution = une prise de parole = un point de contrôle (Praticien et Sceptique : un prompt chacun, nœud partagé comme D53 §3) ; (2) règles 9.3 tenues par le code (150 / 80 mots, nom d'un autre agent dès le tour 2, objection du Sceptique, réponse à January) avec une seule nouvelle demande, puis acceptation journalisée par identifiants ; (3) commandes lues au début du tour, `to_proposals` aussi entre deux prises de parole ; 8 tours au plus ; (4) catalogue de citations : sources retenues puis mémoire, numérotées une fois au tour 1 ; (5) Mermaid filtré par le code (`click`, `%%{`, HTML, schémas non `flowchart`), deux échecs → pas de tableau, le Conseil continue ; (6) propositions du Stratège par lot (un nouveau tour = un nouveau lot) ; choix invalide → question reposée ; le Conseil lance lui-même `program_builder` (lanceur), quel que soit le chemin de la réponse ; (7) compte rendu du Scribe gardé sur l'objectif pour le Stratège.
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): débat du Conseil, tableau du Scribe, propositions et choix"`

---

### Task 4.5 : Back — Programme : port et parcours `program_builder` ⚠ revue par tâche

**Zone : back.** Ne change pas le contrat OpenAPI. Risque : point d'arrêt n° 3 et boucle de révision.

**Files:**
- Create: `backend/app/agents/tools/program_port.py` ; `backend/app/agents/nodes/strategist/plan.py` ; `backend/app/agents/state/program_builder.py` ; `backend/app/agents/graphs/program_builder.py` ; `backend/tests/support/program.py` (`FakeProgramStore`, qui appelle les vraies règles de 4.2)
- Modify: `backend/app/agents/runtime/ports.py` (`program`), `backend/app/agents/graphs/registry.py`, `backend/app/agents/prompts/strategist.md` (mode `plan`)
- Test: `backend/tests/agents/graphs/test_program_builder.py`

**Interfaces:**
- Consumes: `PlanDraft`, `KnownSkills` (4.2) ; `ProposalDraft`, `GoalBrief` (4.3) ; `AgentPorts`.
- Produces:

```python
# tools/program_port.py
@dataclass(frozen=True)
class BudgetView: weekly_minutes: int; cap_minutes: int; weekday_minutes: int; weekend_minutes: int
@dataclass(frozen=True)
class ProgramContext: goal: GoalBrief; proposals: list[ProposalDraft]; budget: BudgetView
    known_skills: KnownSkills; language: str; council_minutes: str | None
    current_plan: str | None      # plan courant en texte (modifs de January comprises), pour une révision
@dataclass(frozen=True)
class DraftSaved: program_id: str; version: int; weeks: int; total_minutes: int
    skipped_modules: list[str]; moved_tasks: int
class ProgramStore(Protocol):
    async def context(self, user_id: str, goal_id: str, proposal_ids: Sequence[str],
                      program_id: str | None) -> ProgramContext
    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]
    async def save_draft(self, user_id: str, session_id: str, goal_id: str, draft: PlanDraft, *,
                         revision: int, start_date: date | None, reason: str) -> DraftSaved
    #   idempotent par (session, revision) ; revision 0 crée le programme, les suivantes une version
    async def validate(self, user_id: str, session_id: str, program_id: str) -> None   # idempotent
NO_PROGRAM: ProgramStore

# graphs/program_builder.py
class ProgramBuilderInput(BaseModel):
    goal_id: str (36); proposal_ids: list[str] = Field(min_length=1, max_length=2); start_date: date | None = None
# START → context → draft → save → ask_validation → route : validate → finalize → END ;
#                                                    revise → draft (revision + 1, note) ; invalide → ask_validation
# nodes/strategist/plan.py
MAX_PLAN_ASKS = 3     # une demande + deux re-demandes avec les problèmes de check_draft
def make_draft(deps) -> Node   # structured_call PlanDraft ; problèmes → nouvelle demande ; reste tel quel ensuite
def make_save(deps) -> Node    # save_draft ; artifact.ready {kind "program", title, url "/apprendre/programme/{id}"}
class ValidationAnswer(BaseModel): action: Literal["validate", "revise"]; note: str = Field(default="", max_length=2000)
def ask_validation(state) -> ProgramState   # interrupt SEUL
def make_finalize(deps) -> Node              # validate (idempotent), résumé
```

- Interruption n° 3 : `{"kind": "validate_program", "question": "Déplace, supprime ou ajoute des tâches dans le calendrier, puis valide le programme ou demande une révision.", "options": [{"value": "validate", "label": "Valider le programme"}], "fields": [{"id": "note", "label": "Ce qu'il faut revoir (pour une révision)"}]}`. Réponses : `"validate"`, `{"action": "validate"}`, `{"action": "revise", "note": "…"}` ou `{"answers": {"note": "…"}}` (= révision) ; autre forme → question reposée.
- Prompt `plan` : budget (minutes, plafond de 85 %), disponibilité, acquis connus (« ne replanifie pas ce qui est acquis »), propositions choisies (deux = mélange), compte rendu du Conseil, plan courant et note de révision (encadrés : texte saisi puis repris par un modèle), règles de 3.4 (champs obligatoires, 15–120 min, verbe d'action, pratique et quiz chaque semaine), langue des leçons ; référentiel de compétences (noms, domaines, synonymes) et liens de prérequis.

- [ ] **Step 1: Write the failing tests**

```python
async def test_builder_saves_draft_and_stops_for_validation(make_builder_runner):
    assert c.pending["kind"] == "validate_program" and c.store.drafts[0].revision == 0
    assert (await c.events("artifact.ready"))[0].payload["kind"] == "program"
async def test_draft_over_budget_is_asked_again_with_problems(...):
    assert "714 au plus" in c.prompt_of_call(2)
async def test_third_bad_draft_is_packed_by_rules(...): ...   # save_draft quand même ; semaines ≤ 714
async def test_known_skill_reduced_to_review(...): ...        # acquis « pandas » declare → révision 20 min déjà acquise
async def test_revise_note_produces_a_new_version(...):
    await c.resume({"action": "revise", "note": "Moins de vidéos"})
    assert [d.revision for d in c.store.drafts] == [0, 1] and "Moins de vidéos" in c.prompt_of_last_plan()
async def test_validate_calls_store_once_even_after_replay(...): ...
async def test_invalid_answer_asks_again(...): ...
async def test_planning_impossible_fails_readably(...): ...    # budget 30 min → run.failed « Budget hebdomadaire trop faible… »
```

- [ ] **Step 2: Run** — `uv run pytest tests/agents/graphs/test_program_builder.py -v` → FAIL.
- [ ] **Step 3: Implement** port, `FakeProgramStore`, nœuds, prompt, graphe, registre.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D86** : (1) port `ProgramStore` ; les règles de 3.4 vivent dans la feature (`check_draft`, `schedule`), appelées par le port : un seul jeu de règles pour le Stratège et pour les modifications de January ; (2) deux re-demandes puis rangement par le code (D83 §4) ; (3) le plan est en base, pas dans l'état du graphe : une révision relit le plan modifié par January ; (4) révision = nouvelle version (`plan_versions`), diff calculé ; (5) validation par l'interruption ou par `POST /programs/{id}/validate` (4.7), `validate` du port idempotent.
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): Stratège et parcours program_builder"`

---

### Task 4.6 : Back — feature `learning` : objectifs, propositions, choix, tableaux ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI. Risque : concurrence (double « Choisir », choix et reprise générique), reprise d'interruption par une feature.

**Files:**
- Create: `backend/app/features/learning/__init__.py`, `schemas.py`, `router.py`, `repository/__init__.py`, `repository/goals.py`, `repository/proposals.py`, `repository/boards.py`, `service/__init__.py`, `service/goals.py`, `service/choice.py`, `service/boards.py`, `service/store.py` (`AgentCouncilStore`), `service/runtime.py` (`LearningRuntime` : verrous)
- Modify: `backend/app/features/registry.py`, `backend/app/bootstrap.py` (`agent_ports` : `council`), `backend/app/main.py` (`BodySizeLimit` sur `/api/v1/boards`, 2 Mio ; `app.state.learning`), `backend/app/core/deps.py` (`LearningDep`), `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/features/learning/conftest.py`, `test_goals_router.py`, `test_choice.py`, `test_boards_router.py`, `test_store.py`

**Interfaces:**
- Consumes: `CouncilStore`, `Choice` (4.3) ; `SessionLauncher` (4.1) ; `find_active_session`, `SessionsService` ; graphes `learning_council`, `program_builder`.
- Produces:

```python
# schemas.py
class GoalCreate(BaseModel): text: str (5..500); target_role: str | None (≤120); deadline: date | None
    weekly_hours: int | None = Field(default=None, ge=1, le=40)   # deadline passée → 422
class GoalOut(BaseModel): id; text; target_role; deadline; weekly_hours; status: GoalStatus
    council_session_id: str | None; program_id: str | None; program_session_id: str | None; created_at
class GoalStarted(BaseModel): goal: GoalOut; session_id: str
class ProposalOut(BaseModel): id; goal_id; batch; rank; name; promise; duration_weeks; weekly_hours
    skills: list[str]; final_project; tradeoffs: list[str]; board_id: str | None; chosen: bool
class ChooseRequest(BaseModel): mix_with: str | None = None; start_date: date | None = None
class ChooseOut(BaseModel): council_session_id: str; status: SessionStatus
class BoardOut(BaseModel): id; goal_id; session_id: str | None; step; kind: BoardKind; title; mermaid
    scene: dict[str, Any] | None; author: Literal["scribe", "user"]; parent_id: str | None; created_at
class BoardEdit(BaseModel): scene: dict[str, Any]; note: str = Field(min_length=1, max_length=2000)

# routes (préfixe /api/v1)
POST /goals -> 201 GoalStarted          # crée l'objectif et lance `learning_council` (sujet goal)
GET  /goals -> list[GoalOut]            # récents d'abord
GET  /goals/{goal_id} -> GoalOut
GET  /goals/{goal_id}/proposals -> list[ProposalOut]     # dernier lot
POST /proposals/{proposal_id}/choose -> 202 ChooseOut
GET  /goals/{goal_id}/boards -> list[BoardOut]           # tous les états, dans l'ordre
POST /boards/{board_id}/edits -> 201 BoardOut            # nouvel état « user » + message à la session

# service/choice.py
async def choose(runtime: AgentRuntime, learning: LearningRuntime, db: AsyncSession, user_id: str,
                 proposal_id: str, req: ChooseRequest) -> ChooseOut
#   sous learning.goal_lock(user_id, goal_id) :
#   1. proposition (et mix_with) du DERNIER lot de l'objectif, sinon 404 / 422 `invalid_mix` ;
#   2. record_choice (même écriture que le nœud) ;
#   3. session du Conseil `waiting_user` sur `choose_path` → SessionsService.resume(valeur choose/mix) ;
#      déjà reprise, ou terminée avec ce choix → rien (idempotent) ; autre état → 409 `council_not_waiting`
# service/store.py — AgentCouncilStore(session_factory, launcher, learning: LearningRuntime)
#   start_program : sous goal_lock ; programme existant pour l'objectif ou session program_builder
#   ouverte (find_active_session, sujet goal) → la rend ; sinon launcher.start("program_builder", …,
#   subject_type="goal", subject_id=goal_id) ; goal.status = "chosen"
# service/boards.py
async def save_edit(db, runtime, user_id: str, board_id: str, edit: BoardEdit) -> BoardOut
#   nouvel état (author user, parent_id) ; session du Conseil ouverte → message « [Tableau] {note} »
#   (SessionsService.message) ; session close → état gardé, aucun message
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_create_goal_starts_council(client, test_runtime):
    r = await client.post("/api/v1/goals", json={"text": "Devenir AI product engineer"})
    assert r.status_code == 201 and r.json()["goal"]["council_session_id"] == r.json()["session_id"]
async def test_goal_with_past_deadline_is_422_without_echo(client): ...
async def test_goals_isolated_between_users(client, app): ...
async def test_proposals_route_returns_latest_batch(client, seeded): ...
async def test_choose_resumes_council_with_choice(client, council_waiting_choice):
    r = await client.post(f"/api/v1/proposals/{p1}/choose", json={})
    assert r.status_code == 202 and resumed_value() == {"action": "choose", "proposal_ids": [p1], "start_date": None}
async def test_choose_mix_requires_two_of_latest_batch(client, ...): ...   # ancien lot → 422 invalid_mix
async def test_concurrent_choose_starts_one_program_session(client, ...):
    await asyncio.gather(*(client.post(f"/api/v1/proposals/{p1}/choose", json={}) for _ in range(3)))
    assert await count_sessions("program_builder") == 1 and chosen_ids() == {p1}
async def test_choose_after_generic_resume_is_idempotent(client, ...): ...
async def test_choose_when_council_running_is_409(client, ...): ...
async def test_board_edit_saves_state_and_messages_the_session(client, ...):
    assert last_user_message() == "[Tableau] J'ai ajouté Docker"
async def test_board_edit_over_2_mib_is_413(client): ...
async def test_store_save_board_is_idempotent(db): ...                     # test_store.py
async def test_start_program_returns_existing_session(db, launcher): ...
async def test_routes_never_log_goal_text(client, caplog): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/features/learning -v` → FAIL.
- [ ] **Step 3: Implement** feature, `AgentCouncilStore`, branchement (`agent_ports(..., learning=)`), limites de taille ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; 5 passages de `-k concurrent`.
- [ ] **Step 5: Décision D87** : (1) `POST /goals` lance le Conseil (aucune route de session à part) ; (2) `choose` écrit le choix puis reprend l'interruption ; la reprise générique reste possible, le nœud `finalize` réécrit le même choix et lance `program_builder` : un seul chemin de lancement, idempotent sous verrou par objectif (un processus) ; (3) routes hors 14.2 : `GET /goals/{id}`, `GET /goals/{id}/boards`, `POST /boards/{id}/edits` (3.3 : « chaque état est enregistré », « modifications renvoyées aux agents ») ; scène ≤ 2 Mio ; (4) une modification du tableau devient un `user.message` « [Tableau] … » lu au tour suivant.
- [ ] **Step 6: Commit** — `git commit -m "feat(learning): objectifs, propositions, choix du parcours et états du tableau"`

---

### Task 4.7 : Back — feature `program` : programmes, tâches, validation, compétences, `.ics` ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI. Risque : concurrence (85 % sous modifications simultanées, double validation), synchronisation des niveaux (D6).

**Files:**
- Create: `backend/app/features/program/schemas.py`, `router.py`, `repository/__init__.py`, `repository/programs.py`, `repository/tasks.py`, `repository/versions.py`, `service/programs.py`, `service/editing.py`, `service/validation.py`, `service/store.py` (`AgentProgramStore`), `service/ics.py`, `service/runtime.py` (verrous) ; `backend/app/features/skills/__init__.py`, `repository.py`, `service.py` ; `backend/app/features/memory/service/skill_levels.py`
- Modify: `backend/app/features/registry.py`, `backend/app/bootstrap.py` (`program`), `backend/app/main.py`, `backend/app/core/deps.py`, `backend/pyproject.toml` (`uv add icalendar`), `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/features/program/test_router.py`, `test_editing.py`, `test_validation.py`, `test_store.py`, `test_ics.py` ; `backend/tests/features/skills/test_service.py` ; `backend/tests/features/memory/test_skill_levels.py`

**Interfaces:**
- Consumes: règles et `diff_plans` (4.2), `ProgramStore` (4.5), `SessionsService.resume`.
- Produces:

```python
# schemas.py
class TaskOut(BaseModel): id; module_id; title; type: TaskType; minutes; done_criterion; planned_date: date
    status: TaskStatus; already_known: bool
class ModuleOut(BaseModel): id; rank; title; skills; prerequisites; skipped: bool
    lesson_id: str | None; lesson_status: LessonStatus | None; resources_count: int; tasks: list[TaskOut]
class WeekOut(BaseModel): id; rank; theme; objective; deliverable; start_date; load_minutes: int
    load_hours: float   # arrondi au demi-heure
    modules: list[ModuleOut]
class ProgressOut(BaseModel): done_tasks; total_tasks; done_minutes; total_minutes
class PlanDiffOut(BaseModel): added: list[str]; removed: list[str]; moved: list[MovedTaskOut]; weeks_before; weeks_after
class ProgramOut(BaseModel): id; goal_id; title; status: ProgramStatus; version; start_date
    weekly_minutes; cap_minutes; weekday_minutes; weekend_minutes; session_id: str | None
    weeks: list[WeekOut]; progress: ProgressOut; diff: PlanDiffOut | None
class ProgramSummaryOut(BaseModel): id; goal_id; title; status; start_date; weeks: int; progress: ProgressOut
class TaskCreate(BaseModel): module_id; title (3..120); type: TaskType; minutes (15..120); done_criterion (3..200); planned_date
class ProgramPatch(BaseModel): start_date: date | None = None   # brouillon seulement
    add_tasks: list[TaskCreate] = Field(default_factory=list, max_length=20)
    delete_task_ids: list[str] = Field(default_factory=list, max_length=50)
class TaskPatch(BaseModel): planned_date: date | None; status: TaskStatus | None; title: str | None (3..120)
    minutes: int | None (15..120)
class ValidateOut(BaseModel): program_id: str; status: ProgramStatus; session_id: str | None

GET   /programs -> list[ProgramSummaryOut]       # hors 14.2 : écran « Programme »
GET   /programs/{program_id} -> ProgramOut
PATCH /programs/{program_id} -> ProgramOut
POST  /programs/{program_id}/validate -> 202 ValidateOut
PATCH /tasks/{task_id} -> TaskOut
GET   /programs/{program_id}/export.ics -> text/calendar (Content-Disposition « programme.ics »)

# service/editing.py — toutes les modifications sous program_lock(user_id, program_id)
WeekRuleBroken(AppError)  # "week_over_budget" / "week_needs_quiz" / "week_needs_practice" /
                          # "date_outside_program", 422, details {week_rank, planned_minutes, cap_minutes}
async def move_or_edit_task(...), add_and_delete(...)   # règles de week_problems sur chaque semaine touchée
# service/validation.py
async def validate_program(ctx: ValidationContext, user_id: str, program_id: str, *, session_id: str | None) -> None
#   idempotent : statut validated, validated_at, version acceptée (accepted_at) ;
#   compétences : SkillsService.upsert_catalog(skills, edges) puis raise_levels(couvertes, "en_cours",
#   preuve « Programme {titre} ») ; chaque niveau changé reflété en mémoire (reflect_skill_level, D6)
# routeur validate : sous le verrou, règles vérifiées sur l'état courant ; session program_builder
#   en attente sur validate_program → resume("validate") (202, session_id) ; déjà validé → 202 sans
#   session ; brouillon sans session ouverte → validate_program en ligne
# service/ics.py
def program_ics(program: ProgramOut) -> bytes
#   un VEVENT par tâche : DTSTART;VALUE=DATE, SUMMARY = titre, DESCRIPTION = type, durée, critère,
#   module ; UID « {task_id}@tremplin » ; PRODID « -//Tremplin//Programme//FR » ; X-WR-CALNAME = titre
# skills/service.py
class SkillsService:
    def __init__(self, db: AsyncSession, user_id: str) -> None
    async def upsert_catalog(self, skills: Sequence[SkillDraft], edges: Sequence[EdgeDraft]) -> dict[str, str]
    async def raise_levels(self, names: Sequence[str], level: SkillLevel, evidence: str) -> list[tuple[str, SkillLevel]]
    #   ne baisse jamais un niveau ; rend (nom, nouveau niveau) des changements
    async def known_levels(self) -> dict[str, SkillLevel]
# memory/service/skill_levels.py
async def reflect_skill_level(runtime: MemoryRuntime, user_id: str, *, title: str, level: SkillLevel,
                              author: str, session_id: str | None, reason: str) -> str
#   crée l'acquis ou monte son niveau (jamais plus bas), journal memory_writes
# service/store.py — AgentProgramStore(session_factory, memory: MemoryRuntime, settings_reader)
#   context : budget_for(réglages, objectif), known_skills = max(user_skills, acquis de la mémoire)
#   save_draft : schedule(...) puis lignes (programme, semaines, modules, tâches) et plan_versions
#   (snapshot, diff avec la version précédente) ; validate : validate_program
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_program_view_has_week_fields_and_progress(client, draft_program): ...   # thème, objectif, livrable, charge
async def test_move_task_within_budget(client, draft_program): ...
async def test_move_over_85_percent_is_422(client, ...):
    r = await client.patch(f"/api/v1/tasks/{tid}", json={"planned_date": "2026-11-17"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "week_over_budget"
async def test_concurrent_moves_never_exceed_85_percent(client, ...):
    await asyncio.gather(move(t1, MONDAY_W2), move(t2, MONDAY_W2))    # chacune tient seule
    assert week_load(2) <= 714
async def test_add_task_over_budget_is_refused_without_echo(client, ...):
    r = await client.patch(f"/api/v1/programs/{pid}", json={"add_tasks": [{... "title": "Titre-unique-xyz" ...}]})
    assert r.status_code == 422 and "Titre-unique-xyz" not in r.text
async def test_deleting_last_quiz_is_refused(client, ...): ...
async def test_date_outside_program_is_refused(client, ...): ...
async def test_validate_resumes_builder(client, builder_waiting): ...
async def test_double_validate_is_idempotent(client, ...): ...                # une version acceptée
async def test_validation_sets_skills_in_progress_and_reflects_memory(db, memory_runtime):
    assert levels["pandas"] == "en_cours" and acquis("pandas").meta["level"] == "en_cours"
async def test_validation_never_lowers_a_level(db, ...): ...                  # « valide » reste « valide »
async def test_ics_has_one_all_day_event_per_task(client, ...):
    cal = Calendar.from_ical(r.content); assert len(cal.walk("VEVENT")) == n_tasks
    assert r.headers["content-type"].startswith("text/calendar")
async def test_programs_isolated_between_users(client, app): ...
async def test_store_save_draft_idempotent_per_revision(db): ...
async def test_known_skills_merge_user_skills_and_memory(db, ...): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/features/program tests/features/skills tests/features/memory -v` → FAIL.
- [ ] **Step 3: Implement** features `program` et `skills`, reflet en mémoire, `.ics`, `AgentProgramStore`, branchement ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; 5 passages de `-k concurrent`.
- [ ] **Step 5: Décision D88** : (1) 85 %, pratique et quiz vérifiés à chaque modification, sous verrou par programme (un processus) ; (2) dimanche autorisé pour un déplacement (seule la semaine est bornée par la spec) ; (3) `GET /programs` et `PATCH /programs/{id}` (ajouts, suppressions, date de début) ; (4) `.ics` : événements sur la journée (les tâches n'ont pas d'heure) ; (5) validation : statut, version acceptée, compétences `en_cours` (D7), reflet de chaque changement de niveau dans l'acquis de la mémoire (D6), jamais à la baisse ; la production des leçons est branchée en 4.10 ; (6) acquis connus = maximum entre `user_skills` et les acquis de la mémoire (ceux de l'Archiviste n'ont pas de ligne `user_skills`).
- [ ] **Step 6: Commit** — `git commit -m "feat(program): programmes, tâches dans le budget, validation, compétences et export .ics"`

---

### Task 4.8 : Back — PDF des leçons et du programme (Gotenberg `convert/html`, gabarits, Markdown sûr) ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI (`GET /programs/{id}/export.pdf`). Risque : sécurité (HTML et Mermaid venus du web jusqu'à Chromium).

**Files:**
- Create: `backend/app/templates/__init__.py`, `backend/app/templates/assets.py`, `backend/app/templates/assets/mermaid.min.js` (version figée), `backend/app/templates/assets/render.js`, `backend/app/templates/lesson/lesson.html.j2`, `lesson.css`, `footer.html`, `backend/app/templates/program/program.html.j2`, `program.css` ; `backend/app/providers/pdf/html.py` (`GotenbergHtmlRenderer`) ; `backend/app/features/lessons/__init__.py`, `service/__init__.py`, `service/markdown.py`, `service/render.py` ; `backend/app/features/program/service/export_pdf.py`
- Modify: `backend/app/providers/pdf/base.py` (`HtmlDocument`, `HtmlPdfRenderer`), `backend/app/core/providers.py` (`PublishingProviders`), `backend/app/bootstrap.py` (`publishing_providers`), `backend/app/main.py` (`create_app(..., publishing_providers=)`), `backend/app/features/program/router.py`, `backend/pyproject.toml` (`uv add markdown-it-py nh3` ; contrat 3 + `app.providers.pdf.html`), `backend/tests/conftest.py` (fixture `publishing_providers`), `backend/tests/support/memory.py` (`FakeHtmlRenderer`), `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/providers/pdf/test_html.py`, `test_html_live.py` ; `backend/tests/features/lessons/test_markdown.py`, `test_render.py` ; `backend/tests/features/program/test_export_pdf.py` ; `backend/tests/templates/test_assets.py`

**Interfaces:**
- Produces:

```python
# pdf/base.py
@dataclass(frozen=True)
class HtmlDocument: index_html: str; assets: Mapping[str, bytes]; footer_html: str | None = None
    wait_for_expression: str | None = None
HTML_RENDER_TIMEOUT_S = 45.0
class HtmlPdfRenderer(Protocol):
    async def html_to_pdf(self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S) -> bytes
# pdf/html.py
class GotenbergHtmlRenderer:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None
#   POST {base}/forms/chromium/convert/html : index.html, footer.html, ressources ; A4 (8,27 × 11,7 in),
#   marges 0,6 in, printBackground, waitForExpression si fourni ; mêmes règles d'erreur que
#   GotenbergRenderer (RenderFailed, corps borné à RENDER_MAX_BYTES, ni HTML ni corps en journal)
# core/providers.py
@dataclass(frozen=True)
class PublishingProviders: html_pdf: HtmlPdfRenderer
# templates/assets.py
MERMAID_VERSION: str; MERMAID_SHA256: str      # la même version majeure que le front
def asset(name: str) -> bytes                  # lecture des fichiers figés de templates/assets/

# lessons/service/markdown.py
ALLOWED_TAGS = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "code", "pre", "blockquote",
                "a", "table", "thead", "tbody", "tr", "th", "td", "hr", "br", "div", "section", "aside", "span"}
@dataclass(frozen=True)
class RenderedMarkdown: html: str; toc: list[tuple[str, str]]; diagrams: int   # (ancre, titre de section)
def markdown_to_html(markdown: str) -> RenderedMarkdown
#   markdown-it-py « commonmark », HTML brut désactivé (échappé), tables ; titres h2 ancrés (slug) ;
#   blocs ```mermaid → <pre class="mermaid"> au texte échappé, filtrés par mermaid_problems (4.4),
#   refusés → <pre class="mermaid-source"> ; puis nh3.clean (ALLOWED_TAGS, attributs href/id/class
#   seulement, schémas http et https, rel « noopener noreferrer ») : ni script, ni style, ni
#   gestionnaire d'événement, ni image, ni iframe
# lessons/service/render.py
async def render_lesson_pdf(renderer: HtmlPdfRenderer, *, title: str, markdown: str, language: str) -> bytes
#   gabarit unique (autoescape Jinja) : sommaire depuis toc, encadrés pour « L'essentiel en 5 lignes »
#   et « Erreurs fréquentes », numéros de page (footer.html), thème clair ; seuls scripts : nos
#   fichiers figés mermaid.min.js et render.js (securityLevel "strict", startOnLoad false ; un
#   schéma en erreur est remplacé par son code ; window.__lessonReady = true à la fin) ;
#   waitForExpression "window.__lessonReady === true" ; RenderFailed → second essai sans script,
#   schémas affichés en code
# program/service/export_pdf.py
async def program_pdf(renderer: HtmlPdfRenderer, program: ProgramOut) -> bytes   # aucun script
GET /programs/{program_id}/export.pdf -> application/pdf (« programme.pdf »)   # 502 render_failed lisible
```

- [ ] **Step 1: Write the failing tests**

```python
def test_markdown_escapes_raw_html():
    out = markdown_to_html("Texte <script>alert(1)</script> <img src=x onerror=alert(1)>")
    assert "<script" not in out.html and "onerror" not in out.html and "<img" not in out.html
def test_javascript_links_are_dropped(): ...           # [x](javascript:alert(1)) → pas de href
def test_mermaid_block_becomes_pre_mermaid(): ...      # ```mermaid flowchart TD … → <pre class="mermaid">
def test_mermaid_directives_are_removed():             # click / %%{init}
    assert 'class="mermaid"' not in markdown_to_html("```mermaid\nflowchart TD\nA-->B\nclick A \"x\"\n```").html
def test_toc_lists_h2_sections(): ...
async def test_lesson_html_has_no_content_script(fake_html_renderer):
    await render_lesson_pdf(fake, title="T", markdown=TRAPPED, language="fr")
    doc = fake.documents[0]
    assert re.findall(r"<script[^>]*>", doc.index_html) == ['<script src="mermaid.min.js">', '<script src="render.js">']
    assert set(doc.assets) == {"lesson.css", "mermaid.min.js", "render.js"} and "pageNumber" in doc.footer_html
async def test_render_failure_retries_without_scripts(): ...
async def test_html_renderer_posts_a4_form(mock_transport): ...   # paperWidth 8.27, paperHeight 11.7, index.html, waitForExpression
async def test_html_renderer_errors_never_cite_body(caplog): ...
def test_mermaid_asset_matches_pinned_hash(): assert sha256(asset("mermaid.min.js")) == MERMAID_SHA256
async def test_program_pdf_route_returns_pdf(client, validated_program): ...   # FakeHtmlRenderer → %PDF
async def test_program_pdf_isolated_between_users(client, app): ...
@pytest.mark.live
async def test_gotenberg_renders_lesson_with_svg_diagram(): ...   # GOTENBERG_URL ; PDF qui contient le texte d'un nœud
```

- [ ] **Step 2: Run** — `uv run pytest tests/providers/pdf tests/features/lessons tests/features/program tests/templates -v` → FAIL.
- [ ] **Step 3: Implement** le fournisseur, les gabarits, le Markdown sûr, le rendu, la route ; télécharger une fois `mermaid.min.js` (même majeure que la dépendance front, `https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js`), noter version et empreinte dans `assets.py` ; composition injectable comme les autres (`create_app(publishing_providers=)`, fixture branchée sur `FakeHtmlRenderer` : aucun test n'atteint Gotenberg) ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; avec Docker : `uv run pytest -m live tests/providers/pdf/test_html_live.py` → PASS (contrôleur).
- [ ] **Step 5: Décision D89** : (1) 17.4 « HTML nettoyé de tout script » appliqué au contenu : HTML brut du Markdown échappé, `nh3` en liste blanche, aucune image ni ressource distante ; (2) les schémas Mermaid deviennent du SVG dans le Chromium de Gotenberg par **nos** fichiers figés (`mermaid.min.js` à empreinte vérifiée, `render.js`), `securityLevel: "strict"`, code filtré par `mermaid_problems` : aucun rendu Mermaid côté serveur n'existe dans la pile et 3.5 exige le SVG ; second essai sans script si le rendu échoue ; (3) `PublishingProviders` injectable ; (4) PDF du programme sans script, rendu à la demande (Gotenberg, quelques secondes : pas un travail d'agent).
- [ ] **Step 6: Commit** — `git commit -m "feat(lessons): PDF A4 par Gotenberg, gabarits leçon et programme, Markdown sûr"`

---

### Task 4.9 : Back — parcours `lesson_factory` (Éclaireur, Rédacteur, Vérificateur)

**Zone : back.** Ne change pas le contrat OpenAPI.

**Files:**
- Create: `backend/app/agents/tools/lesson_port.py` ; `backend/app/agents/prompts/writer.md`, `verifier.md` ; `backend/app/agents/nodes/writer.py`, `backend/app/agents/nodes/verifier/__init__.py`, `verifier/checks.py`, `verifier/verify.py`, `backend/app/agents/nodes/scout/resources.py` ; `backend/app/agents/state/lesson_factory.py` ; `backend/app/agents/graphs/lesson_factory.py` ; `backend/tests/support/lessons.py` (`FakeLessonStore`, `lesson_markdown(words=1500)`)
- Modify: `backend/app/agents/runtime/ports.py` (`lessons`), `backend/app/agents/registry.py` (`writer`, `verifier`), `backend/app/agents/graphs/registry.py`, `backend/app/agents/prompts/scout.md` (mode `resources`)
- Test: `backend/tests/agents/graphs/test_lesson_factory.py`, `backend/tests/agents/nodes/test_lesson_checks.py`

**Interfaces:**
- Produces:

```python
# tools/lesson_port.py
@dataclass(frozen=True)
class ModuleBrief: module_id: str; program_id: str; title: str; skills: tuple[str, ...]
    prerequisites: tuple[str, ...]; week_rank: int; week_theme: str; goal_text: str; language: str
    seed_urls: tuple[str, ...]   # ≤ 5 : pages des praticiens et sources retenues du Conseil liées au module
class ResourcePick(BaseModel): source_id: str; type: ResourceType; duration_minutes: int (1..600)
    level: ResourceLevel; reason: str = Field(min_length=5, max_length=200)
class ResourcePicks(BaseModel): resources: list[ResourcePick] = Field(min_length=3, max_length=6)
@dataclass(frozen=True)
class LessonReport: words: int; unsupported: tuple[str, ...]; problems: tuple[str, ...]; revisions: int
@dataclass(frozen=True)
class PublishedLesson: lesson_id: str; pdf_ok: bool; resources: int
class LessonStore(Protocol):
    async def brief(self, user_id: str, module_id: str) -> ModuleBrief
    async def publish(self, user_id: str, session_id: str, module_id: str, *, markdown: str,
                      resources: Sequence[ResourcePick], report: LessonReport) -> PublishedLesson  # idempotent par module
    async def fail(self, user_id: str, session_id: str, module_id: str, reason: str) -> None
    async def next_module(self, user_id: str, program_id: str, *, exclude_session_id: str) -> str | None
NO_LESSONS: LessonStore

# nodes/verifier/checks.py — contrôles déterministes
SECTIONS = ("Objectifs", "Prérequis", "L'essentiel en 5 lignes", "Explication", "Schémas",
            "Exemple travaillé", "Erreurs fréquentes", "Exercice", "Corrigé de l'exercice",
            "Sources", "Auto-évaluation")
MIN_WORDS = 1200; MAX_WORDS = 2500; MAX_QUOTE_WORDS = 25
@dataclass(frozen=True)
class LessonCheck: words: int; problems: list[str]
def check_lesson(markdown: str, *, title: str, sources: Sequence[tuple[int, str, str]]) -> LessonCheck
#   sources : (numéro, adresse, texte lu) ; problèmes en français : titre « # {titre} » absent ;
#   sections « ## … » manquantes ou dans le désordre ; plus de 3 objectifs ; « L'essentiel » ≠ 5
#   puces ; auto-évaluation ≠ 5 questions ; aucun bloc ```mermaid ; mots hors 1 200–2 500 (blocs de
#   code exclus) ; lien absent des sources lues ; marqueur [n] inconnu ; passage de plus de 25 mots
#   recopié d'une source hors citation « … » suivie de [n]
# nodes/verifier/verify.py
class FactReport(BaseModel): unsupported: list[str] = Field(default_factory=list, max_length=20)
def make_verify(deps) -> Node     # check_lesson + structured_call FactReport (leçon et sources encadrées)
MAX_REVISIONS = 2
# nodes/writer.py
def make_write(deps) -> Node      # invoke_agent (niveau fort) ; révision : problèmes et affirmations non sourcées
# nodes/scout/resources.py
def make_pick_resources(deps) -> Node
#   candidates = verdicts « kept » de la session ; ≥ 3 → structured_call ResourcePicks, ids hors
#   candidates retirés ; < 3 → toutes les retenues, problème « ressources insuffisantes » au rapport
# graphs/lesson_factory.py
class LessonFactoryInput(BaseModel): program_id: str (36); module_id: str (36)
# START → brief → plan → search → read → judge → remember → pick_resources → write → verify →
#   route : problèmes et revisions < 2 → write ; problèmes restants → fail_lesson ; sinon publish
#   publish / fail_lesson → next → END   (`next` : next_module, la chaîne continue même après un échec)
```

- `brief` pose `query` = titre du module, compétences, thème de la semaine (300 caractères au plus) et `urls` = `seed_urls` : les nœuds de l'Éclaireur de la phase 3 tournent tels quels, avec leurs plafonds de session (12 requêtes, 30 pages) pour ce seul module.
- Le Rédacteur reçoit les sources retenues numérotées (titre, adresse, texte lu ≤ 6 000 caractères, tous encadrés par `untrusted()`), la structure exacte, 1 200 à 2 500 mots, en `language` (termes techniques en anglais), citations courtes entre « » suivies de `[n]`.
- Agents : `writer` (`fort`), `verifier` (`standard`).

- [ ] **Step 1: Write the failing tests**

```python
def test_check_lesson_accepts_a_valid_lesson(): assert check_lesson(lesson_markdown(1500), ...).problems == []
@pytest.mark.parametrize("mutation,problem", [("drop:Corrigé de l'exercice", "Section manquante"),
    ("objectives:4", "3 objectifs au plus"), ("words:900", "1 200"), ("words:2600", "2 500"),
    ("link:https://inconnu.example", "lien"), ("copy:40", "recopié"), ("no_mermaid", "schéma")])
def test_check_lesson_reports(mutation, problem): ...
async def test_lesson_factory_publishes_lesson_with_three_to_six_resources(make_lesson_runner):
    pub = c.store.published[0]; assert 3 <= len(pub.resources) <= 6 and pub.report.unsupported == ()
async def test_resources_come_only_from_kept_sources(...): ...   # source_id inventé retiré
async def test_unsupported_claim_triggers_revision(...):
    assert c.writer_calls == 2 and "Affirmation non sourcée" in c.prompt_of_writer(2)
async def test_still_failing_after_two_revisions_marks_lesson_failed(...): ...
async def test_writer_prompt_frames_sources_as_untrusted(...): ...
async def test_chain_continues_with_next_module(...): assert c.store.next_calls == [("prog", sid)]
async def test_replay_publishes_once(...): ...                     # arrêt dans publish, reprise
```

- [ ] **Step 2: Run** — `uv run pytest tests/agents -v` → FAIL.
- [ ] **Step 3: Implement** port, contrôles, nœuds, prompts, graphe, registres.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D90** : (1) une session `lesson_factory` par module (plafonds 12/30 pour ce module), sujet `program` ; (2) recherche du module par les nœuds de l'Éclaireur tels quels, graines = praticiens et sources du Conseil ; ressources prises parmi les sources notées ≥ 60, 3 à 6, moins si le web n'en donne pas (signalé, jamais inventé) ; (3) « chaque lien répond » = chaque lien de la leçon est une page lue `ok` dans la session ; « rien n'est recopié » = aucun passage de plus de 25 mots identique à une source hors citation attribuée ; (4) deux révisions au plus, puis leçon en échec (relancée par 4.10) ; (5) structure exacte en 11 sections (« Corrigé de l'exercice » séparé).
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): Rédacteur, Vérificateur et parcours lesson_factory"`

---

### Task 4.10 : Back — feature `lessons` : leçons, ressources, production en chaîne et tâche « J-7 » ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI. Risque : concurrence (validation, tâche planifiée et fin de leçon qui lancent la production), lecture sans `user_id` au démarrage d'une tâche.

**Files:**
- Create: `backend/app/features/lessons/schemas.py`, `router.py`, `repository/__init__.py`, `repository/lessons.py`, `repository/resources.py`, `service/lessons.py`, `service/resources.py`, `service/production.py`, `service/store.py` (`AgentLessonStore`), `service/runtime.py` ; `backend/app/scheduler/__init__.py`, `base.py`, `registry.py`, `runner.py`, `jobs/__init__.py`, `jobs/lessons_due.py` ; `backend/app/features/research/service/download.py`
- Modify: `backend/app/features/program/service/validation.py` (semaines 1 et 2), `backend/app/features/registry.py`, `backend/app/bootstrap.py` (`lessons`, `scheduler_context`), `backend/app/main.py` (planificateur dans la pile, après le moteur), `backend/app/core/providers.py` (`ResearchProviders.fetcher: WebFetcher`), `backend/tests/support/research.py`, `backend/pyproject.toml` (`uv add apscheduler` ; contrat 8 ; `app.scheduler` dans les sources des contrats 3 et 5), `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/features/lessons/test_router.py`, `test_production.py`, `test_store.py`, `backend/tests/features/research/test_download.py`, `backend/tests/scheduler/test_runner.py`, `test_lessons_due.py`

**Interfaces:**
- Consumes: `LessonStore` (4.9), `render_lesson_pdf` (4.8), `SessionLauncher` (4.1), `validate_program` (4.7), `record_verdict` / `list_sources` (phase 3).
- Produces:

```python
# schemas.py
class ResourceOut(BaseModel): id; module_id; program_id; type: ResourceType; title; url; author; date: str | None
    lang; duration_minutes; level: ResourceLevel | None; reason; score: int | None; status: ResourceStatus
    has_local_copy: bool; note: str | None
class LessonSummaryOut(BaseModel): id; module_id; week_rank; title; status: LessonStatus; word_count; pdf_available: bool
class LessonOut(LessonSummaryOut): program_id; markdown: str; failure_reason: str | None; resources: list[ResourceOut]
class ResourcePatch(BaseModel): status: ResourceStatus
GET   /programs/{program_id}/lessons -> list[LessonSummaryOut]   # hors 14.2
GET   /lessons/{lesson_id} -> LessonOut
GET   /lessons/{lesson_id}/pdf -> application/pdf               # 404 `lesson_pdf_missing` tant qu'absent
GET   /resources?program_id=&type=&lang=&status= -> list[ResourceOut]
PATCH /resources/{resource_id} -> ResourceOut
GET   /resources/{resource_id}/file -> application/pdf          # hors 14.2 : copie locale

# research/service/download.py
async def download_pdf(runtime: ResearchRuntime, user_id: str, url: str) -> bytes | None
#   domaine exclu → None ; providers.fetcher.fetch(url, content_types=("application/pdf",)) sous la garde
#   SSRF ; ≤ 20 Mo ; toute erreur → None (journal : identifiants et code seulement)

# service/production.py
MAX_ATTEMPTS = 3; HORIZON_DAYS = 7; FIRST_WEEKS = (1, 2)
async def ensure_lessons(ctx: ProductionContext, user_id: str, program_id: str, *,
                         exclude_session_id: str | None = None, today: date | None = None) -> str | None
#   sous lessons_lock(user_id, program_id) : programme validé seulement ; modules dus = semaines 1 et 2,
#   ou semaine qui commence au plus tard today + 7 (UTC), non sautés, sans leçon `ready`, essais < 3 ;
#   une session lesson_factory ouverte pour le programme (find_active_session, sujet program, hors
#   exclude_session_id) → rien ; sinon lancement pour le premier module dû (leçon `generating`,
#   attempts + 1) ; rend l'id de session lancée
# service/store.py — AgentLessonStore(session_factory, publishing, storage, research, memory, launcher)
#   publish : leçon `ready` (Markdown, mots, rapport), ressources (upsert par url_hash, métadonnées de
#   la ligne `sources`), copie locale des PDF libres (download_pdf → storage catégorie `resources`),
#   sinon note = résumé de la source (fiche de lecture) ; PDF de la leçon (render_lesson_pdf →
#   storage `lessons`) ; mémoire `lecon` (titre, Markdown, étiquette du programme) ;
#   artifact.ready {kind "lesson", url "/apprendre/lecons/{id}"} émis par le nœud
#   next_module : ensure_lessons(exclude_session_id=…)
# scheduler/base.py
@dataclass(frozen=True)
class JobSpec: name: str; every: timedelta; run: Callable[[JobContext], Awaitable[None]]; at_startup: bool = True
@dataclass(frozen=True)
class JobContext: session_factory: async_sessionmaker[AsyncSession]; launcher: SessionLauncher
    production: ProductionContext
# scheduler/registry.py
JOBS: list[JobSpec] = [JobSpec("lessons_due", timedelta(hours=6), lessons_due.run)]
# scheduler/runner.py
@asynccontextmanager
async def open_scheduler(jobs: Sequence[JobSpec], context: JobContext) -> AsyncIterator[None]
#   APScheduler dans la boucle du back ; une instance par tâche à la fois, retard rattrapé une fois ;
#   une exception de tâche est journalisée par type, jamais propagée ; arrêt sans attendre à la sortie
# scheduler/jobs/lessons_due.py
async def run(ctx: JobContext) -> None
#   programmes validés de tous les utilisateurs (list_programs_due, SEULE lecture sans user_id de la
#   phase, identifiants seulement) → ensure_lessons pour chacun
```

- `validate_program` (4.7) appelle `ensure_lessons` après la validation (semaines 1 et 2 tout de suite).
- Contrat import-linter 8 : `app.features` et `app.agents` n'importent jamais `app.scheduler` ; `app.scheduler` entre dans les sources des contrats 3 (fournisseurs concrets) et 5 (`app.bootstrap`).

- [ ] **Step 1: Write the failing tests**

```python
async def test_validation_starts_lessons_for_weeks_one_and_two(db, launcher, validated):
    assert launcher.started == [("lesson_factory", {"program_id": pid, "module_id": first_module_w1})]
async def test_chain_runs_one_module_at_a_time(...): ...           # session ouverte → ensure_lessons ne lance rien
async def test_next_module_excludes_current_session(...): ...
async def test_week_three_waits_until_seven_days_before(...):
    assert await ensure_lessons(ctx, uid, pid, today=start + timedelta(days=13)) is None    # semaine 3 = start+14
    assert await ensure_lessons(ctx, uid, pid, today=start + timedelta(days=7))             # dans 7 jours
async def test_failed_lesson_is_retried_at_most_three_times(...): ...
async def test_scheduler_and_validation_start_one_chain(...):
    await asyncio.gather(lessons_due.run(job_ctx), validate(...), store.next_module(...))
    assert await count_open_sessions("lesson_factory") == 1
async def test_scheduler_runs_jobs_at_startup_and_survives_errors(caplog): ...
async def test_publish_saves_lesson_pdf_resources_and_memory(db, publishing, ...):
    assert lesson.status == "ready" and lesson.pdf_key and len(resources) == 4 and memory_kinds() == ["lecon"]
async def test_free_pdf_is_stored_locally_otherwise_reading_note(...): ...
async def test_download_refuses_private_address_and_non_pdf(...): ...
async def test_lesson_routes_and_isolation(client, app): ...
async def test_resources_filters(client, ...): ...                 # programme, type, langue, statut
async def test_resource_status_patch(client, ...): ...
async def test_lesson_pdf_missing_is_404(client, ...): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/features/lessons tests/features/research tests/scheduler tests/features/program -v` → FAIL.
- [ ] **Step 3: Implement** feature, production, `AgentLessonStore`, téléchargement, planificateur (version d'APScheduler vérifiée), contrats d'import ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; 5 passages de `-k "one_chain"`.
- [ ] **Step 5: Décision D91** : (1) production en chaîne, un module à la fois par programme (pas de rafale d'appels LLM), relancée par la fin de chaque leçon, par la validation et par la tâche planifiée ; (2) « J-7 » : semaine dont le début ≤ aujourd'hui (UTC) + 7 jours ; tâche toutes les 6 h et au démarrage, sans table `jobs` (phase 8) : l'état des leçons suffit à l'idempotence ; (3) `list_programs_due` : lecture sans `user_id` réservée au planificateur (comme D18, D75), identifiants seulement ; (4) 3 essais par leçon ; (5) copie locale si l'adresse rend un PDF de 20 Mo au plus sous la garde SSRF, sinon fiche de lecture ; (6) routes hors 14.2 : `GET /programs/{id}/lessons`, `GET /resources/{id}/file` ; contrat d'import 8.
- [ ] **Step 6: Commit** — `git commit -m "feat(lessons): leçons et ressources, production en chaîne, tâche planifiée J-7"`

---

### Task 4.11 : Front — tableau Excalidraw (`Board`) dans `shared/session-ui`

**Zone : front.** Présentationnel, types de vue locaux : n'importe ni `schema.d.ts` ni `shared/api`.

**Files:**
- Create: `frontend/src/shared/session-ui/Board/Board.tsx`, `Board.test.tsx`, `index.ts`, `BoardCanvas.tsx` (chargé paresseusement), `BoardToolbar.tsx`, `BoardStateList.tsx`, `boardScene.ts` (+ test), `reveal.ts` (+ test), `annotationNote.ts` (+ test), `exportBoard.ts` ; `frontend/src/shared/session-ui/MermaidSvg/MermaidSvg.tsx`, `MermaidSvg.test.tsx`, `index.ts` ; `frontend/src/shared/session-ui/boardTypes.ts`
- Modify: `frontend/package.json` (`pnpm add @excalidraw/excalidraw @excalidraw/mermaid-to-excalidraw mermaid`), `frontend/src/shared/session-ui/index.ts`, `frontend/src/shared/i18n/messages/session.ts`, `frontend/vite.config.ts` (polices d'Excalidraw servies en local si la doc l'exige)

**Interfaces:**
- Produces:

```ts
// boardTypes.ts
export type BoardKind = "domain_map" | "prerequisites" | "timeline" | "comparison";
export interface BoardStateView { id: string; kind: BoardKind; title: string; step: number; mermaid: string;
  scene: Record<string, unknown> | null; author: "scribe" | "user"; createdAt: string }
export interface BoardEdit { scene: Record<string, unknown>; note: string }
// Board({ states, activeId, onSelect, onSendEdit, sending, readOnly = false })
//   liste des états (titre, type, auteur), canevas, barre : « Exporter en PNG », « Exporter en SVG »,
//   « Exporter (.excalidraw) », « Envoyer mes modifications aux agents » (actif après une modification)
// reveal.ts
export const REVEAL_STEP_MS = 200;
export function revealDelays(count: number, opts: { stepMs?: number; reducedMotion: boolean }): number[]
//   délais cumulés, pas borné à [150, 300] ; reducedMotion → tout à 0
// boardScene.ts
export type SceneResult = { ok: true; elements: unknown[]; files: unknown } | { ok: false; error: string };
export async function mermaidToScene(mermaid: string): Promise<SceneResult>   // parseMermaidToExcalidraw puis convertToExcalidrawElements
// annotationNote.ts
export function annotationNote(before: readonly SceneElementLike[], after: readonly SceneElementLike[]): string
//   « Ajouté : « Docker » ; Modifié : « MLOps » ; 2 élément(s) déplacé(s) » ; rien → ""
// MermaidSvg({ code, title }) : mermaid.initialize({ startOnLoad: false, securityLevel: "strict" }) puis
//   render ; erreur → code affiché en <pre> ; réutilisé par le lecteur de leçons (4.13)
```

- Repli (3.3) : `mermaidToScene` en échec → `MermaidSvg` + `console.error("board_fallback", { boardId })` (identifiant seulement, jamais le code). Ordre d'apparition = ordre des éléments rendus par le convertisseur (ordre d'écriture du Mermaid). Un état `user` avec `scene` s'affiche tel quel, sans animation.

- [ ] **Step 1: Write the failing tests** (`vi.mock("@excalidraw/excalidraw")`, `vi.mock("@excalidraw/mermaid-to-excalidraw")`, `vi.mock("mermaid")`)

```ts
it("revealDelays spaces elements by 200 ms and clamps to 150–300", () => {
  expect(revealDelays(3, { reducedMotion: false })).toEqual([0, 200, 400]);
  expect(revealDelays(2, { stepMs: 500, reducedMotion: false })).toEqual([0, 300]);
  expect(revealDelays(3, { reducedMotion: true })).toEqual([0, 0, 0]);
});
it("Board reveals scribe elements one by one", async () => { /* faux timers : 1 élément, puis 2 après 200 ms */ });
it("renders the fallback with strict security when conversion fails", async () => {
  expect(mermaid.initialize).toHaveBeenCalledWith(expect.objectContaining({ securityLevel: "strict" }));
  expect(console.error).toHaveBeenCalledWith("board_fallback", { boardId: "b1" });
});
it("annotationNote lists added and changed texts", () => { expect(annotationNote(a, b)).toBe("Ajouté : « Docker » ; 1 élément(s) déplacé(s)"); });
it("sends edits with the computed note", async () => { expect(onSendEdit).toHaveBeenCalledWith("b1", { scene: expect.any(Object), note: "Ajouté : « Docker »" }); });
it("exports PNG, SVG and .excalidraw", async () => { /* exportToBlob, exportToSvg, serializeAsJSON appelés */ });
it("keyboard: state list and toolbar are reachable and labelled", () => { /* rôles et noms accessibles */ });
```

- [ ] **Step 2: Run** — `cd frontend && pnpm vitest run src/shared/session-ui` → FAIL.
- [ ] **Step 3: Implement** composants et utilitaires (canevas chargé par `React.lazy`, hors du paquet principal).
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 5: Décision D92** (dans le rapport) : `Board` dans `shared/session-ui` (D9, Tuteur en phase 5) ; 200 ms entre éléments ; modifications envoyées sur demande (bouton) avec une note calculée, pas à chaque geste ; repli journalisé par identifiant ; Excalidraw chargé à la demande ; polices locales si la doc le permet.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): tableau Excalidraw animé avec repli Mermaid"`

---

### Task 4.12 : Front — composants du Conseil et ajouts de session partagés

**Zone : front.** Après 4.1 (contrat : `fields`, `command`, `kind` des sources, citations). Composants de feature présentationnels.

**Files:**
- Create: `frontend/src/shared/session-ui/CitationChips/` (composant, test, `index.ts`), `frontend/src/shared/session-ui/InterruptCard/InterruptFields.tsx` ; `frontend/src/features/learning/components/CouncilStageBar/`, `DebateCommandBar/`, `ProposalCards/`, `CouncilTabs/` (un dossier chacun, avec test et `index.ts`), `frontend/src/features/learning/components/viewTypes.ts` ; `frontend/src/shared/i18n/messages/learning.ts`
- Modify: `frontend/src/shared/session-ui/AgentBubble/AgentBubble.tsx` (+ test), `DebateFeed/DebateFeed.tsx`, `UserMessageBubble/UserMessageBubble.tsx` (+ test), `InterruptCard/InterruptCard.tsx` (+ test), `SourcesPanel/` (bloc « Praticiens repérés »), `sourceTypes.ts`, `sourcesFromEvents.ts` (+ test), `index.ts` ; `frontend/src/shared/realtime/sessionApi.ts` (`postCommand`), `useSessionActions.ts` (+ test), `eventHandlers.ts`, `types.ts` ; `frontend/src/shared/i18n/messages/session.ts`, `frontend/src/shared/i18n/fr.ts`

**Interfaces:**
- Produces:

```ts
// shared/realtime
export type UserCommand = components["schemas"]["UserMessagePayload"]["command"];
export async function postCommand(sessionId: string, command: NonNullable<UserCommand>): Promise<void>
// SessionActions.sendCommand(command): Promise<boolean> ; InterruptCard.onAnswer(value: unknown)
// FeedItem « user » : { kind: "user"; seq; text; command: UserCommand | null } ; AgentTurn.citations: Citation[]
// shared/session-ui
// CitationChips({ citations }) — pastilles « 1 », « 2 » : URL → lien (_blank, noopener noreferrer) ;
//   élément de mémoire → lien « /memoire?item={id} » ; nom accessible « Source 1 : {titre} »
// InterruptCard : `fields` non vide → un champ par question (étiquette = question) + boutons d'option ;
//   valeur envoyée { answers: { q1: "…" } } (champs vides omis) ou la valeur de l'option
// SourceView gagne kind: "page" | "person" et role: string | null ; SourcesViewModel gagne people: SourceView[]
// features/learning/components/viewTypes.ts
export type CouncilStage = "framing" | "research" | "debate" | "proposals" | "program";
export interface ProposalView { id: string; rank: number; name: string; promise: string; durationWeeks: number;
  weeklyHours: number; skills: string[]; finalProject: string; tradeoffs: string[]; boardId: string | null; chosen: boolean }
// CouncilStageBar({ stage, round, rounds }) — Cadrage, Recherche, Débat, Propositions, Programme ;
//   étape courante aria-current="step" ; « Tour 2 / 3 » pendant le débat
// DebateCommandBar({ disabled, onCommand }) — Relancer un tour (another_round), Passer aux
//   propositions (to_proposals), Plus concret (more_concrete), Plus court (shorter)
// ProposalCards({ proposals, canChoose, busy, onChoose, onMix, onAnotherRound, onShowBoard })
//   cartes côte à côte, mêmes rubriques alignées ; « Choisir » ; « Mélanger » : cocher deux cartes
//   puis « Mélanger ces deux parcours » ; « Demander un autre tour » ; « Voir au tableau »
// CouncilTabs({ active, onChange, board, sources, proposals }) — onglets ARIA Tableau, Sources, Propositions
```

- [ ] **Step 1: Write the failing tests**

```ts
it("AgentBubble shows numbered citations that open the source", () => {
  render(<AgentBubble ... citations={[{ index: 1, title: "Doc", url: "https://a.org", memory_item_id: null }]} />);
  expect(screen.getByRole("link", { name: "Source 1 : Doc" })).toHaveAttribute("rel", "noopener noreferrer");
});
it("InterruptCard with fields sends answers", async () => { expect(onAnswer).toHaveBeenCalledWith({ answers: { q1: "Startup" } }); });
it("UserMessageBubble shows a command label", () => { expect(screen.getByText("Commande : Plus court")).toBeInTheDocument(); });
it("sourcesFromEvents puts people apart", () => { expect(model.people[0].title).toBe("Ada Lovelace"); });
it("useSessionActions.sendCommand posts the command", async () => { /* MSW : corps { text: "", command: "shorter" } */ });
it("CouncilStageBar marks the current stage", () => { expect(screen.getByText("Débat")).toHaveAttribute("aria-current", "step"); });
it("DebateCommandBar sends to_proposals", async () => { expect(onCommand).toHaveBeenCalledWith("to_proposals"); });
it("ProposalCards mixes exactly two proposals", async () => { expect(onMix).toHaveBeenCalledWith("p1", "p2"); });
it("ProposalCards disables actions when canChoose is false", () => { ... });
it("CouncilTabs supports arrow-key navigation", async () => { ... });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/shared src/features/learning` → FAIL.
- [ ] **Step 3: Implement** ajouts partagés, composants, textes (`learning.*`, `session.*`).
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck` → PASS (la démo et l'essai de recherche inchangés).
- [ ] **Step 5: Décision D93** (dans le rapport) : citations en pastilles dans `AgentBubble` ; questions à champs gérées par `InterruptCard` (réutilisable par le Comité) ; commandes par `postCommand` dans `shared/realtime` ; praticiens dans `SourcesPanel`.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): composants du Conseil, citations, questions à champs et commandes"`

---

### Task 4.13 : Front — composants du programme et lecteur de leçon

**Zone : front.** Présentationnel, types de vue locaux : n'importe ni `schema.d.ts` ni `shared/api`.

**Files:**
- Create (un dossier par composant, avec test et `index.ts`) : `frontend/src/features/program/components/WeekCalendar/` (dont `DayColumn.tsx`, `TaskCard.tsx`, `MoveMenu.tsx`), `TaskList/`, `PlanDiff/`, `ProgressOverview/`, `WeekHeader/`, `frontend/src/features/program/components/viewTypes.ts` ; `frontend/src/features/lessons/components/LessonReader/` (dont `LessonToc.tsx`, `ReadingProgress.tsx`), `frontend/src/features/lessons/components/viewTypes.ts` ; `frontend/src/shared/i18n/messages/program.ts`, `lessons.ts`
- Modify: `frontend/package.json` (`pnpm add @dnd-kit/core react-markdown remark-gfm`), `frontend/src/shared/i18n/fr.ts`

**Interfaces:**
- Produces:

```ts
// program/components/viewTypes.ts
export type TaskType = "lire" | "regarder" | "pratiquer" | "quiz" | "projet";
export interface TaskView { id: string; moduleTitle: string; title: string; type: TaskType; minutes: number;
  doneCriterion: string; plannedDate: string; done: boolean; alreadyKnown: boolean }
export interface DayView { date: string; capacityMinutes: number; tasks: TaskView[] }
export interface WeekView { rank: number; theme: string; objective: string; deliverable: string; startDate: string;
  loadMinutes: number; capMinutes: number; days: DayView[] }
// WeekCalendar({ week, editable, onMoveTask }) — 7 colonnes ; glisser-déposer (dnd-kit, souris et
//   clavier, annonces en français) ; « Déplacer vers… » (menu des jours) sur chaque carte ;
//   charge du jour / capacité, jour au-delà signalé (texte, pas seulement la couleur) ;
//   onMoveTask(taskId, date) ; « déjà acquis » en étiquette
// WeekHeader({ week }) — thème, objectif, livrable, « 11 h 30 / 11 h 54 (85 %) »
// TaskList({ weeks, editable, onToggleDone, onDelete, onAdd }) — liste complète par semaine et module ;
//   formulaire d'ajout (titre, type, durée 15–120, critère, jour), erreurs en ligne
// PlanDiff({ diff }) — Ajoutées, Retirées, Déplacées (« lun. 16 nov. → mer. 18 nov. »)
// ProgressOverview({ progress, weeks }) — tâches et heures faites / prévues, une barre par semaine
// lessons/components
export interface LessonView { title: string; markdown: string; wordCount: number; pdfUrl: string | null }
// LessonReader({ lesson }) — react-markdown + remark-gfm, HTML brut ignoré (skipHtml), liens http(s)
//   seulement (urlTransform), blocs mermaid → MermaidSvg (4.11) ; sommaire des sections, progression
//   de lecture, colonne 72 caractères, corps 18 px ; « Télécharger le PDF » si pdfUrl
```

- [ ] **Step 1: Write the failing tests**

```ts
it("WeekCalendar moves a task with the keyboard menu", async () => {
  await user.click(screen.getByRole("button", { name: "Déplacer « Lire le chapitre 1 »" }));
  await user.click(screen.getByRole("menuitem", { name: /mercredi 18 novembre/ }));
  expect(onMoveTask).toHaveBeenCalledWith("t1", "2026-11-18");
});
it("WeekCalendar flags a day over its capacity in text", () => { expect(screen.getByText("Jour chargé : 150 / 120 min")).toBeInTheDocument(); });
it("WeekCalendar is read-only when not editable", () => { ... });
it("WeekHeader shows the load against 85 %", () => { expect(screen.getByText(/11 h 54/)).toBeInTheDocument(); });
it("TaskList refuses a duration outside 15–120", async () => { ... });
it("PlanDiff lists moved tasks with both dates", () => { ... });
it("ProgressOverview shows done over planned hours", () => { ... });
it("LessonReader ignores raw HTML and javascript links", () => {
  render(<LessonReader lesson={{ ...l, markdown: "<script>x</script> [a](javascript:alert(1))" }} />);
  expect(document.querySelector("script")).toBeNull(); expect(screen.queryByRole("link", { name: "a" })).toBeNull();
});
it("LessonReader builds a table of contents from sections", () => { ... });
it("LessonReader renders mermaid blocks through MermaidSvg", () => { ... });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/features/program src/features/lessons` → FAIL.
- [ ] **Step 3: Implement** composants et textes.
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck` → PASS.
- [ ] **Step 5: Décision D94** (dans le rapport) : dnd-kit (clavier) plus un menu « Déplacer vers… » ; dépassement de jour signalé sans blocage (seule la semaine est bornée, D88) ; Markdown rendu sans HTML brut, Mermaid par `MermaidSvg` strict.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): calendrier, liste, diff, avancement et lecteur de leçon"`

---

### Task 4.14 : Front — écrans Objectifs et Conseil (feature `learning`)

**Zone : front.** Après 4.6 (contrat). N'utilise aucun type ajouté par 4.7.

**Files:**
- Create: `frontend/src/features/learning/manifest.ts` (+ test), `api.ts`, `queryKeys.ts`, `hooks/useGoals.ts`, `useGoal.ts`, `useProposals.ts`, `useBoards.ts`, `useChooseProposal.ts`, `useBoardEdit.ts` (+ tests), `councilStage.ts` (+ test), `boardsFromEvents.ts` (+ test), `toView.ts` (+ test), `components/GoalForm/`, `components/GoalList/` (avec tests), `pages/GoalsPage/`, `pages/CouncilPage/` (page, `CouncilLayout.tsx`, `CouncilFeed.tsx`, `CouncilSide.tsx`, test, `index.ts`), `pages/CouncilIndexPage/`
- Modify: `frontend/src/app/registry.ts` (ligne `learningManifest`), `frontend/src/shared/i18n/messages/learning.ts`

**Interfaces:**
- Consumes: composants de 4.11 et 4.12 ; routes de 4.6.
- Produces:

```ts
// manifest.ts
export const learningManifest: FeatureManifest = { id: "learning",
  routes: [{ path: "apprendre/objectifs", Component: GoalsPage },
           { path: "apprendre/objectifs/:goalId/conseil", Component: CouncilPage },
           { path: "apprendre/conseil", Component: CouncilIndexPage }],
  nav: [{ section: "learn", labelKey: "learning.nav.goals", path: "/apprendre/objectifs", order: 1 },
        { section: "learn", labelKey: "learning.nav.council", path: "/apprendre/conseil", order: 2 }] };
// councilStage.ts
export function councilStage(events: SessionEvent[], hasProgram: boolean): { stage: CouncilStage; round: number; rounds: number }
//   interruption framing → framing ; tool web_* / source.found → research ; agent.message « tour-n » →
//   debate ; proposal.ready ou interruption choose_path → proposals ; programme connu → program
// boardsFromEvents.ts
export function boardsFromEvents(saved: BoardStateView[], events: SessionEvent[]): BoardStateView[]
//   états de GET /goals/{id}/boards puis board.update du direct (par board_id, sans doublon)
```

- `GoalsPage` : `GoalForm` (texte 5–500, poste visé, échéance future, heures par semaine 1–40) → `POST /goals` → navigation vers le Conseil ; `GoalList` (statut, lien Conseil, lien Programme).
- `CouncilPage` (15.2) : barre d'état en haut (`CouncilStageBar`, `CostBadge`) ; colonne gauche 40 % (`DebateFeed` avec `InterruptCard`, `MessageComposer` actif pendant tout le débat, `DebateCommandBar`, `SessionControls`) ; zone droite 60 % (`CouncilTabs` : `Board` + `useBoardEdit`, `SourcesPanel`, `ProposalCards` rechargées sur `proposal.ready`) ; « Choisir » / « Mélanger » → `POST /proposals/{id}/choose` ; « Demander un autre tour » → reprise `another_round` ; Conseil terminé → étape Programme, suivi de `program_session_id` et lien « Voir le programme » dès `artifact.ready` kind `program`. Reprise après rechargement par `council_session_id`.
- `CouncilIndexPage` : redirige vers le Conseil de l'objectif le plus récent, sinon état vide « Saisis un objectif » avec lien.

- [ ] **Step 1: Write the failing tests** (MSW, `queryWrapper`, faux socket, `vi.mock` du canevas)

```ts
it("GoalsPage creates a goal and opens its council", async () => { expect(await screen.findByRole("heading", { name: /Conseil/ })).toBeInTheDocument(); });
it("CouncilPage answers framing questions", async () => { /* interruption framing → POST resume { answers } */ });
it("CouncilPage streams four agents and the board", async () => {
  // faux socket : agent.message × 4 (tour-1), board.update domain_map, source.found × 8
  expect(screen.getAllByRole("article")).toHaveLength(4); expect(screen.getByRole("tab", { name: "Tableau" })).toBeInTheDocument();
});
it("CouncilPage keeps the composer active during the debate and sends commands", async () => { ... });
it("CouncilPage chooses a proposal", async () => { /* POST /proposals/p1/choose */ });
it("CouncilPage sends board edits to the agents", async () => { /* POST /boards/b1/edits */ });
it("CouncilPage shows the program link once the program is ready", async () => { ... });
it("councilStage follows the session", () => { expect(councilStage(evts, false)).toEqual({ stage: "debate", round: 2, rounds: 3 }); });
it("declares Objectifs and Conseil under Apprendre", () => { expect(learningManifest.nav?.map((n) => n.path)).toEqual(["/apprendre/objectifs", "/apprendre/conseil"]); });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/features/learning src/app` → FAIL.
- [ ] **Step 3: Implement** api, hooks, conversions, pages, manifeste, ligne du registre.
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 5: Décision D95** (dans le rapport) : routes `/apprendre/objectifs`, `/apprendre/objectifs/:goalId/conseil`, `/apprendre/conseil` ; étape déduite des événements ; choix par `choose`, autre tour par reprise ; Conseil suivi jusqu'au lancement du programme.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): écrans Objectifs et Conseil"`

---

### Task 4.15 : Front — écrans Programme, Leçons et Bibliothèque (features `program` et `lessons`)

**Zone : front.** Après 4.7, 4.8 et 4.10 (contrat).

**Files:**
- Create: `frontend/src/features/program/manifest.ts` (+ test), `api.ts`, `queryKeys.ts`, `toView.ts` (+ test), `hooks/usePrograms.ts`, `useProgram.ts`, `useTaskMutations.ts`, `useValidateProgram.ts` (+ tests), `pages/ProgramPage/` (page, `ProgramViews.tsx`, `ValidationBar.tsx`, test, `index.ts`), `pages/ProgramIndexPage/` ; `frontend/src/features/lessons/manifest.ts` (+ test), `api.ts`, `queryKeys.ts`, `toView.ts`, `hooks/useLesson.ts`, `useProgramLessons.ts`, `useResources.ts` (+ tests), `components/ResourceList/`, `components/LibraryFilters/` (avec tests), `pages/LessonsPage/`, `pages/LessonPage/`, `pages/LibraryPage/`
- Modify: `frontend/src/app/registry.ts` (lignes `programManifest`, `lessonsManifest`), `frontend/src/shared/i18n/messages/program.ts`, `lessons.ts`

**Interfaces:**
- Produces:

```ts
// program/manifest.ts — routes « apprendre/programme » (ProgramIndexPage : le plus récent),
//   « apprendre/programme/:programId » ; nav learn « Programme » order 3
// lessons/manifest.ts — « apprendre/lecons » (LessonsPage), « apprendre/lecons/:lessonId » (LessonPage),
//   « apprendre/bibliotheque » (LibraryPage) ; nav learn « Leçons » order 4, « Bibliothèque » order 5
// program/toView.ts
export function toWeekViews(program: ProgramOut, budget: { weekday: number; weekend: number }): WeekView[]
//   jours lun.–dim., capacité = weekday, samedi = weekend, dimanche 0 ; tâches par planned_date
// ResourceList({ resources, onToggleStatus }) — type, langue, durée, niveau, auteur, date, raison ;
//   lien (nouvel onglet) et « Copie locale (PDF) » si présente ; « Lue » / « À lire »
// LibraryFilters({ value, programs, onChange }) — programme, type, langue, statut
```

- `ProgramPage` : trois vues (Semaine : `WeekHeader` + `WeekCalendar` avec choix de la semaine ; Liste : `TaskList` ; Avancement : `ProgressOverview`), `PlanDiff` quand une révision existe ; brouillon et session `program_builder` en attente → `ValidationBar` : « Valider le programme » (`POST /programs/{id}/validate`) et « Demander une révision » (note, reprise `revise`) ; refus 422 (85 %, quiz, pratique) en erreur en ligne, calendrier remis à l'état du serveur ; exports « PDF » et « Calendrier (.ics) » ; leçons du module (statut, lien) dans la liste.
- `LessonPage` : `LessonReader`, `ResourceList`, PDF ; leçon `pending` / `generating` → « Leçon en préparation » ; `failed` → raison et prochaine tentative automatique.
- `LibraryPage` : `LibraryFilters` + `ResourceList`, état vide avec lien vers le programme.
- Hors périmètre : « Demander au tuteur » (F14, phase 5), notifications de fond « Leçon 3 prête » (fil d'activité, phase 8).

- [ ] **Step 1: Write the failing tests**

```ts
it("ProgramPage moves a task and refetches", async () => { /* PATCH /tasks/t1 { planned_date } */ });
it("ProgramPage shows a 422 over budget inline and restores the task", async () => {
  expect(await screen.findByText("Semaine 2 : 760 min prévues, 714 au plus.")).toBeInTheDocument();
});
it("ProgramPage validates a draft", async () => { /* POST /programs/p1/validate → bandeau « Programme validé » */ });
it("ProgramPage asks for a revision with a note", async () => { /* POST /sessions/s1/resume { action: "revise", note } */ });
it("ProgramPage offers PDF and .ics exports", () => { expect(screen.getByRole("link", { name: "Exporter en PDF" })).toHaveAttribute("href", expect.stringMatching(/export\.pdf$/)); });
it("LessonPage renders the lesson, its resources and the PDF link", async () => { ... });
it("LessonPage says a lesson is being prepared", async () => { ... });
it("LibraryPage filters by type and status", async () => { /* GET /resources?type=video&status=to_read */ });
it("ResourceList toggles read status", async () => { /* PATCH /resources/r1 { status: "read" } */ });
it("declares Programme, Leçons and Bibliothèque under Apprendre", () => { ... });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/features/program src/features/lessons src/app` → FAIL.
- [ ] **Step 3: Implement** api, hooks, conversions, composants restants, pages, manifestes, lignes du registre.
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 5: Décision D96** (dans le rapport) : cinq entrées sous Apprendre (15.1 : Objectifs, Conseil, Programme, Leçons, Bibliothèque) ; validation par la route dédiée, révision par reprise ; 422 du serveur affichée et calendrier recalé ; « Demander au tuteur » et notifications laissés aux phases 5 et 8.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): écrans Programme, Leçons et Bibliothèque"`

---

### Task 4.16 : Parcours de bout en bout n° 1 et contrôle de fin de phase (contrôleur)

**Zone : back puis front, puis contrôleur.** L'implémenteur écrit le serveur de bout en bout, le parcours Playwright, le script de contrôle et leurs tests ; le contrôleur fait la revue complète (avant cette tâche), le contrôle sous Docker, le parcours dans le navigateur, le tag, le push et le bilan.

**Files:**
- Create: `backend/tests/e2e/__init__.py`, `backend/tests/e2e/server.py`, `backend/tests/e2e/scripted_models.py`, `backend/tests/e2e/council_script.py` ; `backend/scripts/check_phase4.py` ; `frontend/playwright.config.ts`, `frontend/e2e/council.spec.ts`
- Modify: `backend/app/main.py` (`create_app(..., chat_models: ChatModelSource | None = None)`), `frontend/package.json` (`pnpm add -D @playwright/test` ; script `e2e`), `frontend/eslint.config.js` et `tsconfig` (dossier `e2e/` hors règles de feature), `.gitignore` (rapports Playwright)
- Test: `backend/tests/e2e/test_scripted_models.py`, `backend/tests/scripts/test_check_phase4.py`

**Interfaces:**
- Produces:

```python
# tests/e2e/scripted_models.py
Reply = str | Callable[[Sequence[BaseMessage]], str]
class ScriptedModels:   # ChatModelSource : une file de réponses PAR AGENT (sessions concurrentes sans ordre global)
    def __init__(self, scripts: Mapping[str, Sequence[Reply]]) -> None
    async def get_chat_model(self, user_id: str, tier: Tier, agent: str | None = None) -> BaseChatModel
#   file épuisée → RuntimeError nommant l'agent (jamais le contenu des messages)
# tests/e2e/council_script.py
def council_scripts() -> dict[str, list[Reply]]
#   cadrage 2 questions ; plan de recherche ; 10 notes (8 ≥ 60) ; 2 praticiens ; 3 tours × 4 agents
#   (≤ 150 mots, citations [1], noms dès le tour 2, « Objection : », « January » au tour 2) ; tableaux ;
#   2 propositions ; plan de 2 semaines × 1 module ; ressources, leçons (lesson_markdown), vérifications
# tests/e2e/server.py — `uv run python -m tests.e2e.server --port 8765 --data-dir <dossier>`
#   base migrée (alembic), create_app(settings, memory_providers=fake…, research_providers=fake…
#   (FakeSearch : 10 résultats ; FakeWebReader : pages correspondantes), publishing_providers=
#   FakeHtmlRenderer (make_pdf), chat_models=ScriptedModels(council_scripts())), uvicorn
# scripts/check_phase4.py
async def run_check(client: httpx.AsyncClient, *, goal: str = "Devenir AI product engineer",
                    timeout_s: float = 1800.0) -> list[str]
#   1. GET /health (gotenberg, searxng ok) ; 2. POST /goals ; 3. réponse au cadrage ;
#   4. attente de choose_path : ≥ 8 source.found notées, 4 agents × debate_rounds tours, ≥ 1 board.update,
#      2 à 3 proposal.ready ; 5. POST /proposals/{premier}/choose ; 6. programme en brouillon,
#      chaque semaine ≤ cap_minutes, pratique et quiz ; 7. POST /programs/{id}/validate ;
#   8. leçons des semaines 1 et 2 `ready` avec PDF (GET /lessons/{id}/pdf → %PDF) et 3 à 6 ressources ;
#   9. GET /programs/{id}/export.pdf et export.ics ; CheckFailed(message français) à la première étape ratée
def main() -> None   # python -m scripts.check_phase4 --api http://localhost:8000 ; code de sortie 0/1
```

```ts
// frontend/e2e/council.spec.ts — « conseil complet » (18.2)
test("un objectif mène à un programme validé avec ses leçons", async ({ page, request }) => {
  // Objectifs → saisir l'objectif → Conseil : répondre au cadrage → 8 sources notées dans l'onglet Sources
  // → 12 bulles de débat (4 agents × 3 tours), un message envoyé au tour 1 repris au tour 2 (« January »)
  // → tableau dessiné (canevas ou repli SVG) → 2 propositions → Choisir → Voir le programme
  // → déplacer une tâche au clavier (« Déplacer vers… ») → Valider → Leçons : 2 leçons prêtes
  // → le lien PDF répond 200 (request.get) ; chaque semaine affiche une charge ≤ 85 %
});
```

- [ ] **Step 1: Write the failing tests** — `test_scripted_models_serve_each_agent_in_order` ; `test_check_runs_against_the_app(app, client)` (fournisseurs factices, `ScriptedModels`, santé remplacée par une réponse OK) → `["santé", "objectif", "cadrage", "conseil", "choix", "programme", "validation", "leçons", "exports"]`.
- [ ] **Step 2: Run** → FAIL. **Step 3:** implémenter `chat_models` dans `create_app`, les modèles scriptés, le serveur, le script de contrôle, la config et le parcours Playwright (`pnpm exec playwright install chromium`). **Step 4:** → PASS ; `cd frontend && pnpm e2e` → le parcours passe (back de bout en bout + `vite` lancés par `webServer`) ; suites complètes back et front → PASS ; `uv run python -m pre_commit run --all-files` → OK.
- [ ] **Step 5: Commit** — `git commit -m "test(e2e): parcours n° 1 (conseil complet) et script de contrôle de fin de phase 4"`
- [ ] **Step 6: Contrôle sous Docker (contrôleur)**
  1. `docker compose up -d --build` ; `GET /api/v1/health` au vert (searxng, gotenberg compris).
  2. `cd backend && uv run python -m scripts.check_phase4 --api http://localhost:${BACKEND_PORT:-8000}` → 9 étapes réussies, avec SearXNG, Gotenberg et GLM 5.3 flash réels (**critère de fin de phase** : un objectif mène à un programme validé avec les leçons PDF de 2 semaines).
  3. Navigateur, `/apprendre/objectifs` : saisir un objectif, répondre au cadrage ; pendant le débat, envoyer un message, cliquer « Plus court » puis « Relancer un tour » → message repris nommément au tour suivant, prises de parole raccourcies, un tour de plus ; pastilles de citation qui ouvrent la source ; panneau Sources avec requêtes, retenues, écartées, illisibles et praticiens.
  4. Tableau : éléments qui apparaissent un à un ; déplacer un nœud, ajouter un texte, « Envoyer mes modifications aux agents » → message « [Tableau] … » dans le fil ; exports PNG, SVG, `.excalidraw` ouverts sans erreur ; repli SVG si un schéma échoue.
  5. Pendant un tour : `docker compose restart backend` → la session reprend au même point, ni tableau ni proposition en double.
  6. Propositions comparables côte à côte ; « Demander un autre tour » puis « Mélanger » deux parcours → programme bâti sur les deux.
  7. Programme : glisser une tâche d'un jour à l'autre, tenter un dépassement (refus lisible), supprimer le dernier quiz (refus), « Demander une révision » puis valider ; export PDF (A4, sommaire, numéros de page) et `.ics` importé dans un agenda.
  8. Leçons des semaines 1 et 2 : PDF A4 avec sommaire, encadrés, schéma Mermaid en SVG, numéros de page ; 3 à 6 ressources par module dont les liens répondent ; un acquis déjà `valide` en mémoire est sauté, un acquis `declare` devient une révision « déjà acquis » (F3).
  9. Bibliothèque : filtres programme, type, langue, statut ; « Lue » conservée après rechargement ; copie locale d'un PDF libre téléchargeable.
  10. `docker compose logs backend | grep -E "https?://|<texte de l'objectif>|<réponse de cadrage>"` → aucune ligne.
  11. Non-régression : `/demo`, `/memoire`, `/reglages/recherche/essai`.
- [ ] **Step 7: Décision D97** (constats du contrôle), bilan `docs/superpowers/bilans/phase-4.md`, commit, tag `phase-4`, `git push` et `git push origin phase-4`.

---

## Auto-revue

- **Couverture de la spec** : 3.1 (cadrage ≤ 5 questions, recherche, tour 1 ≤ 150 mots et carte du domaine, 3 tours réglables, 2 à 3 propositions et leurs champs, choix / mélange / nouveau tour, programme, production) → 4.3, 4.4, 4.5, 4.10 · 3.2 (champ de message actif, réponse nommée, cinq boutons, trois points d'arrêt, reprise après redémarrage) → 4.1, 4.3, 4.4, 4.5, 4.12, 4.14, 4.16 · 3.3 (Excalidraw, Mermaid du Scribe, 150–300 ms, quatre types, modifications renvoyées, états enregistrés, exports, repli) → 4.4, 4.6, 4.11, 4.14 · 3.4 (hiérarchie et champs, 85 %, disponibilité, acquis sauté ou révision de 20 min, pratique + quiz, trois vues, PDF et `.ics`) → 4.2, 4.5, 4.7, 4.8, 4.13, 4.15 · 3.5 (Markdown, 1 200–2 500 mots, structure, Rédacteur / Vérificateur, PDF A4 et gabarit) → 4.8, 4.9, 4.10, 4.13, 4.15 · 3.6 (3 à 6 ressources, champs, copie locale ou fiche, Bibliothèque) → 4.9, 4.10, 4.15 · 4.2 / 4.5 (`source`, `lecon`, acquis `en_cours`) → 4.3 (Éclaireur), 4.7, 4.10 · 9.1 (8 agents et niveaux) → 4.3, 4.4, 4.5, 4.9 · 9.2 (`learning_council`, `program_builder`, `lesson_factory`) · 9.3 → 4.4 · 9.4 → 4.3, 4.4, 4.5 (interruptions seules dans leur nœud, tests de rejeu) · 9.5 (`board.update`, `proposal.ready`, `artifact.ready`, `source.found`, `user.message`) → 4.1, 4.4, 4.5, 4.9 · 9.6 (APScheduler, leçons à 7 jours) → 4.10 · 10.3 (praticiens, seuil 60 pour une leçon) → 4.3, 4.9 · 13.3 / 13.4 (13 tables) → 4.2 · 14.2 → 4.6, 4.7, 4.8, 4.10 · 15.1 à 15.4 → 4.11 à 4.15 · 17.2 à 17.4 → 4.3, 4.6, 4.8, 4.9, 4.16 · 18.1 et 18.2 (critère de fin, parcours n° 1) → 4.16 · 18.3 F1 (4 agents, 3 tours, ≥ 8 sources notées, tableau, 2–3 propositions, message repris) → 4.4, 4.16 ; F2 (thème, objectif, livrable, tâches datées, 85 %, leçons PDF et 3–6 ressources des 2 premières semaines) → 4.2, 4.7, 4.10, 4.16 ; F3 (sujet acquis sauté) → 4.2, 4.16 · bilan phase 3 (`httpx2`, rejeu de `judge`, rendu Brave) → 4.1.
- **Hors périmètre volontaire** : carte de compétences F15 et routes `/skills/*` (phase 5, D7 : tables seulement) ; « Demander au tuteur » (F14) ; replanification F13 (`PlanDiff` et `plan_versions` déjà prêts) ; table `jobs`, fil d'activité et notifications de fond (phase 8) ; ressources vidéo transcrites (le lecteur YouTube existe, aucune règle de plus) ; quiz réels de fin de semaine (F9, phase 5 : ici une tâche de type `quiz`) ; mineurs de la phase 3 triés « laisser ».
- **Cohérence des noms** : `AgentPorts` / `NO_PORTS` (4.1) gagne `council` (4.3), `program` (4.5), `lessons` (4.9), branchés par `bootstrap.agent_ports` en 4.6, 4.7 et 4.10 ; `SessionLauncher` (4.1) utilisé par `AgentCouncilStore` (4.6), `ensure_lessons` (4.10) et `JobContext` ; `UserCommand` (4.1) lu par `round_start` / `turn` (4.4) et envoyé par `postCommand` (4.12) ; `BoardKind` défini une fois (`events.py`) et repris par `Board.kind` (4.2), `BoardOut` (4.6), `boardTypes.ts` (4.11) ; `TaskType`, `ResourceType`, `ResourceLevel`, `SkillLevel` définis dans `app/db/models/*` (4.2) et repris par `plan_schema`, `lesson_port` et les schémas d'API ; `PlanDraft` (4.2) produit par le Stratège (4.5), contrôlé par `check_draft` et rangé par `schedule` (4.2) via `AgentProgramStore` (4.7) ; `ProposalDraft` / `Choice` (4.3) écrits par `ProposalSet` (4.4) et `choose` (4.6) ; `mermaid_problems` (4.4) réutilisé par `markdown_to_html` (4.8) ; `MermaidSvg` (4.11) réutilisé par `LessonReader` (4.13) ; `HtmlPdfRenderer` (4.8) utilisé par `AgentLessonStore` (4.10) ; slugs `moderator`, `strategist`, `practitioner`, `skeptic`, `scribe`, `writer`, `verifier` identiques dans `AGENTS`, `agentColors.ts` et `messages/agents.ts`.
- **Décisions** : D82 à D97 réservées, une par tâche ; chaque écart à la spec y est consigné : ports regroupés et lanceur (D82), commandes par `user.message` (D82), budget sur samedi et révision « déjà acquis » selon le niveau (D83), Éclaireur nœud pour nœud et praticiens jamais inventés (D84), règles du débat tenues par le code (D85), routes hors 14.2 (`GET /goals/{id}`, tableaux : D87 ; `GET /programs`, `PATCH /programs/{id}` : D88 ; `GET /programs/{id}/lessons`, `GET /resources/{id}/file` : D91), Mermaid rendu par nos scripts figés dans Gotenberg (D89), une session `lesson_factory` par module et production en chaîne (D90, D91), lecture sans `user_id` du planificateur (D91).
