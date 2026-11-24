# Offers chat

## Intent

Ask open-ended questions about job postings directly from the Offers page. Pick up earlier
conversations or start a separate one without leaving the list of postings.

## User experience

- An **Ask about offers** button opens a dialog from `/carriere/offres`. When the English URL
  migration moves that page, the legacy path redirects to the same page and keeps the same button.
- On wider screens, the left pane lists saved chats and has a **New chat** button. The main pane
  shows the selected conversation and a composer. On narrow screens, a **Chats** control opens
  the list and returns to the thread when one is selected. Use Tremplin's visual components.
- With a new chat, show a short invitation and a few selectable questions about dates,
  applications, contacts, or learning priorities. The composer accepts free-form questions.
- Save chats for the signed-in account. Reopening the dialog brings back the most recent chat.
  Use the existing chat management actions for naming, searching, clearing, and deleting chats.
- Show the reply as it arrives through the existing conversation stream. Show retryable errors,
  restore focus to the trigger on close, and support keyboard navigation and Escape.

## Data and answers

Use the account's current Tremplin data. Job posting records give the date added, source and
requirements. Linked application records give application status, applied date and saved contacts.
Gap assessments and the available skills profile support suggestions about what to learn next.

The assistant answers in the language of the question. It distinguishes saved facts from
suggestions and indicates missing information. If there is no saved contact, it can suggest a role
such as recruiter or hiring manager. It identifies the corresponding offer and application with
links supplied by Tremplin. If an application is unlinked, it does not infer a confirmed match.

Questions can refer to one posting, several, or the collection. Include compact current records
for collection questions and select relevant detail for focused questions. Keep the context within
the existing conversation budget and indicate when the available records cover only part of the
question. Send only the job, application, contact and skill fields needed for that question to the
configured model. Treat postings and saved text as untrusted input.

## Approaches

1. Extend the existing conversation system with an Offers scope. This reuses saved threads,
   streaming, retry behavior, quotas and conversation management while keeping Offers threads
   separate from the Brain and training scopes. This is the proposed approach.
2. Extend the Brain chat with offers as a source. This would also reuse thread persistence, but
   answering from all Brain sources would broaden the context of a conversation started in Offers.
3. Build a separate chat system for Offers. This would allow independent storage and reply
   handling, at the cost of repeating account isolation, error handling and stream logic.

The user chose to use Tremplin data only. Web lookup, sending messages, editing applications and
submitting applications are outside this feature.

## Implementation boundaries

- Extend the existing conversation scope, reuse its storage and session graph, and give Offers
  its own prompt and context builder. Reuse idempotent message submission and turn limits.
- Read the relevant records through feature service interfaces scoped to the current user.
  Serve posting and application links only for records actually included in the context.
- Use the app composition boundary to mount the conversation panel on the Offers list page.
  Keep generated API types in sync with OpenAPI and follow the existing MCP conversation scopes.
- Add HTTP tests for two-account isolation, multiple chats and cross-scope access. With a scripted
  model, verify that replies can use current, relevant records and that content is framed as data.
  Verify opening, switching chats, keyboard behavior, and source links in frontend tests.
