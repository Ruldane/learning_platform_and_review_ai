# Offers Chat Implementation Plan

> **For agentic workers:** Use executing-plans and complete the tasks in order with one agent.

**Goal:** Open a persistent, multi-chat assistant about job postings from the Offers page.

**Architecture:** Add an Offers scope to the existing conversation graph and storage.
Build account-scoped references from postings, applications, contacts, and skills gaps.
Mount the chat in a modal through the front-end feature registry.

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph, React, TanStack Query, Radix Dialog, MSW, Vitest.

**Spec:** [Offers chat design](../specs/2026-11-24-offers-chat-design.md)

## Constraints

- Use saved Tremplin data. Send necessary excerpts to the configured conversation model.
- Keep the API asynchronous and limit the context within the current turn and session budgets.
- Follow AGENTS.md for account isolation, feature interfaces, tests, OpenAPI, and commits.
- Add the entry point at `/carriere/offres`. The URL migration carries it to the English page.

## Review focus

- A chat identifier copied from another account or chat scope returns 404.
- Retrying a send with the same request identifier returns the original session.
- A posting with no linked application and no known contact remains answerable as unknown.
- A follow-up about a previously cited older offer finds that offer again.
- Closing the dialog during a reply preserves the turn and restores focus to the page.

### Task 1. Persist and run Offers conversations

- [ ] In `backend/tests/isolation/test_offers_chat.py`, exercise two accounts and two Offers chats.
  Assert creation returns 201, reading another user's thread or a Brain thread returns 404,
  sending returns 202, and duplicate request IDs return the same session ID.
- [ ] Run the isolation file before implementation and confirm the unimplemented route fails.
- [ ] In `backend/app/features/conversations/offers.py`, implement
  `create_offers_chat(db, user_id)`, `read_offers_chat(db, user_id, conversation_id)`, and
  `ask_offers_chat(runner, db, user_id, conversation_id, body)`. Reuse the existing
  `ConversationThread`, `require_chat`, and `submit_turn` interfaces. Recheck ownership while
  reserving the turn.
- [ ] Extend `ChatScope` and `CHAT_SCOPES` in the existing conversation feature. Expose
  `POST /conversations/offers`, `GET /conversations/offers/{conversation_id}`, and
  `POST /conversations/offers/{conversation_id}/messages`. The scope is stored as text.
- [ ] Declare the new routes in `backend/app/features/conversations/mcp.py` at the same levels
  as comparable conversation routes. Update the existing scope descriptions.
- [ ] Run Offers isolation and the existing chat thread isolation tests.

### Task 2. Ground answers in Offers data

- [ ] In `backend/tests/features/conversations/test_offers_chat.py`, use a scripted model.
  Assert the prompt contains stored dates, the linked status and saved contacts for the
  matching offer, skill gaps, and a bounded history. Assert a second user's records never
  appear and a fake instruction embedded in a posting remains framed as untrusted data.
- [ ] Run the scripted case before adding the context.
- [ ] Read compact summaries through `backend/app/features/postings/service/queries.py` and
  application facts through `backend/app/features/applications/service/offers_context.py`.
  Resolve linked applications by posting ID. Rank relevant offers by company/title match and
  prior verified citations, then use recent records to fill available context. Include a count
  that allows the assistant to report a partial list.
- [ ] Build references in `backend/app/features/conversations/offers_context.py`. Add an
  `offers_adviser` prompt, and small wiring changes in the conversation store and node.
  Use existing citation extraction with `posting` and `application` source kinds.
  Keep unrelated memory and network retrieval out of the Offers context.
- [ ] Run the Offers context, prompt, and chat isolation tests. Check the MCP coverage guard.
- [ ] Export OpenAPI and generate frontend API types. Verify both artifacts are current.

### Task 3. Add the Offers modal

- [ ] In `frontend/src/features/conversations/pages/OffersConversation/OffersConversation.test.tsx`,
  mock the Offers routes. Exercise opening the dialog, selecting and creating chats, sending a
  question, displaying its source links, reopening, and closing with Escape.
- [ ] In the Offers page test, assert composition renders the supplied chat trigger on
  `/carriere/offres` without disrupting the posting form.
- [ ] Run the new tests before implementation and confirm they fail on the missing entry point.
- [ ] Implement `OffersConversation` with a Radix dialog and `OffersThread` with the existing
  list, transcript, composer, and hooks. Add English prompts, labels, and states. On narrow
  screens switch between the chat list and the thread.
- [ ] In `frontend/src/features/gap/manifest.ts` and `frontend/src/app/registry.ts`, compose the
  chat trigger into the page. Update source link routing for postings and applications.
- [ ] Run Offers and related conversation tests. Check keyboard focus, mobile layout, lint,
  type checking, import contracts, and generated API types. Stage explicit paths and commit.
