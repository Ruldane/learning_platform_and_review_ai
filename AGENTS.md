# Tremplin

Tremplin is a local learning and career platform run by AI agents. It serves a primary user
and supports a few accounts in Google sign-in mode. The Docker stack runs FastAPI, async
SQLAlchemy, SQLite, Alembic, LangGraph and Qdrant on the backend, and React 19, TanStack Query,
MSW and Vitest on the frontend.

The backend and frontend share only `contracts/openapi.json`. Read `SPEC.md` for product
requirements and `DECISIONS.md` for choices and deviations. Agents developing the repository
follow this file. Agents operating Tremplin through MCP read `docs/mcp/AGENTS.md` for connection
setup, tokens, access levels, limits and rules of conduct.

## Repository map

- Backend features live in `backend/app/features/<feature>/`. The router calls the service,
  which calls the repository. Each feature has schemas and an MCP declaration in `mcp.py`.
  `features/registry.py` defines `FEATURE_ROUTERS` and `MCP_FEATURES`.
- The backend has Markdown agent prompts and Python nodes under `backend/app/agents/`. The
  `GRAPHS` registry is in `agents/graphs/registry.py`. Provider ports and implementations live in
  `providers/`, the MCP engine in `mcp/`, and `JOBS` in `scheduler/`. The backend also has
  `realtime/`, `db/`, `alembic/`, `scripts/` and `tests/`.
- Frontend features use the same names in `frontend/src/features/`. API, i18n, realtime, session
  UI and shared utilities live in `src/shared/`. `src/app/registry.ts` lists feature manifests,
  and `e2e/` contains the Playwright flows.
- `sandbox/` contains the IDE sandbox image and launcher. Project records live under
  `docs/superpowers/{plans,bilans,recette}` and `DECISIONS.md`.
- Write implementation plans in `docs/superpowers/plans/`. For the resumed work, use one plan
  per batch of ten phases, with a section per phase and a link to the detailed phase 11 plan.
  Write each section before its code. The master plan defines the architecture in section 1
  and the batches in section 7 (D232).

## Architecture

- Use one folder per feature on each side, with matching names. Add a feature through its
  folder and one entry in each registry (`FEATURE_ROUTERS`, `MCP_FEATURES`, `GRAPHS`,
  `JOBS` and `app/registry.ts`). Keep the change inside the feature.
- Routers handle requests and responses, services hold business logic, and repositories access
  the database. A backend feature may import only the service of another feature.
- The import contracts in `backend/pyproject.toml` are blocking. Features and agents must avoid
  concrete `app.providers` implementations. Only `app.main` imports `app.bootstrap*`.
  `app.mcp` must avoid importing features, and `app.features` must avoid `app.scheduler`.
- Obtain a language model through `get_chat_model(tier)`. Access external services through
  provider ports.
- Use one frontend component per folder (`X/X.tsx`, `X.test.tsx`, `index.ts`).
  `components/` receives props and callbacks. Wire API modules, hooks and stores in `pages/`.
  Frontend features cannot import each other. `shared/` cannot import `features/` or `app/`.
  ESLint enforces these boundaries.
- Keep files to 300 lines and functions to 50 lines. The backend uses
  `scripts/check_file_length.py`, and the frontend uses ESLint. Split a growing module into a
  package and preserve its exports.
- **Contract first.** When a route or schema changes, regenerate `contracts/openapi.json` and
  then `frontend/src/shared/api/schema.d.ts`. Generate API types from the contract.
- Every table has a text UUID `id`, `user_id`, `created_at` and `updated_at`. Change the schema
  with Alembic. Filter every repository query by `user_id`. Add a two-user isolation test in
  `backend/tests/isolation/` for every new route.
- Declare each new route in `features/<feature>/mcp.py` with its action and level (1–3), or list
  the reason for excluding it. `backend/tests/mcp/test_coverage_guard.py` enforces coverage.
  `python -m scripts.mcp_levels` lists the levels. Keep level 4 operations private, including
  keys, authentication, model settings and MCP token management.
- Keep interface text in English in `frontend/src/shared/i18n/messages/*.ts`. The `en.ts` module
  assembles the messages. Components reference their keys.

## Security and data

- Never read, display, copy or commit `.env`.
- Reveal only the last four characters of an API key in a response. Keep keys out of logs.
- Return errors as `{"error": {"code", "message", "details"}}` with a message in English.
  Keep the original input out of 422 responses.
- Limit logs to identifiers, counts, codes and durations. Keep user text, email addresses,
  links and MCP call contents out of logs.
- Use fake providers and scripted models in tests. Keep real model and network calls out of
  tests. HTTP requests hand off agent work immediately and return a `session_id`.
- Keep Docker sockets, network access, host mounts and secrets out of the IDE sandbox.
  Agents and Claude propose fixes for user code and apply them only after acceptance.

## Commands

Run backend commands from `backend/`.

```bash
uv sync
uv run pytest tests/<folder> -q           # Target affected folders. The full suite takes ~40 min.
uv run ruff check . && uv run ruff format --check .
uv run python -m mypy app                 # Strict typing
uv run lint-imports
uv run python -m scripts.export_openapi   # Regenerate the contract. Use --check to verify it.
uv run python scripts/check_file_length.py <files.py>
uv run alembic upgrade head
uv run python -m scripts.mcp_levels       # List MCP levels
```

Run frontend commands from `frontend/`. See the Windows notes if `pnpm` is blocked.

```bash
pnpm test                       # A single file: pnpm test src/features/ide/toView.test.ts
pnpm lint
pnpm typecheck
pnpm gen:api                    # Generate schema.d.ts from ../contracts/openapi.json
pnpm gen:api:check              # Check that schema.d.ts matches the contract
pnpm build
pnpm e2e                        # Playwright flows 1–4. playwright.auth.config.ts covers flow 5.
pnpm e2e:docker                 # Run the same flows against the backend image
```

Run Docker commands from the repository root.

```bash
docker build -t learning_career_platform-backend:latest backend
docker compose up -d --no-build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Build the frontend and sandbox images the same way. Tag the sandbox image
`learning_career_platform-sandbox:latest`. The development Compose override enables hot reload.

The hooks in `.pre-commit-config.yaml` run Ruff, length checks, mypy, import-linter, OpenAPI and
generated type checks, ESLint and TypeScript. The default test selection excludes `live` and
`sandbox_live`. The latter runs escape tests against a real sandbox container.

## Workflow

- Start with a failing test, then implement the behavior that makes it pass.
- Cover changed behavior, user isolation and affected Playwright flows. Review each phase and
  conduct one or two overall reviews at the end of its batch (D232).
- Record decisions and deviations from the spec as a new `Dnnn` entry at the end of
  `DECISIONS.md`. Include the date, subject, decision and reason.
- Stage explicit paths with `git add <paths>` and keep all pre-commit hooks enabled. Fix hook
  failures at the source.
- Keep intermediate commits local. Push to GitHub after every twenty completed and tested
  phases starting with phase 11, leaving phase 12 aside. Use the repository identity
  `Ruldane <l.nizzoli@gmail.com>` (D231).
- Use AA contrast, full keyboard access, visible focus and a purposeful focus target after each
  action. Respect `prefers-reduced-motion`.
- Run real model or container checks only in a disposable stack named
  `learning_career_platform-check<N>-*`. Remove that stack after the check and keep regular
  volumes and containers, including those from other projects, untouched.

## Windows workstation notes

- If Smart App Control blocks `pnpm.exe`, Playwright Chromium or the virtual environment's
  `python.exe`, run the frontend tools with Node. From the repository root use
  `node frontend/scripts/run-tool.mjs lint|typecheck` or
  `node frontend/scripts/check-api-types.mjs`. From `frontend/` use
  `node node_modules/vitest/vitest.mjs run <paths>`.
- Run Playwright on Edge using a temporary untracked config and remove it when done.
- Preserve the pre-commit setup that uses uv's signed Python. Running `pre-commit install`
  overwrites it.
- If `docker compose build` requires read permission, build with `docker build` directly.
- Report a blocked executable and wait for the user. Leave Windows security settings intact.
