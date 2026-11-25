# Tremplin in English, everywhere — design

Date: 2026-11-24. Branch: `claude/english` (from `main` at `814a63dc`, pushed to `origin/main` the same day).

## Intent

January wants Tremplin entirely in English: the interface, everything the agents generate, the MCP server, the
README, the code (comments, docstrings, tests), the documentation, and also the stored codes and the URLs.
French remains only in git history and in data already stored by users (lessons, notes, programs), which is not
translated. Quote: "tout doit être en anglais", "EVERYTHING TOUT TOUT TOUT".

## Goals

- English UI: `fr.ts` becomes `en.ts`, every message file translated, English date and number formats.
- Everything generated is English: agent prompts ask for English, error messages (`{"error": {"code", "message"}}`),
  notifications, activity events, PDF/ICS/email templates, MCP descriptions, notices and limit messages.
- English stored codes (task types, resource types, levels, statuses, kinds, lesson section headers…) with Alembic
  data migrations that convert existing rows, and the OpenAPI contract and `schema.d.ts` regenerated.
- English URLs on the front end, with redirects from the old French paths so bookmarks and stored links still work.
- English README with a detailed "What Tremplin does" section and Mermaid diagrams before the setup section.
- English comments, docstrings, test names, AGENTS.md, CLAUDE.md, SPEC.md, DECISIONS.md and `docs/**`.

## Non-goals

- Translating user data already stored (lesson bodies, notes, CVs, programs): it stays as written.
- A bilingual UI: French is replaced, not kept as an option.

## Anti-goals

- A broken app between steps: every step ends with the targeted tests, lint, typecheck and the import contracts green.
- A code value renamed without its data migration, contract regeneration and front update in the same step.

## Approaches considered

1. **One pass per layer** (UI texts, then prompts, then codes, then comments): simple to brief, but the codes step
   touches every feature at once. Chosen for the texts (independent files, parallel agents).
2. **One pass per feature folder, both sides**: each agent owns `backend/app/features/<f>` and
   `frontend/src/features/<f>` with their tests. Chosen for codes, URLs, comments and tests, run one agent at a time
   after the parallel window (January: one agent at a time to save credit).
3. Mechanical translation by script: rejected, quality too low for UI and prompts.

## Steps

1. Parallel window (done 24/11): README, inventories of codes and URLs, the 84 message files, the 47 prompts, MCP.
2. Make the tests green again after step 1 (front tests asserting French strings, back tests on prompts and MCP).
3. Codes: per feature, rename values, Alembic data migration, regenerate `openapi.json` and `schema.d.ts`, update front.
   The lesson `##` section headers in `checks.py` move to English together with the lesson standard and the PDF.
4. URLs: English route table, redirects from French paths, back-end links (`activity` events, MCP outputs).
5. Back-end messages: error messages, notifications, templates; AGENTS.md rule "message en français" becomes English.
6. Comments, docstrings, test names, per feature folder.
7. Documentation: AGENTS.md, CLAUDE.md, SPEC.md, DECISIONS.md (+ a new decision recording the switch), `docs/**`.
8. Merge into `main` and push when the suites are green.

## Constraints

AGENTS.md rules still apply (contract first, Alembic only, isolation tests, files ≤ 300 lines, no secrets, commits by
explicit paths with hooks). Smart App Control: tools run through `node` and the signed uv Python.

## Left to the builder

The exact English wording, the English names of codes and paths (from the inventories), the order of features.
