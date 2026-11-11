# Phase 3 — Recherche web : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mode d'exécution déjà choisi : **subagent-driven allégé** (voir « Déroulement » ci-dessous).

**Goal:** Donner aux agents une recherche web gratuite et sûre : SearXNG par défaut, Brave en secours plafonné à 900 requêtes par mois, un lecteur de pages étendu (GitHub, arXiv, repli Gotenberg, PDF en sous-processus, cache 7 jours, une requête par seconde et par domaine), des sources notées sur 100 par l'Éclaireur et un statut `ok` / `unreadable` visible ; plus le reliquat de la phase 2.

**Architecture:** Les services externes restent derrière des ports de `backend/app/providers/` : `SearchProvider` (`search/searxng.py`, `search/brave.py`), `PageRenderer` (`pdf/gotenberg.py`), `PdfTextExtractor` (nouvelle implémentation en sous-processus) ; le lecteur de la phase 2 (`SafeHttpFetcher`, `TrafilaturaWebReader`, D63) est **étendu**, jamais réécrit : un `RoutingWebReader` aiguille GitHub et arXiv, le lecteur HTML gagne le repli Gotenberg, le fetcher gagne le débit par domaine. Une nouvelle feature `backend/app/features/research/` porte le cache `web_cache`, la table `sources`, les plafonds (session et Brave), le nettoyage des requêtes et l'adaptateur `AgentWebGateway`. Les agents y accèdent par un port `WebGateway` défini dans `app/agents/tools/web_port.py` (contrat 6), branché par `app/bootstrap.py` comme la mémoire (D68). L'Éclaireur (`scout`) tourne dans un parcours de banc d'essai `web_research` qui sera réutilisé tel quel par le Conseil en phase 4. Côté front : `SourcesPanel` dans `shared/session-ui/`, une page « Recherche web » dans `settings/`, une feature `research/` (essai de recherche), et la reprise du suivi de l'Archiviste dans `memory/`.

**Tech Stack:** `httpx` (SearXNG, Brave, Gotenberg, API GitHub et arXiv), `defusedxml` (flux Atom d'arXiv), `asyncio.create_subprocess_exec` + `resource` (PDF), `trafilatura`, `pdfplumber` · React, TanStack Query, openapi-fetch, Vitest, Testing Library, MSW.

**Spec:** `SPEC.md` §9.1 (Éclaireur), §9.4 (piège du nœud rejoué), §9.5 (`source.found`, `tool.called`, `tool.result`), §10 (10.1 à 10.4), §11.3 (clé Brave, 900 requêtes), §11.4 (langues, domaines), §12.3 (`search/`, `pdf/gotenberg.py`, `web/github.py`, `web/arxiv.py`, `tools/web_tools.py`), §13.3 (`sources`), §13.6 (`web_cache`), §17.2, §17.3, §17.4, §18.1 (phase 3). Plan directeur : `docs/superpowers/plans/2026-11-11-00-plan-directeur.md` (§1.2, §1.3, §1.4). Bilan : `docs/superpowers/bilans/phase-2.md` (« Points laissés pour plus tard → Phase 3 »). Décisions : D63 (lecteur web), D66 (ingestion), D68 (port mémoire).

## Global Constraints

Toutes celles du plan directeur s'appliquent (300 lignes par fichier, 50 par fonction, couches router → service → repository, filtre `user_id` partout, aucun appel LLM réel en test, textes front centralisés, etc.). Propres à cette phase :

- **Fournisseurs** (10.1) : interface `SearchProvider.search(query, lang, time_range, categories)` → liste de résultats (titre, lien, extrait, moteur, date). SearXNG par défaut, sans clé ; Brave **seulement si une clé existe** ; ordre de repli réglable, par défaut `["searxng", "brave"]`. SearXNG en JSON (`search.formats: [html, json]`), moteurs généralistes (au moins trois, en parallèle) plus Wikipedia, GitHub, arXiv, Stack Overflow, YouTube.
- **Brave** (11.3) : la clé se saisit comme les clés LLM (chiffrée, 4 derniers caractères seulement, jamais journalisée) ou dans `.env` (`BRAVE_API_KEY`) ; **900 requêtes par mois civil UTC** au plus, puis Brave est sauté.
- **Lecture** (10.2) : page web (httpx + trafilatura), page rendue en JavaScript (repli Gotenberg : URL → PDF → texte), PDF, YouTube (transcription, sinon titre et description), dépôt GitHub (API publique, README), papier arXiv (API arXiv). `web_read(url)` rend texte, titre, auteur, date, langue et un statut **`ok` ou `unreadable`**. Une page `unreadable` n'est **jamais citée** ; aucun contournement de page protégée par connexion. **Cache 7 jours** dans `web_cache`. **15 s au plus par page** (repli compris), **une requête par seconde et par domaine**.
- **Notation** (10.3) : sur 100 = autorité 30 + fraîcheur 20 + profondeur 20 + auteur réel 15 + qualité pédagogique 15 ; **60 pour être retenue**. Requêtes en français et en anglais par défaut (`search_languages`). Domaines privilégiés et exclus dans les réglages, avec une liste de départ. L'interface montre les requêtes lancées, les sources retenues et les sources écartées avec la raison.
- **Plafonds** (10.4) : **12 requêtes et 30 pages lues par session**, réglables.
- **Sécurité** (17.2, 17.3, 17.4) :
  - toute lecture d'URL, y compris GitHub, arXiv et le repli Gotenberg, passe d'abord par la garde SSRF de D63 (`SafeHttpFetcher` + `GuardedTransport`) ; Gotenberg ne reçoit qu'une URL déjà validée, jamais de HTML ;
  - la recherche retire nom, email et téléphone des requêtes avant envoi (17.3) ;
  - pages lues = contenu non fiable : tout texte de page rendu à un agent passe par `untrusted()` (17.4) ;
  - **journaux : identifiants seulement** (utilisateur, session, source, fournisseur, code d'erreur), **jamais une URL, une requête de recherche, un titre ni un extrait** ; aucun message d'erreur ne cite l'URL ni la requête ; erreurs levées `from None` (la chaîne d'exceptions citerait l'URL).
- **Tests sans réseau** : jamais SearXNG, Brave, Gotenberg, GitHub, arXiv ni le web réels. `FakeSearch`, `FakeWebReader` (existant), `FakeRenderer`, `httpx.MockTransport`, résolveur injecté. Seuls les tests marqués `live` (désélectionnés par défaut) touchent un vrai SearXNG ou Gotenberg.
- Contrat front/back : toute tâche back qui change l'API régénère `contracts/openapi.json` (`cd backend && uv run python -m scripts.export_openapi`) **et** `frontend/src/shared/api/schema.d.ts` (`pnpm --dir frontend gen:api`) dans le même commit ; aucune tâche front ne modifie ces deux fichiers à la main.
- Front : textes dans `frontend/src/shared/i18n/messages/<zone>.ts` agrégés par `fr.ts` (D60) ; composants de `components/` présentationnels (types de vue locaux, D34) ; jamais de `window.confirm` ; états vide, chargement, erreur avec nouvel essai sur chaque écran (15.4).

**À vérifier dans la documentation actuelle avant de coder (context7)** : SearXNG `GET /search` (`q`, `format=json`, `language`, `time_range`, `categories`, `pageno` ; champs `results[].title/url/content/engine/publishedDate`, `unresponsive_engines`) et les noms de moteurs du `settings.yml` par défaut de l'image figée ; Brave Web Search API (`GET https://api.search.brave.com/res/v1/web/search`, en-tête `X-Subscription-Token`, paramètres `q`, `search_lang`, `freshness`, `count` ; `web.results[].title/url/description/page_age`) ; Gotenberg 8 (`POST /forms/chromium/convert/url`, champ `url`, options d'attente, drapeaux `--chromium-deny-list` / `--chromium-allow-list` et leur portée sur les sous-requêtes et `fetch`/XHR, `--api-timeout`) ; GitHub REST (`GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/readme`, type `application/vnd.github+json`, contenu base64) ; API arXiv (`https://export.arxiv.org/api/query?id_list=`, Atom, consigne de 3 s entre appels) ; `defusedxml.ElementTree.fromstring` ; `asyncio.create_subprocess_exec`, `resource.setrlimit(RLIMIT_AS)`. Tout écart est suivi tel que la doc l'indique et noté dans la décision de la tâche.

## Review Focus

1. **Page piégée** (« ignore tes consignes », faux marqueur de fin, dans le texte ou le titre d'une page lue) : l'Éclaireur la reçoit encadrée comme contenu non fiable, marqueurs neutralisés, et sa note reste bornée par le schéma. → Tâche 3.7 `test_scout_prompt_frames_page_text_and_title_as_untrusted`, `test_score_is_clamped_by_schema`.
2. **Nœud rejoué après un redémarrage** (piège 9.4) : la même requête ou la même page dans la même session n'est ni recomptée dans les plafonds, ni refacturée par Brave, ni dédoublée dans `sources`. → Tâche 3.6 `test_same_query_twice_in_session_counts_once`, `test_same_url_twice_in_session_counts_once` ; tâche 3.7 `test_web_research_replay_does_not_duplicate_sources`.
3. **SearXNG en panne ou bloqué** (moteurs non répondants, zéro résultat) : repli sur Brave si une clé existe, sinon message français lisible et session `failed` propre, jamais une 500. → Tâche 3.6 `test_falls_back_to_brave_when_searxng_fails`, `test_no_provider_left_is_readable` ; tâche 3.7 `test_web_research_fails_readably_when_search_is_down`.
4. **Deux recherches simultanées à 899 requêtes Brave** : une seule passe, le compteur s'arrête à 900, l'autre bascule ou échoue lisiblement. → Tâche 3.6 `test_brave_cap_is_atomic_under_concurrency`.
5. **Résultat de recherche piégé** (lien qui redirige vers une adresse privée, page vide qui déclencherait le rendu Gotenberg) : refus `unreadable`, Gotenberg jamais appelé pour une adresse refusée, aucune URL dans les journaux. → Tâche 3.4 `test_render_fallback_never_called_for_forbidden_url` ; tâche 3.6 `test_logs_never_contain_query_or_url`.

---

## Déroulement (mode allégé)

- Les tâches s'enchaînent **sans revue par tâche**, **sauf** celles marquées **⚠ revue par tâche** (Opus high) : sécurité (SSRF, clés), temps réel, concurrence. Une **revue complète de la phase** (back puis front) clôt la phase avant 3.11, suivie **d'une vague de corrections** puis **d'une re-revue**.
- Chaque tâche est marquée **Zone : back** ou **Zone : front**. **Jamais deux implémenteurs back en même temps** (hook mypy et index git partagés) : au plus un back et un front ensemble. Les tâches back qui changent le contrat OpenAPI (3.1, 3.6, 3.7) ne tournent **jamais** en parallèle d'une tâche front : leur commit régénère `schema.d.ts`.
- En vague parallèle, seule la tâche back écrit dans `DECISIONS.md` ; la tâche front met sa décision dans son rapport, le contrôleur la recopie sous son numéro. Numéros réservés, une entrée par tâche : **D71** (3.1), **D72** (3.2), **D73** (3.3), **D74** (3.4), **D75** (3.5), **D76** (3.6), **D77** (3.7), **D78** (3.8), **D79** (3.9), **D80** (3.10), **D81** (3.11). Format existant (Date, Sujet, Décision en points numérotés, Raison).
- Commits par chemins explicites (jamais `git add -A`), hooks jamais sautés ; pas de `pre-commit run --all-files` pendant qu'un autre agent écrit.

| Vague | Zone : back | Zone : front |
| --- | --- | --- |
| 1 | 3.1 ⚠ (contrat) | — |
| 2 | 3.2 ⚠ | 3.8 |
| 3 | 3.3 ⚠ | 3.9 |
| 4 | 3.4 ⚠ | — |
| 5 | 3.5 | — |
| 6 | 3.6 ⚠ (contrat) | — |
| 7 | 3.7 (contrat) | — |
| 8 | — | 3.10 |
| — | Revue complète, vague de corrections, re-revue | |
| 9 | 3.11 (contrôleur) | |

Commandes de contrôle d'une tâche back : `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run python -m mypy app && uv run python -c "from importlinter.cli import lint_imports_command; lint_imports_command()" && uv run python -m scripts.export_openapi --check` (la longueur des fichiers est contrôlée par le hook de pre-commit au commit). Front : `cd frontend && pnpm vitest run && pnpm lint && pnpm typecheck`.

## Interfaces consommées (phases 0 à 2)

- `app.config.Settings` : `searxng_url`, `gotenberg_url`, `brave_api_key`, `data_dir` ; `app.core.errors.AppError(code, message, status_code=400, details=None)` ; `app.core.security.KnownSecrets.add` ; `app.core.deps` : `Db`, `CurrentUserDep`, `RuntimeDep`, `get_providers`.
- `app.core.providers` : `Providers(llm, llm_factory, cipher, env_keys, health_checks)`, `MemoryProviders(embedder, index, storage, pdf, web, youtube)`.
- `app.bootstrap` : `build_providers`, `memory_providers(settings)`, `_reader_http()`, `memory_gateway(runtime)`, `open_memory_runtime` ; `app.main.create_app(settings, *, memory_providers=None)` et `_lifespan`.
- Lecteur web (D63) : `app.providers.web.base` (`FETCH_TIMEOUT_S = 15.0`, `FETCH_MAX_BYTES`, `ALLOWED_CONTENT_TYPES`, `FetchedResource`, `WebDocument(url, title, text, author, date, lang, description)`, `UrlForbidden`, `UrlTooLarge`, `UrlUnsupported`, `UrlUnreadable(message)`, `WebFetcher`, `WebReader.read(url, *, require_text=True)`, `youtube_video_id`), `app.providers.web.fetch` (`SafeHttpFetcher(http, *, resolve)`, `system_resolve`, `is_public_address`, `refuse_all_cookies`), `app.providers.web.transport.GuardedTransport`, `app.providers.web.reader` (`TrafilaturaWebReader(fetcher, pdf)`, `MIN_TEXT_CHARS = 200`), `app.providers.web.youtube.TranscriptApiYoutube(reader)`.
- PDF : `app.providers.pdf.base` (`MAX_PDF_PAGES = 500`, `MAX_TEXT_CHARS = 2_000_000`, `PdfUnreadable`, `PdfTextExtractor`), `app.providers.pdf.extract.PdfPlumberExtractor` (`_extract(data, max_pages, max_chars)`), `scripts.sample_pdf.make_pdf(lines)`.
- Sondes : `SearxngProbe`, `GotenbergProbe` (déjà dans `/health`).
- Clés : `app.features.settings.keys_service` (`ApiKeyService`, `DbKeyReader(session_factory, cipher, env_keys).get_key(user_id, provider)`), `app.providers.llm.base` (`KeyTestResult(ok, message)`, `LlmProvider`, `KeyReader`).
- Réglages : `app.features.settings.schemas.UserSettings` (déjà : `search_languages = ["fr", "en"]`, `preferred_domains = []`, `excluded_domains = []`, `search_provider_order = ["searxng", "brave"]`), `SettingsService(db, user_id).get()`, `RunSettings.search_languages`.
- Mémoire : `app.features.memory.service.upload.normalize_url(url)` (D66), `MemoryRuntime`, `DocumentsService.mark_learned`, pipeline (`service/pipeline.py`, `service/ingest_steps.py`), `app.agents.tools.memory_port` (`AgentWrite`, `MemoryGateway`), `app.agents.tools.memory_tools` (`memory_write`, `memory_tools_for`).
- Moteur : `GraphDeps(user_id, session_id, models, bus, settings, session_factory, memory)`, `SessionRunner.start(user_id, graph, input, subject_type=None, subject_id=None)`, `agent_runtime(..., *, memory=)`, `emit(type, payload, agent=)`, `structured_call(model, schema, messages, *, agent, step, intent, retries=2)`, `node_timeout()`, `render_prompt(agent, **vars)`, `untrusted(text, label)`, `AGENTS`, `GRAPHS`, `GraphSpec(name, input_model, build)`, `SourceFoundPayload(title, url, author, date, lang, score)`, `SessionView`, `app.db.models.agents.Session.subject_type/subject_id`.
- Tests back : fixtures `settings`, `db_session_factory`, `app`, `client`, `memory_providers` (`tests/conftest.py`) ; `fake_memory_providers(tmp_path)`, `FakeWebReader`, `FakeYoutube` (`tests/support/memory.py`) ; `act_as(app, user_id)`, `use_test_runtime(monkeypatch)` (`tests/sessions_support.py`) ; `fake_llm(replies)`, `wait_status`, `all_events` (`tests/agents/runtime/runner_helpers.py`) ; fixture `emitted`.
- Front : `api`, `apiBaseUrl`, `unwrap`, `errorMessage`, `t`, `MessageKey`, `FeatureManifest`, `NavEntry`, `FEATURES`, `useSessionStream(sessionId, options)`, `startSession(graph, input)`, `SessionView`, `SessionEvent`, `EventOf<T>`, `agentIdentity(slug)` (`scout` déjà déclaré : « Éclaireur », `#18788b`), `EmptyState`, `LoadingState`, `ErrorState`, `InlineError`, `Button`, `fieldClass`, `fetchSettings`, `putSettings`, `buildUserSettings`, `useSettings`, `useUpdateSettings` (`features/settings/`), `useDocumentActions`, `LearnedProgress` (`features/memory/`), serveur MSW `src/test/server.ts`, `createFakeSocketServer`, `queryWrapper`.

---

### Task 3.1 : Back — reliquat de la phase 2 (suivi de l'Archiviste, vecteurs orphelins, titre encadré) ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI (`SessionView`). Risque : concurrence (double clic sur « Déjà appris », suppression pendant un import).

**Files:**
- Modify: `backend/app/features/sessions/schemas.py`, `backend/app/features/sessions/service.py`, `backend/app/features/sessions/repository.py` ; `backend/app/features/memory/service/documents.py` (`mark_learned`), `backend/app/features/memory/service/runtime.py` (verrou), `backend/app/features/memory/service/ingest_steps.py` (M2) ; `backend/app/agents/tools/memory_tools.py` ; `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/features/sessions/test_router.py`, `backend/tests/features/memory/test_documents_learned.py`, `backend/tests/features/memory/test_pipeline.py`, `backend/tests/agents/tools/test_memory_tools.py`

**Interfaces:**
- Produces:

```python
# sessions/schemas.py — SessionView gagne deux champs (lus sur la ligne `sessions`)
subject_type: str | None
subject_id: str | None
# sessions/service.py — lecture pour les autres features (contrat 2 : service seulement)
async def find_active_session(db: AsyncSession, user_id: str, *, graph: str,
                              subject_type: str, subject_id: str) -> str | None
#   session la plus récente de ce graphe et de cet objet en `running`, `waiting_user` ou `paused`
# memory/service/runtime.py
MemoryRuntime.learn_lock(user_id: str) -> asyncio.Lock   # un verrou par utilisateur
```

- `DocumentsService.mark_learned` : sous `learn_lock(user_id)`, `find_active_session(graph="learned_document", subject_type="document", subject_id=doc.id)` ; s'il y en a une, la rend (202, même `session_id`) sans en lancer une seconde.
- M2 : en fin d'import, si la mise à jour conditionnelle de `indexed_at` ne touche aucune ligne parce que l'élément ou le document a disparu, les vecteurs poussés sont retirés (`index.delete_items(user_id, [item_id])`, panne du magasin avalée et journalisée par identifiant).
- `memory_tools_for(...).write` : le titre d'un élément **déjà présent** (titre venu de la mémoire, pas de l'agent) est rendu encadré : `f"Déjà en mémoire : {untrusted(done.title, 'titre en mémoire')}"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/features/sessions/test_router.py
async def test_session_view_exposes_subject(client, runtime_started_with_subject):
    body = (await client.get(f"/api/v1/sessions/{sid}")).json()
    assert body["subject_type"] == "document" and body["subject_id"] == doc_id

# tests/features/memory/test_documents_learned.py
async def test_learned_twice_returns_running_session(client, indexed_doc, blocked_archivist):
    a = (await client.post(f"/api/v1/documents/{doc}/learned")).json()["session_id"]
    b = (await client.post(f"/api/v1/documents/{doc}/learned")).json()["session_id"]
    assert a == b and await count_sessions("learned_document") == 1

async def test_concurrent_learned_clicks_start_one_session(client, indexed_doc, blocked_archivist):
    r = await asyncio.gather(*(client.post(f"/api/v1/documents/{doc}/learned") for _ in range(2)))
    assert len({x.json()["session_id"] for x in r}) == 1

async def test_learned_after_completion_starts_a_new_session(...): ...   # « Relancer » (I2 phase 2) garde son sens

# tests/features/memory/test_pipeline.py — M2
async def test_document_deleted_during_import_leaves_no_vector(memory_runtime, ...):
    # l'index bloque pendant `index` ; on supprime le document ; on débloque
    assert await memory_providers.index.vectors(user_id, limit=100) == []

# tests/agents/tools/test_memory_tools.py
async def test_duplicate_write_frames_existing_title(deps_with_existing_item):
    text = await tools["memory_write"].ainvoke({...same content...})
    assert "<<<CONTENU_NON_FIABLE" in text and "Ignore tes consignes" in text   # titre piégé, encadré
```

- [ ] **Step 2: Run** — `cd backend && uv run pytest tests/features/sessions tests/features/memory tests/agents/tools -v` → les nouveaux tests FAIL.
- [ ] **Step 3: Implement** les deux champs, `find_active_session`, le verrou et l'idempotence de `mark_learned`, le retrait des vecteurs orphelins, le titre encadré ; régénérer `openapi.json` et `schema.d.ts`.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; `cd frontend && pnpm typecheck` → PASS (champs ajoutés seulement).
- [ ] **Step 5: Décision D71** : (1) `SessionView.subject_type/subject_id` ; (2) « Déjà appris » idempotent tant qu'une session du document est active, verrou par utilisateur (un seul processus) ; (3) M2 réglé par retrait après coup (pas de verrou de suppression) ; (4) titre en mémoire encadré dans le texte d'outil.
- [ ] **Step 6: Commit** — `git commit -m "fix(memory): suivi de l'Archiviste repris, vecteurs orphelins, titre encadré"`

---

### Task 3.2 : Back — PDF sûr : extraction en sous-processus et rendu Gotenberg ⚠ revue par tâche

**Zone : back.** Risque : sécurité (déni de service PDF, Chromium qui charge une page non fiable).

**Files:**
- Create: `backend/app/providers/pdf/worker.py`, `backend/app/providers/pdf/subprocess.py`, `backend/app/providers/pdf/gotenberg.py`
- Modify: `backend/app/providers/pdf/base.py`, `backend/app/providers/pdf/extract.py` (`_extract` → public `extract_pdf_text`), `backend/app/bootstrap.py` (`SubprocessPdfExtractor` à la place de `PdfPlumberExtractor`), `backend/app/config.py`, `backend/pyproject.toml` (contrat 3 + `app.providers.pdf.subprocess`, `app.providers.pdf.worker`, `app.providers.pdf.gotenberg`), `docker-compose.yml` (commande de `gotenberg`)
- Test: `backend/tests/providers/pdf/test_subprocess.py`, `backend/tests/providers/pdf/test_gotenberg.py`, `backend/tests/infra/test_compose.py`

**Interfaces:**
- Produces:

```python
# pdf/base.py
PDF_TIMEOUT_S = 60.0
PDF_MAX_MEMORY_BYTES = 1024 * 1024 * 1024
PDF_TIMEOUT_MESSAGE = "PDF trop long à lire : délai dépassé."
class PdfUnreadable(AppError):           # message facultatif, toujours une constante de ce module
    def __init__(self, message: str = <message actuel>) -> None
class PageRenderer(Protocol):
    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes
class RenderFailed(AppError)             # "render_failed", 502, « Rendu de la page impossible. »
RENDER_MAX_BYTES = 20 * 1024 * 1024

# pdf/extract.py
def extract_pdf_text(data: bytes, max_pages: int, max_chars: int) -> str   # ex-`_extract`, inchangé

# pdf/worker.py — `python -m app.providers.pdf.worker <max_pages> <max_chars> <max_memory_bytes>`
#   pose RLIMIT_AS lui-même (POSIX ; ignoré ailleurs), lit le PDF sur stdin, écrit le texte UTF-8
#   sur stdout ; code 0 = texte, 3 = illisible ; n'importe ni FastAPI ni la base

# pdf/subprocess.py
class SubprocessPdfExtractor:
    def __init__(self, *, timeout_s: float = PDF_TIMEOUT_S,
                 max_memory_bytes: int = PDF_MAX_MEMORY_BYTES, concurrency: int = 2) -> None
#   asyncio.create_subprocess_exec(sys.executable, "-m", "app.providers.pdf.worker", ...),
#   cwd = racine du back (parent du paquet `app`), sémaphore de `concurrency` ;
#   délai → kill + wait → PdfUnreadable(PDF_TIMEOUT_MESSAGE) ; code ≠ 0 → PdfUnreadable() ;
#   stdout lu au plus 4 × MAX_TEXT_CHARS octets ; stderr jeté (jamais journalisé)

# pdf/gotenberg.py
class GotenbergRenderer:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None
#   POST {base_url}/forms/chromium/convert/url, multipart `url` (+ options d'attente vérifiées
#   dans la doc), sous asyncio.timeout(timeout_s) ; corps lu en flux, > RENDER_MAX_BYTES → RenderFailed ;
#   statut ≠ 200, délai, erreur réseau → RenderFailed ; ni l'URL ni le corps dans le message ou le journal
```

- `Settings.web_render_fallback: bool = True` (coupe le repli Gotenberg, lu en 3.4).
- `docker-compose.yml`, service `gotenberg` : `command` avec `--chromium-deny-list` refusant `file:`, les noms internes (`backend`, `frontend`, `qdrant`, `ollama`, `searxng`, `gotenberg`, `localhost`, `host.docker.internal`) et les IP littérales privées, de boucle locale, de lien local (dont `169.254.169.254`) et IPv6 non globales ; forme exacte du drapeau vérifiée dans la doc de l'image figée.

- [ ] **Step 1: Write the failing tests**

```python
async def test_subprocess_extracts_generated_pdf():
    assert "Bonjour Tremplin" in await SubprocessPdfExtractor().extract_text(make_pdf(["Bonjour Tremplin"]))

async def test_subprocess_garbage_is_unreadable():
    with pytest.raises(PdfUnreadable): await SubprocessPdfExtractor().extract_text(b"pas un pdf")

async def test_subprocess_timeout_kills_worker(monkeypatch):
    # worker remplacé par `python -c "import time; time.sleep(30)"` ; timeout_s=0.5
    with pytest.raises(PdfUnreadable) as e: await extractor.extract_text(b"%PDF-")
    assert e.value.message == PDF_TIMEOUT_MESSAGE and no_child_left()

async def test_subprocess_limits_concurrency(): ...   # concurrency=1, deux appels : jamais 2 processus vivants

@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_AS POSIX seulement")
async def test_worker_sets_memory_limit(): ...        # worker de test qui alloue 2 Gio → code ≠ 0 → PdfUnreadable

async def test_renderer_posts_url_form(respx_or_mock_transport):
    pdf = await GotenbergRenderer(http, "http://gotenberg:3000").url_to_pdf("https://ex.org/app", timeout_s=5)
    assert pdf.startswith(b"%PDF") and sent_form["url"] == "https://ex.org/app"

async def test_renderer_errors_never_cite_url(): ...  # 500, délai, corps > RENDER_MAX_BYTES → RenderFailed, message fixe

def test_gotenberg_denies_internal_hosts():           # tests/infra/test_compose.py
    deny = _deny_regex(compose["services"]["gotenberg"]["command"])
    for url in ["http://backend:8000/api/v1/memory/items", "http://169.254.169.254/latest",
                "http://10.0.0.1/", "http://[::1]/", "file:///etc/passwd", "http://qdrant:6333/"]:
        assert re.search(deny, url)
    assert not re.search(deny, "https://example.org/page")
```

- [ ] **Step 2: Run** — `uv run pytest tests/providers/pdf tests/infra/test_compose.py -v` → FAIL.
- [ ] **Step 3: Implement** le worker, l'extracteur, le client Gotenberg (client `httpx.AsyncClient(trust_env=False)` dédié, créé dans `bootstrap.memory_providers`), la commande compose ; l'extracteur en sous-processus remplace `PdfPlumberExtractor` dans la composition (import de documents et lecteur web).
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS (toute la suite PDF de la phase 2 passe avec le sous-processus).
- [ ] **Step 5: Décision D72** : (1) DoS PDF de D63 levé : sous-processus, 60 s, 1 Gio (`RLIMIT_AS`, POSIX), 2 au plus ; (2) le repli Gotenberg envoie une **URL** (`convert/url`), jamais du HTML : 17.4 (« HTML nettoyé de tout script ») vise les gabarits des phases 4 et 6 ; (3) liste de refus Chromium et risque résiduel (rebinding DNS d'un nom public vers une adresse interne pendant le rendu ; requêtes sans prévol vers le back) ; interrupteur `WEB_RENDER_FALLBACK`.
- [ ] **Step 6: Commit** — `git commit -m "feat(providers): PDF en sous-processus borné, rendu d'URL par Gotenberg"`

---

### Task 3.3 : Back — fournisseurs de recherche (SearXNG, Brave) et clé Brave ⚠ revue par tâche

**Zone : back.** Ne change pas le contrat OpenAPI (Brave apparaît dans la liste existante des clés). Risque : clé (stockage, test, journaux).

**Files:**
- Create: `backend/app/providers/search/base.py`, `searxng.py`, `brave.py`, `fake.py` ; `backend/app/providers/keys.py` ; `backend/tests/support/research.py`
- Modify: `backend/app/core/providers.py` (`Providers.key_providers`, `ResearchProviders`), `backend/app/bootstrap.py` (`research_providers`, `env_keys["brave"]`), `backend/app/main.py` (`create_app(..., research_providers=)`, lifespan), `backend/app/features/settings/keys_service.py`, `keys_router.py`, `backend/infra/searxng/settings.yml` (3 moteurs généralistes au moins), `backend/pyproject.toml` (contrat 3 + `app.providers.search.searxng`, `app.providers.search.brave`, `app.providers.search.fake`), `backend/tests/conftest.py` (fixture `research_providers`)
- Test: `backend/tests/providers/search/test_searxng.py`, `test_brave.py`, `test_searxng_live.py` ; `backend/tests/features/settings/test_keys_router.py` ; `backend/tests/infra/test_searxng_settings.py` ; `backend/tests/test_lifespan.py`

**Interfaces:**
- Produces:

```python
# providers/search/base.py
TimeRange = Literal["day", "week", "month", "year"]
SEARCH_CATEGORIES = ("general", "it", "science", "videos")
MAX_RESULTS = 10
@dataclass(frozen=True)
class SearchResult: title: str; url: str; snippet: str; engine: str; published: str | None
class SearchUnavailable(AppError)   # "search_unavailable", 503, « La recherche web est indisponible pour le moment. »
class SearchProvider(Protocol):
    name: str
    async def search(self, query: str, *, lang: str | None = None, time_range: TimeRange | None = None,
                     categories: Sequence[str] = ()) -> list[SearchResult]   # MAX_RESULTS au plus

# providers/search/searxng.py
class SearxngSearch:      # name = "searxng"
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None
#   GET {base_url}/search?q=&format=json[&language=][&time_range=][&categories=a,b] ; délai 10 s ;
#   résultats sans `url` http(s) écartés ; doublons d'URL retirés ; erreur, statut ≠ 200, JSON invalide,
#   ou zéro résultat avec `unresponsive_engines` non vide → SearchUnavailable

# providers/search/brave.py
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
class BraveSearch:        # name = "brave"
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None
#   en-tête X-Subscription-Token ; `search_lang`, `freshness` (pd/pw/pm/py), `count=10` ;
#   401/403/429/5xx/délai → SearchUnavailable ; la clé n'apparaît dans aucun message ni journal
class BraveKeyProvider:   # name = "brave", label = "Brave Search" ; satisfait KeyProvider
    def __init__(self, http: httpx.AsyncClient) -> None
    async def test_key(self, api_key: str) -> KeyTestResult   # une requête minimale, ne lève jamais

# providers/search/fake.py
@dataclass
class FakeSearch:         # pour les tests et le contrôle de fin de phase sans réseau
    name: str
    results: dict[str, list[SearchResult]] = field(default_factory=dict)   # requête → résultats
    error: AppError | None = None
    calls: list[tuple[str, str | None]] = field(default_factory=list)      # (requête, langue)

# providers/keys.py
class KeyProvider(Protocol):   # ce dont l'écran des clés a besoin ; LlmProvider le satisfait déjà
    name: str
    label: str
    async def test_key(self, api_key: str) -> KeyTestResult

# core/providers.py
BraveFactory = Callable[[str], SearchProvider]          # clé → client Brave
@dataclass(frozen=True)
class ResearchProviders:
    searxng: SearchProvider
    brave: BraveFactory
    web: WebReader                 # le même lecteur que MemoryProviders.web (étendu en 3.4)
Providers.key_providers: Mapping[str, KeyProvider]    # LLM + "brave"

# bootstrap.py
@asynccontextmanager
async def research_providers(settings: Settings, web: WebReader) -> AsyncIterator[ResearchProviders]
#   un client SearXNG (réseau interne) et un client Brave (`trust_env=False`, `follow_redirects=False`),
#   fermés à la sortie ; aucune requête à la construction

# tests/support/research.py
def fake_research_providers(web: WebReader, *, searxng: FakeSearch | None = None,
                            brave: FakeSearch | None = None) -> ResearchProviders
```

- `ApiKeyService(..., providers=key_providers)` : `list`, `set`, `delete`, `test` acceptent `brave` ; `models_overview` et `list_models` ne parcourent que les fournisseurs LLM (`Providers.llm`). `build_providers` ajoute `"brave": settings.brave_api_key` à `env_keys` (déjà dans `KnownSecrets`).
- Le test de clé Brave consomme une requête Brave **non comptée** dans les 900 (décision).

- [ ] **Step 1: Write the failing tests**

```python
async def test_searxng_sends_json_query_and_maps_results(mock_transport):
    hits = await SearxngSearch(http, "http://searxng:8080").search("rag", lang="fr", time_range="year",
                                                                  categories=["it", "science"])
    assert last_request.url.params["format"] == "json" and last_request.url.params["categories"] == "it,science"
    assert hits[0] == SearchResult("RAG", "https://ex.org/rag", "extrait", "duckduckgo", "2026-10-01T00:00:00")

async def test_searxng_drops_non_http_and_duplicate_urls(): ...
async def test_searxng_all_engines_unresponsive_is_unavailable(): ...   # results [] + unresponsive_engines
async def test_searxng_403_is_unavailable_with_fixed_message(): ...

async def test_brave_sends_token_header_and_maps_results(): ...          # X-Subscription-Token, web.results
@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_brave_errors_never_contain_the_key(status, caplog):
    with pytest.raises(SearchUnavailable) as e: await BraveSearch(http, "secret-brave-key-1234").search("x")
    assert "secret-brave-key-1234" not in e.value.message + caplog.text
async def test_brave_key_test_reports_invalid_key(): ...                 # 401 → KeyTestResult(ok=False, …)

async def test_brave_key_listed_saved_and_masked(client):               # tests/features/settings/test_keys_router.py
    await client.post("/api/v1/settings/api-keys", json={"provider": "brave", "key": "BSA-0123456789"})
    brave = next(k for k in (await client.get("/api/v1/settings/api-keys")).json() if k["provider"] == "brave")
    assert brave["last4"] == "6789" and brave["label"] == "Brave Search" and "BSA-0123456789" not in str(brave)
async def test_models_overview_excludes_brave(client): ...
async def test_brave_key_isolated_between_users(client, app): ...

def test_searxng_has_three_general_engines_and_json(): ...              # tests/infra/test_searxng_settings.py
async def test_lifespan_uses_injected_research_providers(app, research_providers, client): ...

@pytest.mark.live
async def test_searxng_live_returns_results(): ...                       # SEARXNG_URL de l'environnement
```

- [ ] **Step 2: Run** — `uv run pytest tests/providers/search tests/features/settings tests/infra tests/test_lifespan.py -v` → FAIL.
- [ ] **Step 3: Implement** les fournisseurs, `KeyProvider`, l'extension des clés, la composition injectable (`create_app(research_providers=)`, posés sur `app.state.research_providers`) et la fixture (toute la suite branche `fake_research_providers` : **aucun test ne peut atteindre SearXNG ni Brave**).
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; `export_openapi --check` inchangé.
- [ ] **Step 5: Décision D73** : (1) `SearchProvider` est notre port, `httpx` sans SDK ; (2) Brave construit par clé (`BraveFactory`), clé lue par `DbKeyReader` (UI d'abord, `.env` ensuite, D8) ; (3) `KeyProvider` : l'écran des clés gère Brave sans le traiter comme un LLM ; (4) test de clé hors compteur des 900 ; (5) moteurs SearXNG retenus (noms vérifiés dans l'image figée) et critère « SearXNG indisponible ».
- [ ] **Step 6: Commit** — `git commit -m "feat(providers): recherche SearXNG et Brave, clé Brave dans les réglages"`

---

### Task 3.4 : Back — lecteur web étendu (débit par domaine, GitHub, arXiv, repli Gotenberg) ⚠ revue par tâche

**Zone : back.** Risque : sécurité (SSRF sur de nouveaux chemins de lecture, Chromium).

**Files:**
- Create: `backend/app/providers/web/throttle.py`, `github.py`, `arxiv.py`, `routing.py`
- Modify: `backend/app/providers/web/base.py` (port `WebFetcher.fetch`, messages), `fetch.py` (débit, types et en-têtes par appel), `reader.py` (repli), `backend/app/bootstrap.py` (assemblage), `backend/pyproject.toml` (`uv add defusedxml` ; contrat 3 + `app.providers.web.throttle`, `.github`, `.arxiv`, `.routing`), `backend/tests/support/memory.py` (`FakeRenderer`)
- Test: `backend/tests/providers/web/test_throttle.py`, `test_github.py`, `test_arxiv.py`, `test_routing.py`, `test_reader.py`, `test_fetch.py`

**Interfaces:**
- Consumes: `PageRenderer`, `RenderFailed`, `SubprocessPdfExtractor` (3.2).
- Produces:

```python
# web/base.py — extension compatible du port (D63) : paramètres nommés avec défaut
class WebFetcher(Protocol):
    async def fetch(self, url: str, *, content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
                    headers: Mapping[str, str] | None = None) -> FetchedResource
GITHUB_UNREADABLE = "Dépôt GitHub illisible : README absent ou API indisponible."
ARXIV_UNREADABLE = "Article arXiv introuvable ou API indisponible."

# web/throttle.py
class DomainThrottle:
    def __init__(self, *, interval_s: float = 1.0, overrides: Mapping[str, float] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None
    async def wait(self, host: str) -> None
#   un départ de requête par `interval_s` et par hôte (minuscules), réservé sous verrou puis attendu
#   hors verrou ; overrides par défaut {"export.arxiv.org": 3.0} ; entrées de plus de 60 s purgées ;
#   partagé par tout le processus (tous utilisateurs)

# web/fetch.py
SafeHttpFetcher(http, *, resolve=system_resolve, throttle: DomainThrottle | None = None)
#   `throttle.wait(host)` avant CHAQUE saut (redirections comprises), après les contrôles (a)-(b) de D63

# web/github.py
def github_repo(url: str) -> tuple[str, str] | None
#   https://github.com/<owner>/<repo>[/...] ; owner ^[A-Za-z0-9-]{1,39}$, repo ^[A-Za-z0-9._-]{1,100}$ ;
#   `.git` retiré ; chemins réservés (orgs, settings, …) → None
class GithubReader:
    def __init__(self, fetcher: WebFetcher) -> None
    async def read(self, url: str) -> WebDocument
#   GET https://api.github.com/repos/{o}/{r} puis /readme (Accept application/vnd.github+json,
#   content_types=("application/json",)) ; texte = README décodé (base64) ; title = full_name,
#   author = owner.login, date = pushed_at, description = description ; échec → UrlUnreadable(GITHUB_UNREADABLE)

# web/arxiv.py
def arxiv_id(url: str) -> str | None   # arxiv.org/abs/<id>, /pdf/<id>[.pdf], ids récents et anciens, version gardée
class ArxivReader:
    def __init__(self, fetcher: WebFetcher, pdf: PdfTextExtractor) -> None
    async def read(self, url: str) -> WebDocument
#   GET https://export.arxiv.org/api/query?id_list=<id> (Atom, defusedxml) → titre, auteurs joints,
#   published, résumé ; puis https://arxiv.org/pdf/<id> par le fetcher et `pdf` ; PDF en échec →
#   résumé seul ; aucune entrée → UrlUnreadable(ARXIV_UNREADABLE)

# web/reader.py
TrafilaturaWebReader(fetcher, pdf, *, renderer: PageRenderer | None = None)
#   HTML dont le texte principal < MIN_TEXT_CHARS ET renderer présent → renderer.url_to_pdf(final_url,
#   timeout_s=temps restant) → pdf.extract_text → texte ; RenderFailed ou texte encore court →
#   UrlUnreadable(NO_TEXT_MESSAGE). Jamais de rendu si le fetch a échoué (adresse refusée, 4xx, type refusé).

# web/routing.py
class RoutingWebReader:     # satisfait WebReader
    def __init__(self, default: WebReader, github: GithubReader, arxiv: ArxivReader) -> None
    async def read(self, url: str, *, require_text: bool = True) -> WebDocument
#   tout l'appel sous asyncio.timeout(FETCH_TIMEOUT_S) (15 s par page, repli compris) → délai :
#   UrlUnreadable(TIMEOUT_MESSAGE) ; github_repo(url) → github ; arxiv_id(url) → arxiv ; sinon default
```

- `bootstrap.memory_providers` : un `DomainThrottle` unique ; `web = RoutingWebReader(TrafilaturaWebReader(fetcher, pdf, renderer=gotenberg if settings.web_render_fallback else None), GithubReader(fetcher), ArxivReader(fetcher, pdf))` ; YouTube garde ce lecteur pour son repli. L'import d'URL de la mémoire en profite sans changement.

- [ ] **Step 1: Write the failing tests**

```python
async def test_throttle_spaces_same_host_by_one_second(fake_clock):
    await t.wait("ex.org"); await t.wait("ex.org")
    assert fake_clock.sleeps == [1.0]
async def test_throttle_does_not_delay_other_hosts(fake_clock): ...
async def test_throttle_arxiv_override_is_three_seconds(fake_clock): ...
async def test_fetch_throttles_each_redirect_hop(): ...      # 302 vers un autre hôte : wait appelé pour les deux

@pytest.mark.parametrize("url,expected", [("https://github.com/psf/requests", ("psf", "requests")),
    ("https://github.com/psf/requests.git", ("psf", "requests")),
    ("https://github.com/psf/requests/tree/main/docs", ("psf", "requests")),
    ("https://github.com/settings/profile", None), ("https://gitlab.com/a/b", None)])
def test_github_repo_forms(url, expected): assert github_repo(url) == expected
async def test_github_reads_readme_and_metadata(): ...       # MockTransport : base64 → texte, owner → author
async def test_github_missing_readme_is_unreadable(): ...    # 404 → GITHUB_UNREADABLE

@pytest.mark.parametrize("url,expected", [("https://arxiv.org/abs/1706.03762", "1706.03762"),
    ("https://arxiv.org/pdf/1706.03762v7.pdf", "1706.03762v7"), ("https://arxiv.org/abs/hep-th/9901001", "hep-th/9901001")])
def test_arxiv_id_forms(url, expected): ...
async def test_arxiv_reads_atom_then_pdf(): ...              # titre, auteurs "A, B", published, texte = PDF
async def test_arxiv_pdf_failure_keeps_abstract(): ...
async def test_arxiv_rejects_xml_entity_bomb(): ...          # defusedxml → ARXIV_UNREADABLE

async def test_js_page_falls_back_to_rendered_pdf(): ...     # HTML vide + FakeRenderer(make_pdf([...]))
async def test_render_fallback_never_called_for_forbidden_url():
    # résolveur → 10.0.0.5 : UrlForbidden levée, FakeRenderer.calls == []
async def test_render_failure_is_unreadable(): ...
async def test_routing_whole_read_under_15s(monkeypatch): ...  # FETCH_TIMEOUT_S=0.1, rendu bloqué → TIMEOUT_MESSAGE
async def test_routing_dispatches_github_arxiv_default(): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/providers/web -v` → FAIL.
- [ ] **Step 3: Implement** les modules et l'assemblage ; tests de la phase 2 du lecteur inchangés.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D74** : (1) port `WebFetcher.fetch` étendu par paramètres nommés (compatible D63) ; (2) débit 1 req/s/hôte (hôte exact, pas de domaine enregistrable), 3 s pour `export.arxiv.org` (consigne de l'API, écart avec 10.2) ; (3) GitHub sans jeton (60 appels par heure, limite connue) ; (4) arXiv : métadonnées + PDF, résumé en repli ; `defusedxml` ; (5) repli Gotenberg seulement après un fetch HTML réussi et un texte trop court ; 15 s pour toute la lecture.
- [ ] **Step 6: Commit** — `git commit -m "feat(providers): lecteur web étendu (débit, GitHub, arXiv, repli Gotenberg)"`

---

### Task 3.5 : Back — tables de la recherche, cache, nettoyage des requêtes et domaines

**Zone : back.** Ne change pas le contrat OpenAPI (aucune route).

**Files:**
- Create: `backend/app/db/models/research.py`, `backend/alembic/versions/0004_research.py`, `backend/app/features/research/__init__.py`, `repository/__init__.py`, `repository/cache.py`, `repository/sources.py`, `repository/queries.py`, `repository/usage.py`, `service/__init__.py`, `service/privacy.py`, `service/domains.py`, `service/cache.py`
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/features/research/conftest.py`, `test_repositories.py`, `test_privacy.py`, `test_domains.py`, `test_cache.py`, `backend/tests/db/test_migrations.py`

**Interfaces:**
- Produces (`app/db/models/research.py` ; types partagés avec `app.agents`, contrat 6) :

```python
PageStatus = Literal["ok", "unreadable"]
SourceVerdict = Literal["pending", "kept", "rejected"]
SourceKind = Literal["page", "person"]        # « pages et personnes repérées » (13.3) ; personnes : phase 4
CacheKind = Literal["page", "search"]
SOURCE_THRESHOLD = 60

class WebCacheEntry(UserScopedMixin, Base):   # table web_cache (13.6)
    kind: str (8); key_hash: str (64); status: str (16); payload: dict (JSON); expires_at: datetime
    # unique (user_id, kind, key_hash)
class Source(UserScopedMixin, Base):          # table sources (13.3)
    session_id: str | None (36); kind: str (8, "page"); url: str (Text); url_hash: str (64)
    title, author, lang, published: str | None; status: str (16); verdict: str (16, "pending")
    score: int | None; score_detail: dict | None (JSON); reason: str | None (300); summary: str | None (Text)
    # unique (user_id, session_id, url_hash) ; index (user_id, session_id)
class WebQuery(UserScopedMixin, Base):        # table web_queries (ajout)
    session_id: str (36); query_hash: str (64); query: str (Text, nettoyée); lang: str | None (8)
    provider: str | None (16); result_count: int (0)
    # unique (user_id, session_id, query_hash)
class SearchUsage(UserScopedMixin, Base):     # table search_usage (ajout)
    provider: str (16); month: str (7, "2026-11"); key_fingerprint: str (16); count: int (0)
    # unique (user_id, provider, month, key_fingerprint)
```

```python
# repository/*.py — tous héritent de UserScopedRepository (filtre user_id)
WebCacheRepository.get(kind, key_hash, now) -> WebCacheEntry | None        # non expirée seulement
WebCacheRepository.put(kind, key_hash, status, payload, expires_at) -> None  # upsert
WebCacheRepository.purge_expired(now) -> int
SourceRepository.get_by_url(session_id, url_hash) -> Source | None
SourceRepository.add(source) / .count_pages(session_id) -> int / .list_for_session(session_id) -> list[Source]
WebQueryRepository.get(session_id, query_hash) -> WebQuery | None
WebQueryRepository.add(query) / .count(session_id) -> int
SearchUsageRepository.increment(provider, month, fingerprint) -> None
async def month_total(db, *, provider: str, month: str, fingerprint: str) -> int
#   SEULE lecture sans filtre user_id de la phase (somme des compteurs d'une même clé, tous
#   utilisateurs : une clé `.env` est partagée en mode Google) ; ne renvoie qu'un nombre

# service/privacy.py
@dataclass(frozen=True)
class Identity: full_name: str | None; email: str | None
def scrub_query(query: str, identity: Identity) -> str
#   retire : tout email (regex), tout numéro de téléphone (formats FR 0X XX XX XX XX, +33 X…, international
#   +<indicatif> 8 à 15 chiffres avec séparateurs), le nom complet et le nom de famille (dernier mot du nom,
#   ≥ 3 lettres) sans tenir compte de la casse ni des accents ; espaces ramassés ; le prénom seul est gardé

# service/domains.py
def normalize_domain(value: str) -> str      # minuscules, sans schéma, chemin, port ni « www. » ; ValueError sinon
def host_matches(host: str, domain: str) -> bool   # égal ou sous-domaine (`docs.python.org` ⊂ `python.org`)
@dataclass(frozen=True)
class RankedHit: result: SearchResult; preferred: bool
def rank_results(results: Sequence[SearchResult], *, preferred: Sequence[str],
                 excluded: Sequence[str]) -> list[RankedHit]
#   exclus retirés ; privilégiés en tête, ordre d'origine conservé dans chaque groupe

# service/cache.py
PAGE_TTL = timedelta(days=7); UNREADABLE_TTL = timedelta(hours=24); SEARCH_TTL = timedelta(hours=24)
def url_key(url: str) -> str                 # sha256 de normalize_url(url) (D66)
def search_key(provider: str, query: str, lang: str | None, time_range: str | None,
               categories: Sequence[str]) -> str
class WebCache:
    def __init__(self, db: AsyncSession, user_id: str, *, now: Callable[[], datetime] = utcnow) -> None
    async def get_page(self, url: str) -> CachedPage | None
    async def put_page(self, url: str, page: CachedPage) -> None   # TTL selon le statut
    async def get_search(self, key: str) -> list[SearchResult] | None
    async def put_search(self, key: str, results: Sequence[SearchResult]) -> None
@dataclass(frozen=True)
class CachedPage: status: PageStatus; title: str | None; text: str; author: str | None
                  date: str | None; lang: str | None; reason: str | None
```

- [ ] **Step 1: Write the failing tests**

```python
async def test_migration_0004_creates_research_tables(alembic_db): ...   # 4 tables, contraintes nommées

async def test_cache_returns_page_within_7_days_then_expires(cache, clock):
    await cache.put_page("https://Ex.org/a#x", CachedPage("ok", "T", "texte", None, None, "fr", None))
    clock.advance(days=6); assert (await cache.get_page("https://ex.org/a")).title == "T"
    clock.advance(days=2); assert await cache.get_page("https://ex.org/a") is None
async def test_unreadable_page_cached_24_hours(cache, clock): ...
async def test_cache_is_per_user(db_session_factory): ...

async def test_month_total_sums_all_users_for_same_key(db): ...
async def test_web_query_unique_per_session(db): ...                  # IntegrityError sur le doublon

@pytest.mark.parametrize("raw,clean", [
    ("cours rag jane.doe@mail.fr", "cours rag"),
    ("Jane Doe portfolio data", "portfolio data"),
    ("doé formation llm", "formation llm"),                            # nom de famille, accents ignorés
    ("Jane python", "Jane python"),                                    # prénom seul gardé
    ("appeler 06 12 34 56 78 ou +33 6 12 34 56 78", "appeler ou"),
    ("rag 2024 llama 3.1 8b", "rag 2024 llama 3.1 8b")])               # chiffres ordinaires gardés
def test_scrub_query(raw, clean): assert scrub_query(raw, Identity("Jane Doé", "jane.doe@mail.fr")) == clean

@pytest.mark.parametrize("value,expected", [("https://www.Python.org/doc", "python.org"), ("docs.python.org", "docs.python.org")])
def test_normalize_domain(value, expected): ...
def test_rank_results_excludes_and_puts_preferred_first(): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/features/research tests/db -v` → FAIL.
- [ ] **Step 3: Implement** modèles, migration, repositories, `privacy`, `domains`, `cache`.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; `alembic upgrade head` puis `downgrade -1` sur une base vide → OK.
- [ ] **Step 5: Décision D75** : (1) schéma des 4 tables, dont 2 ajouts (`web_queries` : rejeu et requêtes affichées ; `search_usage` : 900 par mois) ; (2) `web_cache` par utilisateur ; 7 jours pour une page lue, 24 h pour une page illisible et pour une liste de résultats (parade « cache » de 10.1) ; (3) `month_total`, deuxième lecture sans `user_id` après D18, un nombre seulement ; (4) règle de nettoyage (17.3) : prénom seul gardé (faux positifs), noms complets et de famille retirés ; (5) correspondance des domaines par suffixe.
- [ ] **Step 6: Commit** — `git commit -m "feat(research): tables web_cache et sources, cache, nettoyage des requêtes, domaines"`

---

### Task 3.6 : Back — service de recherche et de lecture, plafonds, Brave 900 par mois, réglages ⚠ revue par tâche

**Zone : back.** Change le contrat OpenAPI (`UserSettings`, `GET /research/usage`). Risque : clé et facturation (plafond Brave), concurrence (compteurs), confidentialité (requêtes).

**Files:**
- Create: `backend/app/features/research/service/errors.py`, `service/runtime.py`, `service/searching.py`, `service/reading.py`, `service/usage.py`, `backend/app/features/research/schemas.py`, `router.py`
- Modify: `backend/app/features/registry.py`, `backend/app/features/settings/schemas.py`, `backend/app/bootstrap.py` (`open_research_runtime`), `backend/app/main.py` (lifespan : `app.state.research`), `backend/app/core/deps.py` (`ResearchDep`), `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/features/research/test_searching.py`, `test_reading.py`, `test_router.py`, `backend/tests/features/settings/test_router.py`

**Interfaces:**
- Consumes: `ResearchProviders` (3.3), `WebCache`, repositories, `scrub_query`, `rank_results` (3.5), `DbKeyReader`, `SettingsService`.
- Produces:

```python
# service/errors.py
QUOTA_CODE = "web_quota_reached"
class WebQuotaReached(AppError)   # 429 ; « Plafond de {cap} requêtes atteint pour cette session. »
                                  #       « Plafond de {cap} pages lues atteint pour cette session. »
class NoSearchProvider(AppError)  # "search_unavailable", 503, « Aucun moteur de recherche n'a répondu. »
BRAVE_MONTHLY_CAP = 900

# service/runtime.py
@dataclass
class ResearchRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: ResearchProviders
    keys: KeyReader                  # DbKeyReader de la composition
    def session_lock(self, user_id: str, session_id: str) -> asyncio.Lock
    brave_lock: asyncio.Lock         # un seul pour le processus (compteur mensuel d'une clé)

# service/searching.py
@dataclass(frozen=True)
class SearchOutcome: query: str; provider: str | None; hits: list[RankedHit]; cached: bool; replayed: bool
async def search(runtime: ResearchRuntime, user_id: str, session_id: str | None, query: str, *,
                 lang: str | None = None, time_range: TimeRange | None = None,
                 categories: Sequence[str] = ()) -> SearchOutcome
#   1. scrub_query (Identity : users.name, users.email) ; vide après nettoyage → 422 `search_query_empty`
#   2. session_id présent : sous session_lock, WebQuery existante (même hash) → résultats du cache,
#      replayed=True, rien de compté ; sinon count(session) ≥ search_max_queries → WebQuotaReached
#   3. cache de recherche (24 h) par fournisseur, dans l'ordre des réglages
#   4. chaîne : fournisseurs de `search_provider_order` ; brave seulement si clé lisible ET
#      _reserve_brave(...) vrai ; SearchUnavailable ou zéro résultat → suivant ; épuisée → NoSearchProvider
#   5. rank_results (domaines des réglages) ; WebQuery écrite (requête nettoyée, fournisseur, nombre)
async def _reserve_brave(runtime, db, user_id: str, api_key: str, now: datetime) -> bool
#   sous brave_lock, transaction unique : month_total(...) < 900 → increment → commit → True ; sinon False
#   empreinte = sha256(clé)[:16] ; mois = now UTC "AAAA-MM"

# service/reading.py
@dataclass(frozen=True)
class PageOutcome: source_id: str | None; url: str; status: PageStatus; title: str | None; text: str
                   author: str | None; date: str | None; lang: str | None; reason: str | None
                   cached: bool; replayed: bool
async def read(runtime: ResearchRuntime, user_id: str, session_id: str | None, url: str) -> PageOutcome
#   1. URL http(s) normalisée (normalize_url) ; domaine exclu → status unreadable, reason
#      « Domaine exclu dans les réglages. », sans lecture
#   2. session_id présent : sous session_lock, Source existante (même url_hash) → rendue, replayed=True ;
#      sinon count_pages(session) ≥ search_max_pages → WebQuotaReached
#   3. cache (page) ; sinon providers.web.read(url) ; AppError de lecture (UrlForbidden, UrlTooLarge,
#      UrlUnsupported, UrlUnreadable, PdfUnreadable) → status unreadable, reason = message de l'erreur ;
#      résultat mis en cache (TTL selon le statut)
#   4. session_id présent : ligne Source (kind page, verdict pending, status) → source_id
async def record_verdict(db, user_id: str, source_id: str, *, score: int, detail: dict[str, int],
                         reason: str, summary: str) -> Source
#   verdict kept si score ≥ SOURCE_THRESHOLD et status ok, sinon rejected ; une source unreadable
#   n'est jamais kept ; idempotent (même verdict réécrit)

# schemas.py / router.py
class BraveUsageOut(BaseModel): has_key: bool; used: int; cap: int; month: str
class SearchUsageOut(BaseModel): brave: BraveUsageOut
class SourceOut(BaseModel): id: str; url: str; title: str | None; author: str | None; lang: str | None
    published: str | None; status: PageStatus; verdict: SourceVerdict; score: int | None; reason: str | None
GET /research/usage -> SearchUsageOut     # `used` = month_total de la clé en vigueur (0 sans clé)
GET /research/sources?session_id= -> list[SourceOut]   # sources d'une session (table `sources`, 13.3)
```

- `UserSettings` (`settings/schemas.py`) : `search_max_queries: int = Field(12, ge=1, le=50)`, `search_max_pages: int = Field(30, ge=1, le=100)` ; `search_provider_order: list[Literal["searxng", "brave"]]` (1 à 2, sans doublon) ; `search_languages` : codes `^[a-z]{2}$`, 1 à 6, sans doublon ; `preferred_domains` / `excluded_domains` : 50 au plus, normalisés par la même règle que `normalize_domain` (validateur local à `schemas.py`, pas d'import de service), **liste de départ** : privilégiés `["wikipedia.org", "arxiv.org", "github.com", "docs.python.org", "developer.mozilla.org", "pytorch.org", "huggingface.co", "scikit-learn.org"]`, exclus `["pinterest.com", "facebook.com", "instagram.com", "tiktok.com", "linkedin.com"]` (pages derrière connexion, 10.2). Une valeur stockée invalide retombe sur le défaut (règle existante `_parse_stored`).
- Journaux : `search` et `read` journalisent utilisateur, session, fournisseur, statut, code d'erreur et `source_id` ; **jamais** la requête, l'URL, le titre.

- [ ] **Step 1: Write the failing tests**

```python
async def test_query_is_scrubbed_before_any_provider(runtime, searxng_fake, user_named_jane):
    await search(runtime, uid, None, "portfolio Jane Doé jane@x.fr")
    assert searxng_fake.calls == [("portfolio", None)]
async def test_falls_back_to_brave_when_searxng_fails(runtime_with_brave_key): ...   # provider == "brave"
async def test_brave_skipped_without_key(runtime): ...                               # NoSearchProvider, brave jamais construit
async def test_no_provider_left_is_readable(runtime):
    with pytest.raises(NoSearchProvider) as e: ...
    assert e.value.status_code == 503 and "moteur" in e.value.message
async def test_provider_order_from_settings(runtime): ...                            # ["brave", "searxng"]
async def test_excluded_domain_removed_preferred_first(runtime): ...
async def test_query_quota_stops_at_setting(runtime): ...                            # search_max_queries=2 → 3e : WebQuotaReached
async def test_same_query_twice_in_session_counts_once(runtime, searxng_fake):
    a = await search(runtime, uid, sid, "rag"); b = await search(runtime, uid, sid, "rag")
    assert b.replayed and len(searxng_fake.calls) == 1 and await count_queries(sid) == 1
async def test_brave_stops_at_900_per_month(runtime_with_brave_key, usage_at_900): ...  # brave sauté
async def test_brave_cap_is_atomic_under_concurrency(runtime_with_brave_key, usage_at_899):
    await asyncio.gather(*(search(runtime, uid, f"s{i}", "q") for i in range(5)))     # searxng en panne
    assert await month_total(...) == 900
async def test_brave_cap_shared_by_users_with_same_env_key(...): ...
async def test_search_cache_avoids_second_provider_call_within_24h(...): ...

async def test_read_ok_creates_pending_source(runtime, fake_web): ...
async def test_unreadable_page_is_reported_with_reason(runtime, fake_web):
    out = await read(runtime, uid, sid, "https://ex.org/vide")       # FakeWebReader lève UrlUnreadable(NO_TEXT_MESSAGE)
    assert out.status == "unreadable" and out.reason == NO_TEXT_MESSAGE and out.source_id
async def test_forbidden_url_is_unreadable_not_500(runtime, fake_web): ...
async def test_excluded_domain_is_not_read(runtime, fake_web): ...          # fake_web.calls == []
async def test_page_quota_stops_at_setting(runtime): ...
async def test_same_url_twice_in_session_counts_once(runtime, fake_web): ... # 1 lecture, 1 ligne
async def test_cached_page_not_read_again_within_7_days(runtime, fake_web): ...
async def test_unreadable_source_is_never_kept(db): ...                     # score 90 + unreadable → rejected
async def test_logs_never_contain_query_or_url(runtime, caplog):
    await search(runtime, uid, sid, "requete-secrete"); await read(runtime, uid, sid, "https://secret.example/p")
    assert "requete-secrete" not in caplog.text and "secret.example" not in caplog.text

async def test_usage_route_counts_current_month(client): ...                # tests/features/research/test_router.py
async def test_usage_route_isolated_between_users(client, app): ...
async def test_sources_route_lists_session_sources_and_is_isolated(client, app): ...
async def test_settings_rejects_unknown_provider_and_bad_domain(client): ... # 422, valeur reçue non recopiée
async def test_settings_defaults_include_starting_domain_lists(client): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/features/research tests/features/settings -v` → FAIL.
- [ ] **Step 3: Implement** le runtime (ouvert dans le lifespan après la mémoire, sur `app.state.research_providers`), `search`, `read`, `record_verdict`, le routeur, les réglages ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS ; lancer 5 fois `uv run pytest tests/features/research/test_searching.py -k concurrency`.
- [ ] **Step 5: Décision D76** : (1) une « requête » = un appel de `web_search` (replis compris), une « page lue » = une URL distincte de la session (cache compris) ; (2) zéro résultat déclenche le repli ; (3) compteur Brave par empreinte de clé, verrou de processus + transaction ; mois civil UTC ; (4) domaine exclu jamais lu, privilégié en tête de liste et signalé à l'Éclaireur, sans bonus de points ; (5) réglages : bornes, liste de départ (11.4) ; routes `GET /research/usage` et `GET /research/sources` hors 14.2.
- [ ] **Step 6: Commit** — `git commit -m "feat(research): recherche avec repli, lecture avec statut, plafonds de session et Brave"`

---

### Task 3.7 : Back — outils web des agents, Éclaireur et parcours `web_research`

**Zone : back.** Change le contrat OpenAPI (`SourceFoundPayload`).

**Files:**
- Create: `backend/app/agents/tools/web_port.py`, `web_tools.py` ; `backend/app/agents/prompts/scout.md` ; `backend/app/agents/nodes/scout.py` (paquet `nodes/scout/` si > 300 lignes) ; `backend/app/agents/state/web_research.py` ; `backend/app/agents/graphs/web_research.py` ; `backend/app/features/research/service/gateway.py`
- Modify: `backend/app/agents/runtime/events.py`, `deps.py`, `execution.py`, `runner.py`, `lifespan.py` (paramètre `web`), `backend/app/agents/registry.py` (`scout`), `backend/app/agents/graphs/registry.py`, `backend/app/bootstrap.py` (`web_gateway(runtime)`), `backend/app/main.py`, `contracts/openapi.json`, `frontend/src/shared/api/schema.d.ts`
- Test: `backend/tests/agents/tools/test_web_tools.py`, `backend/tests/agents/graphs/test_web_research.py`, `backend/tests/features/research/test_gateway.py`

**Interfaces:**
- Consumes: `search`, `read`, `record_verdict`, `WebQuotaReached`, `QUOTA_CODE` (3.6) ; `memory_write` (phase 2).
- Produces:

```python
# agents/tools/web_port.py — ce dont les agents ont besoin ; branché par bootstrap.web_gateway (contrat 6)
@dataclass(frozen=True)
class WebHit: title: str; url: str; snippet: str; engine: str; published: str | None; preferred: bool
@dataclass(frozen=True)
class WebSearchResult: query: str; provider: str | None; hits: list[WebHit]
@dataclass(frozen=True)
class PageRead: source_id: str; url: str; status: Literal["ok", "unreadable"]; title: str | None; text: str
                author: str | None; date: str | None; lang: str | None; reason: str | None
@dataclass(frozen=True)
class SourceVerdictView: source_id: str; score: int; verdict: Literal["kept", "rejected"]; reason: str
class WebGateway(Protocol):
    async def search(self, user_id: str, session_id: str, query: str, *, lang: str | None = None,
                     time_range: str | None = None, categories: Sequence[str] = ()) -> WebSearchResult
    async def read(self, user_id: str, session_id: str, url: str) -> PageRead
    async def judge(self, user_id: str, session_id: str, source_id: str, *, criteria: dict[str, int],
                    reason: str, summary: str) -> SourceVerdictView
    async def limits(self, user_id: str) -> WebLimits
@dataclass(frozen=True)
class WebLimits: languages: tuple[str, ...]; preferred: tuple[str, ...]; max_queries: int; max_pages: int
NO_WEB: WebGateway   # lève AppError("web_unavailable", …, 503) ; défaut de GraphDeps.web

# agents/tools/web_tools.py — mêmes conventions que memory_tools (tool.called puis tool.result)
async def web_search(deps: GraphDeps, query: str, *, lang: str | None = None, agent: str) -> WebSearchResult
async def web_read(deps: GraphDeps, url: str, *, agent: str) -> PageRead
#   résumé de tool.result : « {n} résultat(s) via {fournisseur} » / « Lue » / « Illisible : {raison} » ;
#   les arguments de tool.called portent la requête NETTOYÉE (renvoyée par la passerelle)
def web_tools_for(deps: GraphDeps, *, agent: str) -> list[BaseTool]
#   `web_search` et `web_read` en StructuredTool ; `web_read` rend au modèle le texte encadré par
#   untrusted(text, f"page {source_id}") avec titre, auteur, date et langue ; une page unreadable
#   rend « Page illisible : {raison}. Ne pas la citer. »

# events.py — SourceFoundPayload complété (champs ajoutés avec défaut : compatible)
class SourceFoundPayload(BaseModel):
    title: str; url: str; author: str | None; date: str | None; lang: str | None; score: int | None
    source_id: str | None = None
    status: Literal["ok", "unreadable"] = "ok"
    verdict: Literal["kept", "rejected"] | None = None
    reason: str | None = None

# nodes/scout.py
AGENT = "scout"
class SearchPlan(BaseModel): queries: list[PlannedQuery] = Field(min_length=1, max_length=6)
class PlannedQuery(BaseModel): text: str = Field(min_length=2, max_length=200); lang: str = Field(pattern=r"^[a-z]{2}$")
class SourceScore(BaseModel):     # bornes = barème 10.3
    authority: int = Field(ge=0, le=30); freshness: int = Field(ge=0, le=20); depth: int = Field(ge=0, le=20)
    author: int = Field(ge=0, le=15); pedagogy: int = Field(ge=0, le=15)
    reason: str = Field(min_length=1, max_length=300); summary: str = Field(min_length=1, max_length=600)
    @property
    def total(self) -> int
MAX_PAGES_PER_RUN = 10   # borné aussi par le plafond de pages restant
PAGE_CHARS_FOR_SCORING = 6000

# graphs/web_research.py
class WebResearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=5)   # pages à lire en plus (essai, contrôle)
# START → plan → search → read → judge → remember → finalize → END ; aucune interruption
```

- **Nœuds** (`nodes/scout.py`, un nœud = une fonction de `GraphDeps`, piège 9.4 respecté : chaque appel externe est idempotent par la passerelle) :
  - `plan` : `agent.started` (« je prépare les requêtes ») ; `structured_call` (niveau `rapide`) → `SearchPlan`, une à trois requêtes par langue de `limits.languages`, tronqué au plafond de requêtes.
  - `search` : `web_search` par requête ; `WebQuotaReached` → arrêt propre des requêtes ; toutes en `search_unavailable` → l'erreur remonte (session `failed`, message français).
  - `read` : URLs uniques des résultats (privilégiés d'abord) puis `input.urls`, au plus `min(MAX_PAGES_PER_RUN + len(urls), pages restantes)` ; `web_read` chacune ; une page `unreadable` émet aussitôt `source.found` (`status="unreadable"`, `reason`, `score=None`) et n'est jamais notée ni citée.
  - `judge` : par page `ok`, `structured_call` → `SourceScore` ; prompt avec titre et texte **encadrés** (`untrusted`), domaines privilégiés signalés ; `deps.web.judge(...)` ; `source.found` avec `score`, `verdict`, `reason`.
  - `remember` : chaque source retenue → `memory_write(kind="source", title, text=summary + "\n" + url, reason="Source retenue par l'Éclaireur (score {n}/100).", tags=[lang])` (4.2 : ne pas la rechercher deux fois ; doublon = déjà en mémoire, rien d'écrit).
  - `finalize` : résumé « {k} source(s) retenue(s), {r} écartée(s), {u} illisible(s). »
- `AgentWebGateway(runtime: ResearchRuntime)` dans `features/research/service/gateway.py` : ouvre sa session de base par appel, convertit `SearchOutcome` / `PageOutcome` en types du port ; `bootstrap.web_gateway(runtime) -> WebGateway` ; `agent_runtime(..., *, memory=, web=)`.
- Agent `AgentSpec(name="scout", tier="rapide")` (slug déjà connu du front).

- [ ] **Step 1: Write the failing tests**

```python
async def test_web_read_tool_frames_page_text_as_untrusted(deps_with_fake_web): ...
async def test_web_read_tool_says_unreadable_must_not_be_cited(...): ...
async def test_web_search_tool_emits_scrubbed_query_in_tool_called(emitted, ...): ...

async def test_web_research_emits_scored_and_unreadable_sources(test_runtime, fake_llm, fake_search, fake_web):
    # plan → 2 requêtes ; 3 pages : A (score 82), B (score 41), C illisible
    sid = await start("web_research", {"query": "attention multi-têtes"})
    await wait_status(sid, "completed")
    found = [e.payload for e in await all_events(sid) if e.type == "source.found"]
    assert {(f["status"], f["verdict"]) for f in found} == {("ok", "kept"), ("ok", "rejected"), ("unreadable", None)}
    assert next(f for f in found if f["verdict"] == "kept")["score"] == 82
    assert next(f for f in found if f["status"] == "unreadable")["reason"]
async def test_kept_source_written_to_memory_as_source(...): ...         # memory.written kind "source"
async def test_extra_urls_are_read_and_flagged(...): ...                  # input urls → source.found
async def test_scout_prompt_frames_page_text_and_title_as_untrusted(fake_llm_recording, ...):
    assert "<<<CONTENU_NON_FIABLE" in prompt and prompt.count("<<<FIN_CONTENU_NON_FIABLE>>>") >= 1
async def test_score_is_clamped_by_schema(...): ...                       # authority=45 refusé → 2 essais puis échec lisible
async def test_web_research_stops_at_query_quota(...): ...                # search_max_queries=1 : 1 requête, session completed
async def test_web_research_fails_readably_when_search_is_down(...):
    assert row.status == "failed" and "moteur" in row.error["message"]
async def test_web_research_replay_does_not_duplicate_sources(...):
    # arrêt après `read` (recover_on_startup) puis reprise : lignes `sources` et appels de recherche inchangés
async def test_gateway_isolated_between_users(...): ...
```

- [ ] **Step 2: Run** — `uv run pytest tests/agents tests/features/research -v` → FAIL.
- [ ] **Step 3: Implement** le port, les outils, la passerelle, le prompt (barème 10.3 recopié, 60 pour retenir, encadrement `_shared/untrusted.md`, « une affirmation cite une source lue »), les nœuds, le graphe, le câblage ; régénérer le contrat.
- [ ] **Step 4: Verify** — commandes de contrôle back → PASS.
- [ ] **Step 5: Décision D77** : (1) port `WebGateway` (contrat 6), comme `MemoryGateway` ; (2) note sur 100 calculée par le code à partir de 5 critères bornés (le modèle ne donne pas le total), seuil 60 ; (3) `SourceFoundPayload` complété (`source_id`, `status`, `verdict`, `reason`) : 10.3 exige l'affichage des écartées avec la raison et 18.1 « page illisible signalée » ; (4) 18e parcours `web_research` (banc d'essai, hors 9.2, réutilisé par le Conseil en phase 4), entrée `urls` facultative ; (5) sources retenues écrites en mémoire `source` ; repérage des praticiens (personnes) laissé à la phase 4.
- [ ] **Step 6: Commit** — `git commit -m "feat(agents): outils web, Éclaireur et parcours web_research"`

---

### Task 3.8 : Front — reprise du suivi de l'Archiviste et `SourcesPanel`

**Zone : front.** Après 3.1 (contrat). `SourcesPanel` est présentationnel (types de vue locaux) : il ne dépend pas de 3.7.

**Files:**
- Create: `frontend/src/features/memory/hooks/useRunningLearnings.ts` (+ test) ; `frontend/src/shared/session-ui/SourcesPanel/SourcesPanel.tsx`, `SourcesPanel.test.tsx`, `index.ts` ; `frontend/src/shared/session-ui/SourceCard/SourceCard.tsx`, `SourceCard.test.tsx`, `index.ts` ; `frontend/src/shared/session-ui/sourceTypes.ts`
- Modify: `frontend/src/features/memory/api.ts` (`fetchRunningLearnings`), `hooks/useDocumentActions.ts`, `pages/DocumentsPage/DocumentsPage.tsx` (+ test), `frontend/src/shared/session-ui/index.ts`, `frontend/src/shared/i18n/messages/session.ts`

**Interfaces:**
- Produces:

```ts
// features/memory/api.ts — GET /sessions?graph=learned_document&status=running
export async function fetchRunningLearnings(signal?: AbortSignal): Promise<{ documentId: string; sessionId: string }[]>
//   sessions dont subject_type === "document" et subject_id non nul
// hooks/useRunningLearnings.ts — TanStack Query, une lecture au montage (pas d'interrogation périodique)
export function useRunningLearnings(): { data: { documentId: string; sessionId: string }[] | undefined; ... }
// useDocumentActions : les sessions en cours reçues complètent `learnings` (sans écraser une entrée locale)

// shared/session-ui/sourceTypes.ts
export interface SourceView { id: string; url: string; title: string; author: string | null; date: string | null;
  lang: string | null; score: number | null; status: "ok" | "unreadable"; verdict: "kept" | "rejected" | null;
  reason: string | null }
export interface QueryView { id: string; text: string; lang: string | null; summary: string | null; ok: boolean | null }
export interface SourcesViewModel { queries: QueryView[]; kept: SourceView[]; rejected: SourceView[]; unreadable: SourceView[] }
// SourcesPanel({ model, pending }: { model: SourcesViewModel; pending: boolean })
//   trois blocs « Retenues », « Écartées », « Illisibles » + liste « Requêtes lancées » ; vide → état vide ;
//   `pending` → « L'Éclaireur cherche… » annoncé (aria-live polite)
// SourceCard({ source }: { source: SourceView })
//   titre en lien (target _blank, rel "noopener noreferrer") SAUF une illisible (texte, jamais un lien) ;
//   score « 82/100 », auteur, date, langue ; raison affichée pour écartée et illisible
```

- [ ] **Step 1: Write the failing tests**

```ts
it("DocumentsPage: after a reload, a running Archiviste session is followed again", async () => {
  // GET /sessions?graph=learned_document&status=running → [{ id: "s1", subject_type: "document", subject_id: "d1", … }]
  render(<DocumentsPage />, { wrapper });
  expect(await screen.findByLabelText("Progression de « Cours NLP »")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Déjà appris/ })).toBeDisabled();
});
it("ignores running sessions of other subjects", async () => { /* subject_type "goal" ignoré */ });
it("SourcesPanel groups kept, rejected and unreadable sources", () => {
  render(<SourcesPanel model={model} pending={false} />);
  expect(within(screen.getByRole("region", { name: "Retenues" })).getByText("82/100")).toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "Écartées" })).getByText("Contenu trop superficiel.")).toBeInTheDocument();
});
it("SourceCard never links an unreadable page", () => {
  render(<SourceCard source={{ ...unreadable }} />);
  expect(screen.queryByRole("link")).toBeNull();
  expect(screen.getByText("Page illisible : aucun texte principal trouvé.")).toBeInTheDocument();
});
it("SourcesPanel shows the queries that were sent", () => { /* « rag evaluation » (en) */ });
```

- [ ] **Step 2: Run** — `cd frontend && pnpm vitest run src/features/memory src/shared/session-ui` → FAIL.
- [ ] **Step 3: Implement** la lecture des sessions en cours, la fusion dans `learnings`, les deux composants et leurs textes (`session.sources.*`).
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck` → PASS.
- [ ] **Step 5: Décision D78** (dans le rapport ; le contrôleur la recopie) : reprise par `GET /sessions` filtré, sans interrogation ; `SourcesPanel` dans `shared/session-ui/` (D9, réutilisé par le Conseil) ; une source illisible n'est jamais un lien.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): suivi de l'Archiviste repris, panneau des sources"`

---

### Task 3.9 : Front — composants des réglages de recherche et de l'essai

**Zone : front.** Présentationnels seulement (aucun appel d'API) : réalisable avant le contrat de 3.6 et 3.7.

**Files:**
- Create (un dossier par composant, avec test et `index.ts`) : `frontend/src/features/settings/components/LanguagePicker/`, `DomainListEditor/`, `ProviderOrderEditor/`, `SearchCapsFields/`, `BraveUsageMeter/` ; `frontend/src/features/research/components/ResearchBenchForm/`, `frontend/src/features/research/components/viewTypes.ts` ; `frontend/src/shared/i18n/messages/research.ts`
- Modify: `frontend/src/features/settings/components/viewTypes.ts`, `frontend/src/shared/i18n/messages/settings.ts`, `frontend/src/shared/i18n/fr.ts` (ligne `research`)

**Interfaces:**
- Produces:

```ts
// settings/components/viewTypes.ts (ajouts)
export type SearchProviderName = "searxng" | "brave";
export interface SearchSettingsView { languages: string[]; preferred: string[]; excluded: string[];
  order: SearchProviderName[]; maxQueries: number; maxPages: number }
export interface BraveUsageView { hasKey: boolean; used: number; cap: number; month: string }
// LanguagePicker({ value, onChange }) — fr, en, es, de, it, pt ; au moins une langue (la dernière ne se décoche pas)
// DomainListEditor({ label, value, onChange, max = 50 }) — ajout par champ + bouton, retrait par bouton ;
//   saisie normalisée (minuscules, schéma, chemin, « www. » retirés) ; invalide ou doublon → message en ligne
// ProviderOrderEditor({ value, braveAvailable, onChange }) — monter / descendre ; Brave grisé avec
//   « Ajoutez une clé Brave dans Modèles et clés » si braveAvailable faux
// SearchCapsFields({ maxQueries, maxPages, onChange }) — bornes 1–50 et 1–100
// BraveUsageMeter({ usage }) — « 312 / 900 requêtes en novembre 2026 » ; sans clé : « Brave inactif (aucune clé) »
// research/components/ResearchBenchForm({ onSubmit, busy }) — requête (2 à 300 caractères) et jusqu'à
//   5 adresses supplémentaires (http(s)) ; onSubmit({ query, urls })
```

- [ ] **Step 1: Write the failing tests** — un test par composant, par exemple :

```ts
it("DomainListEditor normalizes and rejects duplicates", async () => {
  await user.type(screen.getByLabelText("Ajouter un domaine"), "https://www.Python.org/doc{Enter}");
  expect(onChange).toHaveBeenLastCalledWith(["python.org"]);
  // re-saisie de python.org → « Ce domaine est déjà dans la liste. »
});
it("LanguagePicker keeps at least one language", async () => { /* décocher la dernière : désactivé */ });
it("ProviderOrderEditor moves Brave first", async () => { expect(onChange).toHaveBeenCalledWith(["brave", "searxng"]); });
it("BraveUsageMeter shows the monthly count", () => { expect(screen.getByText("312 / 900 requêtes en novembre 2026")).toBeInTheDocument(); });
it("ResearchBenchForm refuses a non http(s) address", async () => { /* ftp://… → message en ligne, onSubmit non appelé */ });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/features/settings/components src/features/research` → FAIL.
- [ ] **Step 3: Implement** les composants et les textes.
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck` → PASS.
- [ ] **Step 5: Décision D79** (dans le rapport) : six langues proposées, normalisation des domaines identique au back, Brave grisé sans clé.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): composants des réglages de recherche et de l'essai"`

---

### Task 3.10 : Front — pages « Recherche web » et « Essai de recherche »

**Zone : front.** Après 3.7 (contrat complet).

**Files:**
- Create: `frontend/src/features/settings/pages/SearchSettingsPage/` (page, test, `index.ts`), `frontend/src/features/settings/hooks/useSearchUsage.ts` (+ test) ; `frontend/src/features/research/manifest.ts` (+ test), `api.ts`, `hooks/useResearchRun.ts` (+ test), `pages/ResearchBenchPage/` (page, test, `index.ts`) ; `frontend/src/shared/session-ui/sourcesFromEvents.ts` (+ test)
- Modify: `frontend/src/features/settings/manifest.ts`, `api.ts` (`fetchSearchUsage`), `userSettings.ts` (nouveaux champs + `toSearchSettingsView` / `withSearchSettings`), `frontend/src/app/registry.ts` (ligne `researchManifest`), `frontend/src/shared/session-ui/index.ts`

**Interfaces:**
- Produces:

```ts
// shared/session-ui/sourcesFromEvents.ts — réutilisé par le Conseil (phase 4)
export function sourcesFromEvents(events: SessionEvent[]): SourcesViewModel
//   tool.called(web_search) → QueryView (args.query, args.lang) ; tool.result du même call_id → summary, ok ;
//   source.found → SourceView (id = source_id ?? url), rangée selon status / verdict ; dernier événement
//   d'une même source gagne

// settings/manifest.ts — nav ajoutée : { section: "settings", labelKey: "settings.search.navLabel",
//   path: "/reglages/recherche", order: 2 }
// research/manifest.ts
export const researchManifest: FeatureManifest = { id: "research",
  routes: [{ path: "reglages/recherche/essai", Component: ResearchBenchPage }],
  nav: [{ section: "settings", labelKey: "research.nav.bench", path: "/reglages/recherche/essai", order: 3 }] };
// research/api.ts : startResearch({ query, urls }) → startSession("web_research", { query, urls })
// useResearchRun : sessionId courant (dans l'URL `?session=<id>` pour survivre au rechargement)
```

Pages :
- `SearchSettingsPage` : `LanguagePicker`, deux `DomainListEditor` (privilégiés, exclus), `ProviderOrderEditor` (`braveAvailable` = `usage.brave.has_key`), `SearchCapsFields`, `BraveUsageMeter` ; « Enregistrer » = `PUT /settings` complet (`buildUserSettings` étendu, jamais `...settings`) ; succès annoncé, erreur en ligne avec la saisie gardée.
- `ResearchBenchPage` : `ResearchBenchForm` → session `web_research` → `SessionStatusBar`, `CostBadge`, `SourcesPanel` (`sourcesFromEvents(stream.events)`, `pending` tant que `running`), message de `run.failed` ; lien « Nouvel essai ».
- Chaque page : chargement, erreur avec « Réessayer », état vide avec action.

- [ ] **Step 1: Write the failing tests** (MSW, `queryWrapper`, faux socket)

```ts
it("sourcesFromEvents classifies kept, rejected and unreadable", () => {
  expect(sourcesFromEvents([toolCalled("c1", "web_search", { query: "rag", lang: "en" }), toolResult("c1", true, "8 résultat(s) via searxng"),
    sourceFound({ source_id: "a", score: 82, verdict: "kept" }), sourceFound({ source_id: "c", status: "unreadable", reason: "Page injoignable." })]))
    .toMatchObject({ queries: [{ text: "rag", summary: "8 résultat(s) via searxng" }], kept: [{ id: "a" }], unreadable: [{ id: "c" }] });
});
it("SearchSettingsPage saves languages and domains with a full PUT", async () => {
  // ajoute « es » et le domaine exclu « example.com » → corps PUT : search_languages ["fr","en","es"], excluded_domains contient "example.com",
  // et garde tiers, availability… inchangés
});
it("SearchSettingsPage greys Brave without a key", async () => { /* usage.brave.has_key false */ });
it("ResearchBenchPage streams scored sources and flags an unreadable page", async () => {
  // POST /sessions → s1 ; faux socket : tool.called, tool.result, source.found ×3, run.completed
  expect(await screen.findByText("82/100")).toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "Illisibles" })).getByText("Page illisible : aucun texte principal trouvé.")).toBeInTheDocument();
});
it("ResearchBenchPage resumes the session given in ?session= after a reload", async () => { ... });
it("declares the research bench under Réglages", () => { expect(researchManifest.nav?.[0].path).toBe("/reglages/recherche/essai"); });
```

- [ ] **Step 2: Run** — `pnpm vitest run src/features/settings src/features/research src/shared/session-ui src/app` → FAIL.
- [ ] **Step 3: Implement** api, hooks, pages, manifestes, ligne du registre, `sourcesFromEvents`.
- [ ] **Step 4: Verify** — `pnpm vitest run && pnpm lint && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 5: Décision D80** (dans le rapport) : deux entrées de navigation sous Réglages (15.1 ne liste pas la recherche ; 11.4 en fait des réglages), feature front `research` (même nom que le back), session dans l'URL, `sourcesFromEvents` partagé.
- [ ] **Step 6: Commit** — `git commit -m "feat(front): réglages de recherche et essai de recherche"`

---

### Task 3.11 : Contrôle de fin de phase (contrôleur)

**Zone : back (script) puis contrôleur.** L'implémenteur écrit seulement le script et son test ; le contrôleur fait la revue complète (avant cette tâche), le contrôle sous Docker, le parcours dans le navigateur, le tag, le push et le bilan.

**Files:**
- Create: `backend/scripts/check_phase3.py`
- Test: `backend/tests/scripts/test_check_phase3.py`

**Interfaces:**
- Produces:

```python
UNREADABLE_PROBE = "https://example.com/"   # page publique sans texte principal (≥ 200 caractères absents)
async def run_check(client: httpx.AsyncClient, *, query: str = "mécanisme d'attention transformeur",
                    extra_urls: Sequence[str] = (UNREADABLE_PROBE,), timeout_s: float = 300.0) -> list[str]
#   étapes, chacune lève CheckFailed(message français), renvoie les étapes réussies :
#   1. GET /health : searxng et gotenberg ok
#   2. POST /sessions {graph: "web_research", input: {query, urls: extra_urls}}
#   3. GET /sessions/{id} jusqu'à completed
#   4. GET /research/sources?session_id= : au moins une source status ok avec un score, et une
#      source status unreadable avec une raison
#   5. GET /research/usage répond
def main() -> None   # python -m scripts.check_phase3 --api http://localhost:8000 ; code de sortie 0/1
```

- [ ] **Step 1: Write the failing test** — `test_check_runs_against_the_app(app, client)` : fournisseurs factices (`FakeSearch`, `FakeWebReader` où `UNREADABLE_PROBE` est illisible), faux LLM scripté, santé remplacée par une réponse OK → `["santé", "lancement", "fin", "sources", "usage"]`.
- [ ] **Step 2: Run** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS ; suites complètes back et front → PASS ; `uv run python -m pre_commit run --all-files` → OK.
- [ ] **Step 5: Commit** — `git commit -m "chore(research): script de contrôle de fin de phase 3"`
- [ ] **Step 6: Contrôle sous Docker (contrôleur)**
  1. `docker compose up -d --build` ; `GET /api/v1/health` au vert (searxng, gotenberg compris).
  2. `cd backend && uv run python -m scripts.check_phase3 --api http://localhost:${BACKEND_PORT:-8000}` → 5 étapes réussies, avec le vrai SearXNG et le vrai Gotenberg (une clé LLM valide pour l'Éclaireur).
  3. Navigateur, `/reglages/recherche` : ajouter l'espagnol, un domaine exclu, enregistrer, recharger → conservé ; sans clé Brave, Brave grisé.
  4. Si une clé Brave existe : la saisir dans « Modèles et clés », « Tester » → OK, 4 derniers caractères seulement ; mettre Brave en tête de l'ordre, lancer un essai → compteur Brave augmenté ; remettre SearXNG en tête.
  5. `/reglages/recherche/essai`, requête réelle : les requêtes lancées, les sources retenues (score ≥ 60) et écartées (raison) arrivent en direct ; une adresse supplémentaire sans texte (`https://example.com/`) est signalée « Illisible » et n'est pas un lien (**critère de fin de phase**). Une page rendue en JavaScript (application monopage publique) est lue par le repli Gotenberg.
  6. Relancer la même requête dans les 24 h : aucun nouvel appel au moteur (cache) ; une page déjà lue sort du cache.
  7. Pendant un essai : `docker compose restart backend` → la session reprend et finit, sans source en double.
  8. `docker compose stop searxng` : sans clé Brave, l'essai échoue avec un message français ; relancer SearXNG.
  9. Mémoire : un gros PDF importé reste lisible ; « Déjà appris » puis rechargement de la page → progression de l'Archiviste toujours affichée, un second clic ne lance pas de seconde session.
  10. `docker compose logs backend | grep -E "https?://|<requête de l'essai>"` → aucune ligne (journaux sans URL ni requête).
  11. Non-régression : `/demo` (débat, question, reprise) et `/memoire` (recherche).
- [ ] **Step 7: Décision D81** (constats du contrôle), bilan `docs/superpowers/bilans/phase-3.md`, commit, tag `phase-3`, `git push` et `git push origin phase-3`.

---

## Auto-revue

- **Couverture de la spec** : 10.1 (`SearchProvider`, SearXNG défaut, Brave si clé, ordre réglable, JSON, moteurs, risque de blocage → cache et plusieurs moteurs) → 3.3, 3.5, 3.6 · 10.2 (httpx + trafilatura, repli Gotenberg, PDF, YouTube inchangé, GitHub, arXiv, statut `ok`/`unreadable`, jamais citée, pas de contournement de connexion, cache 7 jours, 15 s, 1 req/s/domaine) → 3.2, 3.4, 3.5, 3.6, 3.7 · 10.3 (barème 30/20/20/15/15, seuil 60, langues fr/en, domaines, requêtes et sources retenues ou écartées affichées) → 3.6, 3.7, 3.8, 3.10 · 10.4 (12 requêtes, 30 pages, réglables) → 3.6, 3.9, 3.10 · 11.3 (clé Brave, 900 par mois) → 3.3, 3.6 · 11.4 (langues, domaines, liste de départ) → 3.6, 3.9, 3.10 · 12.3 (`search/`, `pdf/gotenberg.py`, `web/github.py`, `web/arxiv.py`, `tools/web_tools.py`) → 3.2, 3.3, 3.4, 3.7 · 13.3 `sources`, 13.6 `web_cache` → 3.5 · 17.2 (isolation, journaux sans URL ni requête) → 3.5, 3.6 · 17.3 (nom, email, téléphone retirés) → 3.5, 3.6 · 17.4 (contenu non fiable, adresses privées, Gotenberg) → 3.2, 3.4, 3.7 · 18.1 (critère de fin) → 3.7 `test_web_research_emits_scored_and_unreadable_sources`, 3.10, 3.11 · bilan phase 2 (`subject_id` et reprise front, DoS PDF, titre encadré, M2) → 3.1, 3.2, 3.8.
- **Hors périmètre volontaire** : repérage de 5 à 10 praticiens par objectif (personnes, `sources.kind = "person"`) et citations numérotées du Conseil (phase 4, qui réutilise `web_research`, l'Éclaireur et `SourcesPanel`) ; rendu de `source.found` dans `DebateFeed` (phase 4) ; détection de langue propre (on garde celle de trafilatura) ; purge planifiée de `web_cache` (`purge_expired` existe, branchée sur APScheduler en phase 8) ; mineurs de la phase 2 triés « laisser » (M1, M4, M5, M6).
- **Cohérence des noms** : `SearchProvider` / `SearchResult` / `SearchUnavailable` (3.3) utilisés par `rank_results` (3.5) et `search` (3.6) ; `ResearchProviders` (3.3) lu par `ResearchRuntime` (3.6) puis `AgentWebGateway` (3.7) ; `PageRenderer` / `RenderFailed` (3.2) consommés par `TrafilaturaWebReader` (3.4) ; `PageStatus`, `SourceVerdict`, `SOURCE_THRESHOLD` définis une fois dans `app/db/models/research.py` (3.5) ; `WebQuotaReached` / `QUOTA_CODE` (3.6) attrapés par les nœuds de l'Éclaireur (3.7) ; `SourceFoundPayload.source_id/status/verdict/reason` (3.7) lus par `sourcesFromEvents` (3.10) vers `SourceView` (3.8) ; slug `scout` identique dans `AGENTS`, `agentColors.ts`, `messages/agents.ts`.
- **Décisions** : D71 à D81 réservées, une par tâche ; chaque écart à la spec y est consigné : URL et non HTML envoyée à Gotenberg (D72), 3 s pour arXiv (D74), tables `web_queries` et `search_usage` et TTL de 24 h (D75), lecture `month_total` sans `user_id` (D75), routes `GET /research/usage` et `GET /research/sources` et liste de départ des domaines (D76), parcours `web_research` et `SourceFoundPayload` complété (D77), entrées de navigation sous Réglages (D80).
