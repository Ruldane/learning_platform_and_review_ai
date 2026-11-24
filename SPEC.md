# Tremplin specification

Nov 11, 2026 · @January

## 1. Vision and approved decisions

Tremplin combines AI-guided learning and job search in one local app. Both use a shared memory
of what January already knows. Claude Code can use this specification directly.

**Product principles**

- **Live progress.** Long actions show agents debating, researching, or drawing in real time.
- **Human approval.** January expressly approves programs, CVs, and messages before finalization.
- **Shared memory.** Learning, imports, and decisions feed one store that every agent can read.
- **Accuracy.** Agents rephrase and tailor content without inventing experience, degrees, or
  figures. They cite the source of every claim drawn from the web.
- **Costs limited to models.** The rest runs on open-source software in Docker.
- **Code organization.** The `frontend` and `backend` directories hold files of up to 300 lines.

**Approved decisions**

| Topic | Decision |
| --- | --- |
| Deployment | Local Docker first, Cloudflare later |
| Backend | Python, FastAPI, LangChain, and LangGraph |
| LLM providers | Anthropic, OpenAI, and GLM, selected in the UI. Haiku by default |
| Sign-in | Google OAuth, disabled by default locally |
| Web search | Free and self-hosted (section 10) |
| Vector database | Open source in Docker, native equivalent on Cloudflare (section 4) |
| Embeddings | Local model served by Ollama |
| CV | PDF as the only source. Recreate the design once as a reusable template |
| LinkedIn | Profile PDF export or pasted text only. No automated access |
| Study time | 10 to 15 hours weekly, with 2 hours each weekday and a weekend block |
| Interface | Light theme only |
| Scope | All 19 features in section 2 are in the MVP |
| Manual configuration | LLM provider API keys only |

**Initial assumptions**

- The dictated phrase “Echo la main” refers to **Ollama**.
- D312 sets English for the interface and newly generated lessons. Sources can use any language.
- UI strings are centralized. Existing lessons and other stored prose retain their language.
- The repository codename is `tremplin`. The public name was open in the original proposal.

## 2. MVP scope

The MVP covers 19 features. Seven are core, six were approved in discussion, and six were added.

| No. | Feature | Description | Section |
| --- | --- | --- | --- |
| F1 | Learning Council | Four agents debate the goal live with web research and a whiteboard | 3 |
| F2 | Program | Weekly schedule, task list, lesson PDFs, and downloadable resources | 3 |
| F3 | Vector memory | Agents read and write imports and skills in an explorable store | 4 |
| F4 | CV Review | Two agents tailor the CV to a posting and render it in the same design | 5 |
| F5 | Application tracking | Pipeline, suggested follow-ups, and duplicate alerts | 6 |
| F6 | Model settings | Provider and model per role, plus API key management | 11 |
| F7 | Google sign-in | A space for each user, optional locally | 17 |
| F8 | Skill gap assessment | Compare postings with skills and add gaps to the plan | 7 |
| F9 | Skill validation | Quizzes and spaced reviews before marking a topic as learned | 7 |
| F10 | Mock interview | Posting-based technical and behavioral interview | 7 |
| F11 | Proof projects | A small project per module yields a CV line and draft post | 7 |
| F12 | Market radar | Analyze postings for the target role to prioritize skills | 7 |
| F13 | Adaptive replanning | Weekly review and revised schedule | 7 |
| F14 | Guided study | A tutor supports each study block in real time | 8 |
| F15 | Skill map | Graph of mastered, ongoing, and missing skills with evidence | 8 |
| F16 | Application kit | Tailored CV, letter, messages, and company dossier in one click | 8 |
| F17 | Morning brief | Live home page with study, reviews, follow-ups, and new postings | 8 |
| F18 | Quick capture | Turn a link, PDF, or note into a summary, flashcards, and memory | 8 |
| F19 | Hiring panel | Four recruiter personas discuss the CV against the job posting | 8 |

The MVP excludes a mobile app, automated submissions or messages, automated LinkedIn access,
voice mode, and payments.

## 3. Learning workflow (F1 and F2)

January enters a goal and four agents debate it live. She selects a learning path and Tremplin
produces a full program with lessons and resources.

### 3.1 Session flow

1. **Goal.** January enters a free-text goal such as becoming an AI product engineer, an
   optional deadline, and her time budget. The Moderator reads memory and asks up to five
   clarifying questions.
2. **Research.** The Scout searches the web (section 10). Each selected source appears live
   in the Sources panel with its author, date, and language.
3. **Opening round.** Each agent posts a position in up to 150 words. The Scribe draws a domain
   map on the whiteboard.
4. **Later rounds.** Agents respond to and challenge each other before converging. The default
   is three rounds, configurable from one to five.
5. **Proposals.** The Council presents two or three paths. Each has a name, expected outcome,
   duration in weeks, weekly workload, skills, final project, tradeoffs, and whiteboard diagram.
6. **Choice.** January chooses one path, combines two, or asks for another round. For another
   round, return to step 4.
7. **Program.** The Strategist makes a weekly plan. January can move, remove, or add items
   before approving it.
8. **Production.** Lessons and resources are produced in the background. Weeks one and two
   are produced immediately. Later weeks are produced seven days in advance to allow replanning.

### 3.2 January's role

- The message field stays available throughout the debate. The next round includes the message,
  and the agents must address it explicitly.
- Controls remain visible for pausing, starting another round, moving to proposals, asking for
  more concrete details, and asking for shorter replies.
- The session waits for January after the goal questions, at path selection, and at program
  approval.
- An interrupted session resumes at the same point, including after a Docker restart.

### 3.3 Animated whiteboard

- The whiteboard is an Excalidraw canvas with a hand-drawn classroom style.
- The Scribe emits a Mermaid `flowchart`. The frontend converts it to Excalidraw elements
  with `@excalidraw/mermaid-to-excalidraw`.
- Elements appear in reasoning order with 150 to 300 ms between them.
- Diagrams include domain maps, prerequisite graphs, path timelines, and proposal comparisons.
- January can move, annotate, and correct the board. Agents receive her edits as a message.
- Every board state is saved. Exports are available as PNG, SVG, and `.excalidraw`.
- If conversion fails, the frontend displays Mermaid's SVG and logs the error.

### 3.4 Program (F2)

A program contains weeks, weeks contain modules, and modules contain tasks.

| Level | Required fields |
| --- | --- |
| Week | Theme, measurable goal, hours, end-of-week deliverable |
| Module | Title, target skills, prerequisites, linked lesson and resources |
| Task | Action title, type, 15 to 120 minute duration, completion criterion, scheduled day |

Task types are `read`, `watch`, `practice`, `quiz`, and `project`.

**Scheduling rules**

- The default is two hours each weekday and one three- to four-hour weekend block. January
  can change availability in Settings.
- Planned work uses at most 85% of the budget to leave room for interruptions.
- Skip a topic memory already knows, or make it a 20-minute review labeled **Already known**.
- Each week includes at least one practice task and ends with a quiz (F9).
- Views include a weekly calendar, full list, and overall progress. Export to PDF or `.ics`.

### 3.5 Lessons

- Each module has one lesson stored as Markdown, readable in the app and downloadable as a PDF.
- Lessons are 1,200 to 2,500 words.
- Each lesson includes up to three objectives, prerequisites, a five-line summary, explanation,
  diagrams, a worked example, common mistakes, an exercise and separate answer, sources, and
  a five-question self-assessment.
- The Writer drafts the lesson. The Checker verifies facts against retrieved sources and
  checks links. The lesson paraphrases the sources and uses short, attributed quotes.
- A shared A4 HTML and CSS template provides a contents list, callouts, Mermaid diagrams as
  SVG, page numbers, and a light theme.

### 3.6 Resources

- Each module has three to six resources.
- Each has a type (official documentation, course, video, article, repository, or paper),
  language, duration, level, author, date, and a one-sentence reason for choosing it.
- Freely downloadable PDF papers and docs are saved locally. For other resources, keep the
  link and its reading entry.
- Library lists resources with filters for program, type, language, and read status.

## 4. Vector memory (F3)

January and the agents read and write memory through a local vector database. The relational
database retains the source text so the vector index can be rebuilt at any time. [Qdrant]

### 4.1 Technology

| Component | Local Docker | Future Cloudflare deployment |
| --- | --- | --- |
| Vector store | `qdrant/qdrant` Docker image, under Apache 2.0 | Vectorize |
| Embeddings | Multilingual `bge-m3` on Ollama, 1,024 dimensions | `@cf/baai/bge-m3` on Workers AI |
| Code interface | `MemoryRepository` backed by LangChain's `VectorStore` | `MemoryRepository` |

The same embedding model keeps the dimensions and search behavior consistent when migrating.
`bge-m3` supports over 100 languages, including French and English.

A shared interface makes the implementations portable. The original plan estimated that the
free Vectorize allowance of five million dimensions would fit about 4,880 chunks at 1,024
dimensions each. Beyond that, the design calls for a paid plan or a smaller model and the
reindex operation in section 4.6. [Vectorize pricing][vectorize-pricing]

[Qdrant]: https://github.com/qdrant/qdrant
[vectorize-pricing]: https://developers.cloudflare.com/vectorize/platform/pricing/

### 4.2 Organization

Qdrant uses one `memory` collection, filtered by `user_id` and `kind`.

| `kind` | Content | Writers |
| --- | --- | --- |
| `document` | Chunks from CVs, LinkedIn exports, notes, PDFs, and saved web pages | January |
| `skill` | One point per concept or skill with mastery and evidence | January, agents, quizzes |
| `lesson` | Chunks of generated lessons | Agents |
| `source` | Summaries of web sources for reuse | Agents |
| `posting` | Job postings and company dossiers | January, agents |
| `decision` | Preferences and decisions, such as favoring practice over videos | January, agents |

Common payload fields are `user_id`, `kind`, `source_id`, `title`, `text`, `lang`, `tags`,
`created_by`, `created_at`, and `session_id`.

**Skill mastery levels**

| Level | Condition |
| --- | --- |
| `declared` | January reports the skill or it is extracted from an imported document |
| `in_progress` | A module in the current program covers the skill |
| `validated` | January passes a quiz with 80% or higher (F9) |
| `proven` | A completed project uses the skill (F11) |

### 4.3 Ingestion

- Accept PDF, DOCX, Markdown, text, URLs, YouTube transcripts, and pasted text.
- Extract and clean text, split it into roughly 500-token chunks with a 60-token overlap, embed
  the chunks, and save them.
- A content hash prevents duplicate indexing.
- Each document shows its processing status as queued, in progress, indexed, or failed.
- January can mark a document as already learned. The Archivist extracts its concepts as
  `declared` skills.

### 4.4 Agent reads

- `memory_search(query, kinds, k)` performs dense search filtered by `kind`, with eight results
  by default.
- `memory_get_skills()` summarizes the skill map (F15).
- Each agent graph starts by loading relevant skills, decisions, and documents for the goal.

### 4.5 Agent writes

- Agents write through `memory_write(kind, title, text, tags, evidence)`.
- Agents can write `source` and `lesson` entries directly.
- Agent-written skills start at `declared` or `in_progress`. A quiz or project can raise the level.
- A proposed `decision` waits under **To confirm** before being saved.
- Each write records the agent, date, session, and a one-sentence reason.

### 4.6 Memory explorer

The Memory page shows what agents know about January.

- **List.** Filter by type, tag, author, and date. Edit, delete, and merge duplicates.
- **Semantic search.** View matching results with their scores.
- **Entry details.** Read the text, chunks, metadata, nearest neighbors, and write history.
- **2D vector map.** The backend projects vectors with PCA by default. Colors identify types
  and clicking a point opens its entry.
- **Query preview.** See the exact chunks an agent would receive for a query.
- **Statistics.** View totals by type, the last write, and estimated Vectorize quota usage.
- **Actions.** Rebuild vectors from text, export JSON, or open the Qdrant dashboard at
  `http://localhost:6333/dashboard`.

## 5. CV Review (F4)

Two agents review a CV against a specific posting. They propose changes with reasons and
regenerate the PDF in the original design at January's request.

### 5.1 Master profile (one-time setup)

- January imports her CV PDF, a LinkedIn profile PDF or pasted profile text, and a free-text
  description of her skills and goals.
- The Archivist creates a structured JSON **master profile** with identity, title, summary,
  experience and achievements, education, skills, projects, languages, and links.
- January reviews and edits the profile in a form.
- Tailored CVs select and rephrase facts from the master profile as their sole factual source.

### 5.2 Design capture (once per design)

1. The backend extracts text blocks with their position, font, size, and color, plus an image
   of each page.
2. The Layout Designer uses a vision model to make an HTML and CSS template with the same
   columns, margins, colors, and hierarchy.
3. Render the template to PDF and compare it with the original. The app shows them side by
   side with a similarity score. Automatic corrections run for up to three passes.
4. January approves the result or asks for an adjustment in natural language, such as
   “The left column is too wide.”

- **Fonts.** Save the original font in the template folder if it is freely available. Otherwise
  use the closest substitute and report the change.
- **Rendering.** The template aims for visual fidelity within rendering tolerances.

### 5.3 Review against a posting

January enters a posting URL or pastes the text. If the link requires sign-in or the page is
empty, the app immediately asks for the posting text before starting the analysis.

1. **Posting analysis.** Extract title, seniority, required and preferred qualifications,
   verbatim keywords, screening criteria such as experience, location, and language, and tools.
2. **Company research.** Find the product, stack, news, values, hiring process, and the hiring
   platform if the application URL identifies it.
3. **Duplicate check.** Check application tracking (section 6).
4. **Machine reading.** The ATS Reader extracts the PDF text as a parser would and checks
   reading order, section headings, keywords, and their variants.
5. **Human reading.** The Recruiter checks first-screen clarity, title fit, quantified
   achievements, order of relevance, red flags, and length.
6. **Debate.** The two agents resolve disagreements, such as keyword density and readability,
   in up to two visible rounds.
7. **Suggestions.** Each change names the section, before and after text, reason, type, and
   supporting fact from the master profile. January can approve or refuse them singly or in bulk.
8. **Output.** January can view a report on what to change or generate a CV PDF with the template
   and approved changes.
9. **Final check.** The ATS Reader reviews the generated PDF. Changes to the original page
   count require approval.

The PDF uses `CV_<Name>_<Company>_<Role>.pdf`. Its version is saved and linked to the application.

**Before and after indicators**

| Indicator | Calculation |
| --- | --- |
| Requirement coverage | Share of mandatory qualifications supported by a real CV fact |
| Machine readability | Passed checks for text, reading order, headings, contacts, and fonts |

The checks cover selectable text, standard section headings, contact details in the body, and
font sizes. The screen explains that the app's indicators do not represent a universal ATS score.

### 5.4 Applicant tracking system knowledge

Agents use a dated knowledge base refreshed by web research every 30 days. The initial
findings come from [Huntr's survey][huntr-ats].

- An ATS primarily stores and searches applications. Huntr reported that none of the major
  systems studied automatically rejected a CV based on its content alone.
- Screening questions can filter applications automatically. The Application Kit (F16)
  identifies them and drafts accurate answers.
- Recruiters use keywords for search and ranking. Some systems include AI ranking.
- Keep contact details in the body, use standard fonts of 10 points or larger, and use
  a PDF or Word file.

**Agent rules**

- Use the posting's exact words where they accurately describe January.
- Use standard headings, reverse chronological order, and consistent dates. Keep text out of
  images.
- Avoid hidden text and keyword stuffing.
- Report the checks the CV passes. The app makes no guarantee of passing a hiring screen.

### 5.5 Safeguards

- A validation node checks every proposed sentence against the master profile. A tool, figure,
  or title missing from the profile sends the change to **To confirm**.
- Once January confirms a new fact, it is added to the master profile first.
- Send posting keywords for skills January lacks to skill gap assessment (F8).

## 6. Application tracking (F5)

Applications records each posting, suggests timely follow-ups, and prevents duplicates.

### 6.1 Application record

- **Fields.** Company, role, posting URL, posting text snapshot, channel, application date,
  status, submitted CV version, letter, contacts (name, role, link), notes, and next action
  with its date.
- **Statuses.** To apply, Applied, Followed up, Interview, Offer, Rejected, No answer, Withdrawn.
- **Views.** Kanban by status, sortable table, and an event timeline on each record.
- Copy the posting text on creation to keep it available if the listing disappears.

**Ways to create an application**

1. Generating a CV for a posting creates an application in **To apply**. The **I applied**
   button records the date.
2. January can create a record through a form.
3. The tracking assistant can create a record from a message such as “I applied to X yesterday
   for role Y” and show it for confirmation.

### 6.2 Follow-ups

| Trigger | Suggestion |
| --- | --- |
| 7 days after applying, without a reply | LinkedIn message to the recruiter or hiring manager |
| 14 days after applying, without a reply | Follow-up email |
| 21 days after applying, without a reply | Move the record to No answer |
| Day after an interview | Thank-you message |
| 7 days after an interview, without a reply | Ask for an update |

- January can change the delays in Settings.
- Each follow-up shows who to contact and a draft to copy. January can mark it done, snooze
  it for three days, or dismiss it.
- With no saved contact, offer a LinkedIn search link prefilled with the company and role.
- January copies and sends the draft herself.
- Due follow-ups appear in the Morning Brief (F17) and in a badge on the tab.

### 6.3 Duplicate alerts

Adding a posting from any screen triggers the duplicate check.

| Confidence | Condition |
| --- | --- |
| Certain | Same normalized URL |
| Probable | Same company and title similarity of at least 85% |
| Possible | Same company and high vector similarity of the posting text |

- An alert can say “You applied to X for role Y on November 3 (Applied).”
- January can open the existing record, confirm this is a different role, or cancel.
- An application to the same company for a different role in the past 30 days shows a notice.

### 6.4 Indicators

The tab shows application counts by status, the response rate, average response time, and
the number of follow-ups due.

### 6.5 Chat about job postings

**Ask about offers** opens a dialog from `/career/postings`. The old address
`/carriere/offres` redirects there. January can create and revisit several saved chats. The
assistant answers from her saved Tremplin postings, application history, contacts, and skill
gaps. It can explain when an offer was added, whether she applied, whom she has saved as a
contact, and what to learn to improve her fit. [Offers chat design][offers-chat-design]

[offers-chat-design]: docs/superpowers/specs/2026-11-24-offers-chat-design.md

## 7. Approved learning and career features (F8 to F13)

Skill gaps inform the learning plan, and completed work supplies evidence for the CV.

### F8. Skill gap assessment

- **Trigger.** An added posting or a request to assess a target role.
- **Analysis.** The Analyst extracts skills, maps them to the skill catalog, and compares
  them with January's current skills.
- **Result.** A table shows whether each skill is required or preferred, its current level,
  and the proposed action. A skill may already be in a program week, be added, or be out of scope.
- **Match score.** The score runs from 0 to 100. Required qualifications weigh 2 and preferred
  ones weigh 1. A `validated` or `proven` skill counts as 1, `declared` as 0.6, `in_progress`
  as 0.3, and a missing skill as 0.
- Adding a skill to the schedule starts replanning (F13), which requires approval.
- An overview shows the ten skills most often missing across postings.

### F9. Skill validation

- The Examiner makes a quiz of 8 to 12 questions per module. It mixes multiple choice, short
  answers, code reading, and explanations in January's own words.
- Grade open answers with a rubric and explain each mistake.
- A score of at least 80% moves the skill to `validated`. Lower scores add targeted review
  tasks and a retake two days later.
- **Spaced review.** Lessons and quiz mistakes supply flashcards. Intervals are 1, 3, 7, 16,
  and 35 days. A mistake resets a card to one day.
- The daily review queue is capped at 15 minutes.
- A `validated` skill returns to `in_progress` after two consecutive failed flashcard reviews.

### F10. Mock interview

- Start from an application or enter a role directly.
- **Modes.** Behavioral, technical, case study, and mixed. Choose 15, 30, or 45 minutes.
  Practice in English by default or choose French.
- The Interviewer asks one question at a time and follows up on answers. It uses the posting,
  company dossier, submitted CV version, and known gaps.
- MVP interviews use text.
- **Debrief.** Scores cover clarity, structure, technical depth, and role fit. Include three
  strengths, three improvements, and a better version of the weakest answer.
- Missed questions become flashcards. The debrief is linked to the application.

### F11. Proof projects

- Each module ends with a three- to six-hour project with context, goal, constraints,
  and acceptance criteria.
- January submits a repository URL or a description with screenshots.
- The Practitioner assesses the submission against the criteria and gives written feedback.
- Approval moves the skill to `proven` and creates four drafts for a CV line, a master profile
  project, a LinkedIn post, and a README outline.
- January approves entries to the master profile.
- Portfolio lists projects with their status.

### F12. Market radar

- Every week and on demand, the Scout gathers 30 to 50 public postings for the target role
  and region.
- The Analyst extracts skills, tools, seniority, remote options, and any listed salary.
- **Result.** Rank skills by frequency, show changes since the last run, and flag gaps such
  as “Requested in 60% of postings and missing from your program.”
- Postings with a match score of at least 70 appear in the Morning Brief.
- Report how many postings were read and count inaccessible sites separately.

### F13. Adaptive replanning

- **Weekly review.** Sunday at 6 p.m. by default, with a configurable time. It covers planned
  and recorded hours, completed tasks, and quiz scores.
- The Strategist proposes a new plan that redistributes overdue tasks within the weekly budget.
- When progress is more than 30% behind for two weeks, suggest reducing scope or moving the
  deadline.
- When ahead of schedule, suggest bringing tasks forward or exploring a topic in more depth.
- **Other triggers.** A skill gap added to the plan or a message such as “I only have five
  hours this week.”
- Each proposal shows the old and new plan, waits for approval, and keeps version history.

## 8. Daily learning and career features (F14 to F19)

These features support daily work with a tutor during study, a home page refreshed each morning,
and a hiring panel that evaluates a CV before submission.

### F14. Guided study session

- Start the day's block with a timer. The default is 50 minutes of work and 10 minutes of rest.
  Both are configurable.
- The Tutor leads January through the goal, lesson sections with a comprehension question
  after each one, the exercise, and three final questions.
- **Modes.** Socratic asks questions to guide discovery. In Feynman, January explains and
  the Tutor looks for gaps. Direct gives answers.
- The stuck control offers three levels of hints before revealing the solution.
- The Tutor reads the lesson, sources, and memory and can draw on the whiteboard.
- **End of session.** Summarize the block, log time, check off tasks, update skills, make
  flashcards from mistakes, and add a journal entry.
- The current streak and weekly hours stay visible.

### F15. Skill map

- Nodes represent skills and edges represent prerequisites. Color shows mastery and size
  shows market demand (F12).
- The Strategist creates the catalog with the program. Postings and Market Radar extend it.
- Click a node to see lesson, quiz, project, and CV evidence, postings that require the skill,
  and the next action.
- **Views.** Prerequisite graph, radar chart by domain, and progress chart with weekly data.
- **Comparison.** Current skills, a target role, or a specific posting.
- F4, F8, F12, and F13 read the same catalog.

### F16. Application kit

For a posting, one click generates seven items in parallel and displays each as it is ready.

| Item | Details |
| --- | --- |
| Tailored CV | Section 5 workflow |
| Cover letter | 250 to 350 words in the posting's language |
| LinkedIn messages | Short invitation and longer message |
| Follow-up emails | Drafts for days 7 and 14 |
| Form answers | Flag screening questions and answer from the master profile only |
| Company dossier | One page of cited research |
| 60-second pitch | A role-specific answer to “Tell me about yourself” |

- The dossier covers business, product, stack, six months of news, culture, the interview
  process, five questions to ask, and points to watch.
- January can edit all items before use. The application record stores them and can export
  them as one archive.
- A free-text **personal style guide** in Settings informs drafts written on January's behalf.
- January supplies salary expectations herself.

### F17. Morning Brief

- Generate it daily at 7 a.m. by default, and on app open if the brief is from yesterday.
- **Contents.** Today's study block, due flashcards and follow-ups, new Radar postings, weekly
  progress, one cited resource or news item, and two sentences from the Council on today's priority.
- The brief is the home page, with quick actions to start studying, review, add a posting,
  and capture an item.
- The activity feed shows background work such as generated lessons, Radar updates, and
  memory writes.

### F18. Quick capture

- Open the global field with Ctrl+K or Cmd+K. Enter a link, text, file, or a note such as
  “I learned X today.”
- The Archivist reads it, summarizes it in five lines, extracts concepts, links them to program
  modules, and stores the result in memory.
- If the capture covers a planned task, suggest marking it done. Suggest flashcards as well.
- If a link cannot be read, ask for the text immediately.
- The **learning journal** lists captures, sessions, and quizzes chronologically with a
  weekly summary.

### F19. Simulated hiring panel

- **Input.** A CV version and a posting.
- **Roles.** An ATS reader checking what recruiter searches find the CV, an HR recruiter,
  the hiring manager, and a prospective teammate.
- Each gives a first impression. After two live debate rounds, each votes yes, no, or maybe
  on an interview and names their main objection.
- **Result.** Verdict, ranked objections, and three changes that could change a vote.
- Running the panel again after changes shows both results.
- The company dossier adapts the roles to the organization, such as a startup or large enterprise.
- The screen labels the result as a simulation.

## 9. Agents and orchestration

Each workflow is a LangGraph graph. Agents are nodes, January's approvals are interrupts,
and each event is streamed to the interface and saved.

### 9.1 The 17 agents

| Agent | Role | Features | Model tier |
| --- | --- | --- | --- |
| Moderator | Orders turns, asks clarifying questions, and summarizes | F1, F19 | Fast |
| Strategist | Designs paths, prerequisites, and schedules | F1, F2, F13, F15 | Strong |
| Practitioner | Brings practical experience and reviews projects | F1, F11 | Standard |
| Scout | Finds web sources and working practitioners | F1, F2, F12, F16, F17 | Fast |
| Skeptic | Challenges ideas, checks the time budget, and trims scope | F1 | Standard |
| Scribe | Draws on the whiteboard and records the discussion | F1, F14 | Fast |
| Writer | Writes lessons | F2 | Strong |
| Checker | Checks facts, links, and originality | F2, F16 | Standard |
| Archivist | Imports content and extracts concepts and master profiles | F3, F4, F18 | Fast |
| ATS Reader | Checks machine readability of CVs | F4, F19 | Standard |
| Recruiter | Reviews CVs as a human reader would | F4, F19 | Standard |
| Layout Designer | Recreates the CV design using vision | F4 | Vision |
| Analyst | Extracts skills and calculates match scores | F8, F12 | Fast |
| Examiner | Creates quizzes, grades answers, and writes flashcards | F9 | Standard |
| Interviewer | Runs mock interviews and debriefs | F10 | Strong |
| Tutor | Guides study sessions | F14 | Standard |
| Tracking Assistant | Creates applications from text and drafts messages | F5, F16 | Fast |

The Strategist, Practitioner, Scout, and Skeptic debate in the Learning Council. The Moderator
and Scribe support the discussion without taking a position.

The hiring panel (F19) uses the ATS Reader and Recruiter. Two Recruiter prompt variants play
the Hiring Manager and Prospective Teammate.

### 9.2 A graph per workflow

The initial design has sixteen graphs in separate modules. These are `learning_council`,
`program_builder`, `lesson_factory`, `cv_capture`, `cv_review`, `application_kit`,
`gap_analysis`, `quiz`, `interview`, `market_radar`, `replan`, `study_session`, `capture`,
`hiring_committee`, `daily_brief`, and `project_review`.

They load memory context, do the work, pause for approval, finalize, and write to memory.

### 9.3 Debate rules

- The Moderator sets the speaking order. Each agent sees all previous rounds.
- Each turn is at most 150 words.
- Claims about the domain cite a retrieved source or a memory entry.
- Starting in round two, each agent addresses at least one other by name.
- The Skeptic raises at least one objection per round.
- The next round addresses January's messages first.
- The Moderator can end the debate early once positions stop changing.
- Each session can set a token cap and shows estimated cost in real time.

### 9.4 Human approval

- Pause with LangGraph `interrupt()` and a JSON payload with type, question, and options.
  [LangGraph interrupts][langgraph-interrupts]
- Use a checkpointer with the session ID as `thread_id`. Resume with `Command(resume=value)`.
- The async SQLite checkpointer uses `checkpoints.db`, a separate database file.
- Resuming starts the interrupted node again from the beginning. Keep database writes, paid
  calls, and other side effects after `interrupt()` or in their own node.

[langgraph-interrupts]: https://docs.langchain.com/oss/python/langgraph/interrupts

### 9.5 Real-time events

Each run publishes typed events, stores them in `session_events`, and streams them by WebSocket.

| Type | Payload |
| --- | --- |
| `agent.started` | Agent, step, and intent, such as “Looking for recognized courses” |
| `agent.token` | Fragment of a message in progress |
| `agent.message` | Agent's final message |
| `tool.called`, `tool.result` | Tool, arguments, and result summary |
| `source.found` | Title, link, author, date, language, and score |
| `board.update` | Mermaid code and step number |
| `memory.written` | Written entry and reason |
| `interrupt.requested` | Question and options for January |
| `proposal.ready`, `artifact.ready` | Available proposal or file such as a PDF or plan |
| `cost.updated` | Cumulative tokens and estimated cost |
| `run.completed`, `run.failed` | End of run with a summary or error |

- All events have `id`, `session_id`, `seq`, `ts`, `type`, `agent`, and `payload`.
- On reconnect, the client sends its last `seq` and the server replays subsequent events.
- For each step, the UI shows the intent statement and tool calls.

### 9.6 Reliability

- Pydantic validates proposals, plans, CV changes, quizzes, and other structured outputs.
  Retry twice on validation failure, then emit a readable error.
- Allow up to 120 seconds per node and retry provider errors with increasing delays.
- Store each agent's prompt and variables in a versioned Markdown file.
- Record model, token counts, latency, and estimated cost in `llm_calls`. Display calls
  in the agent log.
- APScheduler runs the brief, radar, weekly review, follow-ups, lesson generation seven days
  ahead, and ATS knowledge refresh in the backend process.

## 10. Web search

SearXNG runs in Docker as the default open-source metasearch engine. It needs no API key.
Brave Search is an optional fallback.

### 10.1 Providers

| Provider | Cost in the original design | API key | Use |
| --- | --- | --- | --- |
| Local SearXNG | Free and open source | None | Default |
| Brave Search API | $5 monthly credit, about 1,000 queries | Required | Optional fallback |

- The Brave plan described in the original design required a credit card.
- `SearchProvider.search(query, lang, time_range, categories)` returns results with title,
  link, excerpt, engine, and date.
- The fallback order is configurable. By default use SearXNG and then Brave if a key is set.
- The repository's SearXNG `settings.yml` enables JSON with `search.formats: [html, json]`.
- Enabled engines include general search, Wikipedia, GitHub, arXiv, Stack Overflow, and YouTube.
- General search engines may temporarily throttle a busy SearXNG instance. Query multiple
  engines, cache results, and rate-limit requests.

### 10.2 Reading pages

| Content | Method |
| --- | --- |
| Web page | Fetch with `httpx` and extract the main text with `trafilatura` |
| JavaScript-rendered page | Fall back to a Gotenberg PDF conversion, then extract text |
| PDF | Download and extract text |
| YouTube video | Transcript when available, otherwise title and description |
| GitHub repository | Read the README through the public API |
| Research paper | arXiv API |

- `web_read(url)` returns text, title, author, date, language, and an `ok` or `unreadable` status.
- Cite successfully read pages only and respect sign-in requirements.
- Store each read page for seven days in `web_cache`.
- Allow up to 15 seconds per page and one request per second per domain.

### 10.3 Source quality

The Scout scores sources out of 100. A lesson can use sources scoring at least 60.

| Criterion | Points |
| --- | --- |
| Authority, such as official docs, a recognized institution, or a verified practitioner | 30 |
| Publication date, with a preference for the last 12 months on AI topics | 20 |
| Depth | 20 |
| Identifiable author | 15 |
| Teaching quality | 15 |

- **Practitioners.** The Scout finds five to ten people per goal by name, role, and publication
  venue. Prioritize their articles and talks and retain public professional information only.
- **Languages.** Search in French and English by default, with other languages configurable.
  Lessons summarize in English and cite sources in their original language.
- Settings lets January edit preferred and excluded domains.
- The interface shows queries, chosen sources, rejected sources, and rejection reasons.

### 10.4 Limits

- Default to 12 queries and 30 page reads per session, with configurable limits.
- A Cloudflare deployment would use Brave or a separately hosted SearXNG instance.

## 11. Model and API key settings (F6)

Settings lets January choose a provider and model for each tier and enter API keys.
One LLM key is enough to run the application.

### 11.1 Providers

| Provider | Integration | Variable | Role |
| --- | --- | --- | --- |
| Anthropic | `langchain-anthropic` and `ChatAnthropic` | `ANTHROPIC_API_KEY` | Default |
| OpenAI | `langchain-openai` and `ChatOpenAI` | `OPENAI_API_KEY` |  |
| GLM (Z.ai) | `ChatOpenAI` with `base_url` | `ZAI_API_KEY` | OpenAI-compatible |

The default Z.ai URL is `https://api.z.ai/api/paas/v4/` and is configurable for other plans.
Agents obtain all model clients through `get_chat_model(tier)`.

### 11.2 Model tiers

Agents request a tier. Settings maps the tier to a provider and model.

| Tier | Use | Initial default |
| --- | --- | --- |
| Fast | Research, extraction, moderation | Claude Haiku |
| Standard | Debate, review, quiz, tutoring | Claude Haiku |
| Strong | Planning, lesson writing, interviews | Claude Haiku |
| Vision | CV design capture | Claude Haiku |

- **Presets.** All Haiku, Haiku with Sonnet for Strong, All GLM, All OpenAI, and Custom.
- Fetch available models from each provider's API when supported. Otherwise accept a model ID.
- `model_defaults.py` holds default IDs such as `claude-haiku-5-5` and `claude-sonnet-5-5`.
  Check the provider's documentation when changing them.
- Advanced settings allow model overrides per agent.
- If the vision tier uses a model without vision, disable design capture and explain why.

### 11.3 API keys

- Add keys through the root `.env` file or Settings.
- Encrypt keys added in the app with `APP_SECRET`, generated on first start in a Docker volume.
- Return only the final four characters to the browser. Keep keys out of logs.
- The test button makes a minimal call and shows the result.
- Local embeddings and default web search need no key.
- An optional Brave key enables up to 900 queries per month in the original design to stay
  within the credit.

### 11.4 Other settings

| Setting | Default |
| --- | --- |
| Availability | 2 hours each weekday, 3 to 4 on the weekend |
| Lesson language | English |
| Search languages | French and English |
| Debate rounds | 3 |
| Session cap | 300,000 tokens |
| Brief time | 7 a.m. |
| Weekly review | Sunday at 6 p.m. |
| Follow-up delays | 7, 14, and 21 days |
| Personal style guide | Empty |
| Preferred and excluded domains | Starter list |

### 11.5 Cost tracking

A screen shows token counts and estimated costs by day, feature, agent, and model.
Update prices in `model_prices.json`.

## 12. Architecture and source layout

The original design uses six Docker containers for the frontend, backend, and four open-source
services. Provider interfaces let a future Cloudflare deployment reuse the features.

Only provider implementations know their services. A Cloudflare deployment would supply
implementations for that platform.

### 12.1 Stack

| Layer | Choice | Purpose |
| --- | --- | --- |
| Backend | Python, FastAPI, Uvicorn | Async, WebSocket support, Python Workers target |
| Agents | LangChain and LangGraph | Interrupts and resume |
| Schemas | Pydantic v2 | Structured outputs and API validation |
| Relational DB | SQLite WAL, async SQLAlchemy 2, Alembic | Embedded database, D1-like schema |
| Vector DB | Qdrant | Section 4 |
| Embeddings | Ollama with `bge-m3` | Local, free, multilingual |
| Web search | SearXNG | Section 10 |
| PDF rendering | [Gotenberg] with Chromium | HTML and CSS to PDF for lessons and CVs |
| PDF reading | `pdfplumber`, `pypdfium2` | Positioned text and page images |
| Web reading | `httpx`, `trafilatura` | Main content extraction |
| Scheduled work | APScheduler | In-process scheduling |
| Files | Docker volume behind `FileStorage` | Can use R2 later |
| Frontend | React, TypeScript, Vite | UI and build tooling |
| Interface | Tailwind CSS, shadcn/ui | Light theme |
| Frontend data | TanStack Query, Zustand | Server cache and local state |
| Whiteboard | Excalidraw, `@excalidraw/mermaid-to-excalidraw` | Editable hand-drawn style |
| Skill map | React Flow with `elkjs` | Automatically laid-out graph |
| Charts | Recharts | Radar, line, and bar charts |
| Tests | pytest, Vitest, Playwright | Unit, component, and end-to-end checks |
| Quality | ruff, mypy, ESLint, Prettier | Commit checks |

Use stable versions at implementation time and pin them with lockfiles.

[Gotenberg]: https://github.com/gotenberg/gotenberg

### 12.2 Source organization rules

- Limit source files to **300 lines** and functions to 50. ESLint `max-lines` and backend
  `scripts/check_file_length.py` enforce the limits at commit time.
- Use matching feature directory names in the backend and frontend.
- A router receives requests and returns responses. The service handles business logic.
  The repository talks to the database.
- Features use provider interfaces for external models, search, embeddings, vectors, PDFs,
  and files.
- Each agent has a Markdown prompt and Python node. Each graph has a module.
- Generate TypeScript API types from the backend's OpenAPI schema.

### 12.3 Backend source tree

```text
backend/
  pyproject.toml
  Dockerfile
  alembic/
  scripts/check_file_length.py
  app/
    main.py              # App construction and routers
    config.py            # Settings read from the environment
    core/                # Security, encryption, errors, and logging
    db/                  # Engine, sessions, and models grouped by tables
    providers/
      llm/               # factory.py, anthropic.py, openai.py, glm.py
      search/            # base.py, searxng.py, brave.py
      embeddings/        # base.py, ollama.py
      vector/            # base.py, qdrant.py
      pdf/               # base.py, gotenberg.py, extract.py
      storage/           # base.py, local.py
      web/               # reader.py, youtube.py, github.py, arxiv.py
    agents/
      prompts/           # Markdown prompts by agent
      nodes/             # Python nodes by agent
      graphs/            # One module per graph
      state/             # State schemas by graph
      tools/             # memory_tools.py, web_tools.py, board_tools.py
      runtime/           # runner.py, checkpointer.py, events.py, costs.py
    features/            # Router, service, repository, and schemas per feature
      learning/  program/  lessons/  memory/  cv/  applications/
      gap/  quiz/  interview/  projects/  radar/  replan/
      study/  skills/  kit/  brief/  capture/  committee/
      settings/  auth/
    realtime/            # websocket.py, replay.py
    scheduler/           # Modules for scheduled jobs
    templates/           # HTML and CSS templates for lessons, programs, reports, and CVs
  tests/
```

### 12.4 Frontend source tree

```text
frontend/
  package.json
  Dockerfile
  vite.config.ts
  src/
    main.tsx
    app/                 # routes, layout, providers
    shared/
      api/               # HTTP client and generated OpenAPI types
      realtime/          # useSessionStream and event replay
      ui/                # shadcn components
      i18n/              # en.ts and message catalogs
      lib/
    features/            # Components, hooks, api.ts, and types.ts per feature
      home/              # Morning Brief
      learning/          # DebatePanel, AgentBubble, SourcesPanel, Board, ProposalCards
      program/           # WeekCalendar, TaskList, PlanDiff
      lessons/  study/  quiz/
      memory/            # List, 2D map, and query preview
      skills/            # Skill map
      cv/                # Master profile, design capture, review, and diff
      applications/      # Kanban, application records, and follow-ups
      kit/  committee/  interview/  radar/  projects/
      capture/  settings/  auth/
```

## 13. Data model

SQLite holds application data and memory source text. Qdrant stores the vectors and a payload copy.

### 13.1 Shared rules

- Each table has `id` as a text UUID, `user_id`, `created_at`, and `updated_at`. Store
  timestamps as ISO dates in UTC.
- Filter every repository query by `user_id`, including in local single-user mode.
- Use SQLite types and JSON columns for flexible data to stay compatible with D1.
- Change the schema through Alembic migrations.
- Store files under `storage/<user_id>/<type>/` and save only their paths in the database.

### 13.2 Accounts and agents

| Table | Contents |
| --- | --- |
| `users` | Email, name, Google ID, language |
| `user_settings` | Availability, languages, model tiers, style guide, scheduled times |
| `api_keys` | Provider, encrypted key, last four characters, last test time |
| `sessions` | Graph, status, linked object, tokens, cost |
| `session_events` | Session, `seq`, type, agent, payload, timestamp |
| `llm_calls` | Session, agent, provider, model, input and output tokens, latency, cost |
| `jobs` | Scheduled job, last run, next run, error |

Session statuses include `running`, `waiting_user`, `completed`, and `failed`.

### 13.3 Learning

| Table | Contents |
| --- | --- |
| `goals` | Goal, target role, deadline, status |
| `proposals` | Proposed paths for a goal and the selected path |
| `boards` | Mermaid and Excalidraw scene for each board state |
| `programs` | Goal, version, status, start date, weekly hours |
| `weeks` | Position, theme, goal, workload, deliverable |
| `modules` | Week, title, target skills, linked lesson |
| `tasks` | Module, title, type, duration, criterion, planned day, status |
| `lessons` | Module, Markdown, PDF path, status, word count |
| `resources` | Module, metadata, link, selection reason and score, local copy |
| `sources` | Pages and people with URL, author, language, date, score, and summary |
| `plan_versions` | Program version, diff, reason, approval date |
| `study_sessions` | Start, end, minutes, mode, summary |
| `quizzes`, `quiz_questions`, `quiz_attempts` | Module quizzes, questions, attempts, scores |
| `flashcards` | Front, back, skill, interval, due date |
| `projects` | Brief, submission URL, status, assessment, drafts |
| `journal_entries` | Type, text, links to session, capture, or quiz |

Resource metadata includes type, title, author, date, language, duration, and level.

### 13.4 Skills and memory

| Table | Contents |
| --- | --- |
| `skills` | Name, domain, synonyms |
| `skill_edges` | Prerequisite relationship between skills |
| `user_skills` | Mastery level and evidence per skill |
| `skill_snapshots` | Weekly level snapshots for the progress chart |
| `documents` | Imported file name, type, path, status, hash |
| `memory_items` | Entry `kind`, title, text, tags, author, hash |
| `memory_chunks` | Fragment of an entry with its Qdrant vector ID |
| `memory_writes` | Write log with agent, session, and reason |

### 13.5 Career

| Table | Contents |
| --- | --- |
| `master_profile` | Versioned master profile JSON |
| `cv_templates` | HTML and CSS template, fonts, similarity score, status |
| `job_postings` | URL, normalized URL, company, role, saved text, structured analysis |
| `companies` | Normalized name, dossier, sources, refresh date |
| `cv_reviews` | Posting, session, before and after indicators |
| `cv_modifications` | Section, before and after, reason, type, cited profile facts, status |
| `cv_versions` | Posting, template, JSON content, PDF path |
| `applications` | Posting, status, date, channel, CV version, next action |
| `application_events` | Timestamped application history |
| `contacts` | Name, role, link, related application |
| `reminders` | Type, due date, status, draft |
| `kit_items` | Type, content, and status of each kit item |
| `interviews` | Mode, duration, messages, debrief |
| `committee_runs` | CV version, posting, votes, verdict |
| `radar_runs` | Role, region, read and inaccessible postings, skill ranking |

### 13.6 System

| Table | Contents |
| --- | --- |
| `briefs` | Daily brief JSON |
| `web_cache` | URL hash, content, and date for each fetched page |

The first migration calls for indexes on `session_events(session_id, seq)`,
`tasks(planned_date)`, `flashcards(due_date)`, `job_postings(url_norm)`,
`job_postings(company_norm, title)`, and `reminders(due_at, status)`.

## 14. API

The REST API lives under `/api/v1`. A POST starts a session, a WebSocket streams its
events, and a POST answers an interrupt.

### 14.1 Agent session contract

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/sessions` | Start `{graph, input}` and return `session_id` within two seconds |
| GET | `/sessions/{id}` | Status, latest `seq`, pending interrupt |
| WS | `/sessions/{id}/stream?after_seq=N` | Stream and replay events from section 9.5 |
| POST | `/sessions/{id}/resume` | Answer an interrupt with `{interrupt_id, value}` |
| POST | `/sessions/{id}/message` | Send January's message during a debate |
| POST | `/sessions/{id}/pause`, `/cancel` | Pause or cancel |
| GET | `/sessions?graph=&status=` | Session history |

WebSockets carry server events to the client. January's actions use logged REST requests.

### 14.2 Endpoints by domain

The initial design groups routes by domain. See the generated contract for current paths and
schemas. [OpenAPI contract](contracts/openapi.json)

- **Goals and program.** `GET POST /goals`, `GET /goals/{id}/proposals`,
  `POST /proposals/{id}/choose`, `GET PATCH /programs/{id}`, `POST /programs/{id}/validate`,
  `GET /programs/{id}/export.pdf`, `GET /programs/{id}/export.ics`, `PATCH /tasks/{id}`.
- **Lessons and resources.** `GET /lessons/{id}`, `GET /lessons/{id}/pdf`, `GET /resources`,
  `PATCH /resources/{id}`.
- **Study.** `POST PATCH /study-sessions`, `GET /flashcards/due`, `POST /flashcards/{id}/review`,
  `GET /quizzes/{id}`, `POST /quizzes/{id}/attempts`.
- **Memory.** `POST GET /documents`, `GET POST PATCH DELETE /memory/items`,
  `POST /memory/search`, `GET /memory/map`, `GET /memory/stats`, `POST /memory/reindex`,
  `GET /memory/export`, `POST /capture`.
- **Skills.** `GET /skills/graph`, `GET /skills/{id}`, `GET /skills/compare`,
  `GET /skills/history`.
- **Profile and CV.** `GET PUT /profile`, `GET POST /cv/templates`, `POST /cv/reviews`,
  `PATCH /cv/modifications/{id}`, `POST /cv/reviews/{id}/generate`,
  `GET /cv/versions/{id}/pdf`.
- **Postings.** `POST /postings` accepts a URL or text and returns a duplicate check result.
  Use `GET /postings/{id}` and `GET /postings/{id}/gap` for details.
- **Applications.** `GET POST PATCH /applications`, `POST /applications/{id}/events`,
  `GET /reminders`, `PATCH /reminders/{id}`, `POST GET /applications/{id}/kit`,
  `GET /applications/{id}/kit.zip`, `POST /applications/{id}/interviews`, `POST /committee`.
- **Radar and projects.** `POST /radar/runs`, `GET /radar/latest`, `GET /projects`,
  `POST /projects/{id}/submit`.
- **Home.** `GET /brief/today`, `GET /activity`, `GET /journal`.
- **Settings.** `GET PUT /settings`, `GET POST DELETE /settings/api-keys`,
  `POST /settings/api-keys/{provider}/test`, `GET /settings/models`, `GET /costs`.
- **Sign-in.** `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout`,
  `GET /auth/me`.
- **Health.** `GET /health` checks the database, Qdrant, Ollama, SearXNG, Gotenberg, and model
  providers.

### 14.3 Conventions

- Use `snake_case` in JSON and serve OpenAPI documentation at `/api/docs`.
- Return errors as `{error: {code, message, details}}` with a readable English message.
- An HTTP request returns a `session_id` while the agent works in the background.
- `POST /postings` is idempotent by normalized URL.

## 15. Frontend

A light-theme single-page app with eight sidebar entries and a global capture field.

### 15.1 Navigation

| Entry | Screens |
| --- | --- |
| Home | Morning Brief, quick actions, activity feed |
| Learn | Goals, Council, Program, Lessons, Library |
| Study | Guided sessions, reviews, quizzes |
| Skills | Map, radar chart, progress, Portfolio |
| Career | Master profile, CV templates, reviews and versions, postings, gaps, Market Radar |
| Applications | Kanban, record, follow-ups, kits, interviews, hiring panel |
| Memory | Explorer, 2D map, query preview, documents |
| Settings | Models and keys, availability, style, costs, agent log |

### 15.2 Council screen

The Council and hiring panel (F19) share the same components.

- **Status bar.** Current stage (goal, research, debate, proposals, program), round, token
  count, and estimated cost.
- **Left column, 40%.** Live debate feed with one bubble per agent, its avatar, name, role,
  and color.
- Bubbles show agent activity and expandable tool calls.
- Numbered citations open their sources.
- **Right column, 60%.** Tabs for the Whiteboard, Sources, and Proposals.
- **Footer.** Message field and controls to pause, start another round, or move to proposals.
- An interrupt appears as an inline card with the question and options.
- Proposal cards sit side by side. January can choose one, merge paths, or request another round.

### 15.3 Key screen components

| Screen | Components |
| --- | --- |
| Program | Drag-and-drop `WeekCalendar`, `TaskList`, and before-and-after `PlanDiff` |
| Lesson | Reader, contents, progress, passage questions for the Tutor, and PDF download |
| CV | `MasterProfileForm`, `TemplateCompare`, `ReviewDiff`, indicators, and PDF preview |
| Applications | Kanban, record drawer, copyable `ReminderCard`, and `DuplicateAlert` |
| Memory | Filterable table, zoomable `VectorMap`, and `SearchBench` |
| Skills | `SkillGraph`, `SkillRadar`, and `ProgressChart` |
| Global | `CommandCapture` (Cmd+K), `ActivityFeed`, cost badge, and health indicator |

The CV comparison slider shows the original and render. The review diff offers approval
or refusal for each suggestion. Indicators compare the before and after versions.

### 15.4 Design

- Use one light theme with an off-white background, charcoal text, and one accent color.
- Give each agent a fixed color across bubbles, board annotations, and logs.
- Keep lesson text at 18 px and its column to 72 characters.
- Keep animations under 300 ms and disable them with `prefers-reduced-motion`.
- Meet AA contrast, support keyboard navigation and visible focus, and announce streaming
  text to screen readers.
- Design for screens at least 1,280 px wide and keep the app usable at 1,024 px.
- Each screen has an empty state with an action, a loading state, and an error state with retry.
- Unobtrusive notifications announce background results, such as “Lesson 3 ready.”

### 15.5 First launch

1. Check service health and show the embedding model download progress.
2. Enter and test an API key.
3. Import the CV and LinkedIn export, or skip this step.
4. Set availability.
5. Enter the first goal to start the Council.

## 16. Local Docker and a future Cloudflare deployment

Run `docker compose up` to start Tremplin. Section 16.3 maps local services to potential
Cloudflare equivalents. Section 16.4 lists checks needed before a migration.

### 16.1 Services

| Service | Image | Access | Role |
| --- | --- | --- | --- |
| `frontend` | Built from `./frontend` | `http://localhost:5173` | Interface |
| `backend` | Built from `./backend` | `http://localhost:8000` | API, agents, scheduled jobs |
| `qdrant` | `qdrant/qdrant` | `http://localhost:6333/dashboard` | Vectors and dashboard |
| `ollama` | `ollama/ollama` | Internal network | Embeddings |
| `ollama-init` | `ollama/ollama` | Exits after setup | Downloads `bge-m3` |
| `searxng` | `searxng/searxng` | Internal network | Web search |
| `gotenberg` | `gotenberg/gotenberg:8` | Internal network | HTML to PDF |

- Named volumes include `app_data` for SQLite, checkpoints, files, and the app secret,
  `qdrant_data`, and `ollama_data`.
- The backend reports readiness after the four services respond. `GET /health` shows their status.
- `docker-compose.dev.yml` adds hot reloading for the frontend and backend.
- On macOS, set `OLLAMA_BASE_URL` to a host Ollama instance to use the machine's GPU.

### 16.2 Repository root and startup

```text
tremplin/
  frontend/
  backend/             # Includes infra/searxng/settings.yml
  docker-compose.yml
  docker-compose.dev.yml
  .env.example
  README.md
  SPEC.md
```

```bash
cp .env.example .env     # Add at least one LLM key
docker compose up -d
# Open http://localhost:5173
```

```bash
# Model keys are enough for local mode.
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ZAI_API_KEY=
BRAVE_API_KEY=            # Optional
AUTH_MODE=local           # local or google
GOOGLE_CLIENT_ID=         # Required for AUTH_MODE=google
GOOGLE_CLIENT_SECRET=
```

### 16.3 Cloudflare equivalents

| Local | Cloudflare |
| --- | --- |
| FastAPI in Docker | [Python Workers][python-workers] |
| SQLite | D1 |
| Qdrant | Vectorize |
| Ollama with `bge-m3` | Workers AI with `@cf/baai/bge-m3` |
| File volume | R2 |
| WebSockets and session state | Durable Objects |
| APScheduler | Cron Triggers |
| Gotenberg | Browser Rendering or client-side PDF generation |
| SearXNG | Brave monthly credit or a separately hosted SearXNG instance |
| Frontend container | Workers Static Assets |

The initial design identifies Python Workers with FastAPI and LangChain as the backend target.
Provider interfaces, a SQLite-compatible schema, source text for memory, and a shared embedding
model make the migration manageable.

### 16.4 Checks before migrating

After the local MVP, verify the following in a dedicated phase.

1. LangGraph and its checkpointer on Python Workers. WebAssembly can limit native extensions.
2. CPU time for Python startup and LangChain imports within free-plan request limits.
3. `pdfplumber`, `pypdfium2`, and `trafilatura` in WebAssembly. PDF reading could move to the
   browser if needed.
4. The free Vectorize capacity, estimated at 4,880 chunks at 1,024 dimensions in the design.
5. The daily Workers AI embedding quota.
6. Long-running lesson and radar graphs within request duration limits.

If Python Workers cannot host the backend, keep the frontend, D1, Vectorize, and R2 on
Cloudflare and host the backend container separately.

## 17. Google sign-in, security, and privacy (F7)

Local mode starts with a single user and opens directly. An environment variable enables Google
sign-in.

### 17.1 Authentication modes

| Mode | Behavior |
| --- | --- |
| `AUTH_MODE=local` (default) | Creates one `local` user on first launch and opens the workspace |
| `AUTH_MODE=google` | Gives each user a workspace after Google sign-in |

- Google sign-in uses OAuth 2.0 authorization code with PKCE and `openid email profile` scopes.
- The session cookie uses `HttpOnly` and `SameSite=Lax` and lasts 30 days.
- The callback is `http://localhost:8000/api/v1/auth/google/callback`.
- An eligible account can claim the `local` user's data at the first switch to Google mode.
- `ALLOWED_EMAILS` accepts comma-separated email addresses, lowercased and trimmed. A value
  of `*` permits any account. An empty list prevents the backend from starting in Google mode.
  Claiming local data requires an account named in an explicit list.
- Google mode requires an OAuth client in the Google console. See the [setup guide](README.md).

### 17.2 Isolation and secrets

- Each row has `user_id`. Filter Qdrant by `user_id` and store files per user.
- Test each router for cross-account isolation.
- Encrypt API keys in the database. Keep the full key out of logs and browser responses.
- Log IDs and omit CV and document content.

### 17.3 Data sent outside the computer

| Data | Destination |
| --- | --- |
| Prompts, which can contain CV and profile content | Selected LLM provider |
| Search queries | Search engines used by SearXNG |
| Database, vectors, files, and embeddings | Local machine |

- First-run setup explains these destinations.
- The search tool strips names, email addresses, and phone numbers before sending queries.
- Saved contacts include only name, role, and a public link.
- Settings provides data export and deletion controls.

### 17.4 Application security

- **Untrusted content.** Prompts delimit web pages and imported documents and instruct agents
  to treat the contents as data.
- Agents use the tools in section 9. They have no general filesystem or terminal access.
- The page reader allows HTTP and HTTPS public addresses only.
- Remove scripts from HTML sent to Gotenberg.
- Limit imports to 20 MB and allowlisted file types.
- Restrict CORS to the frontend origin.
- January sends her own applications and messages.

## 18. Implementation plan and acceptance criteria

The MVP covers all 19 features in ten phases. Each phase ends with a working application
and an acceptance check.

### 18.1 Phases

- **Phase 0, Foundation.** Set up the repository, Compose, service health, SQLite and Alembic,
  settings, API keys, the three-provider model factory, and quality checks. After
  `docker compose up`, `/health` is healthy and the key test in Settings succeeds.
- **Phase 1, Agent runtime.** Add LangGraph execution, checkpointing, events, WebSocket replay,
  interrupts, cost logging, and a two-agent demo. The demo debate streams live, pauses for
  a question, and resumes after a backend restart.
- **Phase 2, Memory (F3).** Add embeddings, Qdrant, ingestion, memory tools, and exploration.
  Search finds an imported PDF and the explorer displays an agent write with its author.
- **Phase 3, Web search.** Add SearXNG, page extraction, caching, and source scoring.
  A query returns scored sources that were read and identifies unreadable pages.
- **Phase 4, Council and program (F1, F2).** Add the Council graph, whiteboard, proposals,
  program, calendar, lessons, PDFs, and resources. A goal yields an approved program with
  two weeks of lesson PDFs.
- **Phase 5, Study (F9, F13, F14, F15, F18).** Add quizzes, flashcards, guided study, the skill
  map, replanning, capture, and journal. A complete guided session updates skills and the plan.
- **Phase 6, CV (F4, F8).** Add the master profile, capture, review, PDF generation, and skill
  gap assessment. A pasted posting yields a tailored CV PDF with the original design.
- **Phase 7, Applications (F5, F10, F16, F19).** Add tracking, follow-ups, duplicate alerts,
  kits, panels, and interviews. The full application cycle works, including duplicate alerts.
- **Phase 8, Daily workflow (F11, F12, F17).** Add Radar, the brief, projects, activity, and
  scheduled jobs. Today's brief runs automatically and contains every section.
- **Phase 9, Finishing (advanced F6, F7).** Add Google sign-in, export and deletion, onboarding,
  end-to-end tests, and the README. The three original end-to-end flows pass.

### 18.2 Implementation instructions

- Read the entire specification and work phase by phase. At each phase end, run tests,
  check the acceptance criteria, and commit.
- Keep changes within the specification.
- If a library behaves differently from the design, follow its current official documentation
  and record the change in `DECISIONS.md`.
- At implementation time verify model IDs, LangGraph streaming, Excalidraw APIs, Gotenberg
  routes, and the Z.ai API URL.
- Follow the source organization rules in section 12.2 from the first file.
- Add service unit tests and an API test per router. The three initial end-to-end flows cover
  the Council, CV review, and application cycle with duplicate alerts and follow-ups.
- Use a deterministic fake model provider in tests.

### 18.3 Feature acceptance criteria

- **F1.** A goal produces a visible three-round debate among four agents, at least eight
  scored sources, an animated board, and two or three proposals. The next round addresses
  messages sent during the debate.
- **F2.** Each week has a theme, goal, deliverable, and dated tasks within 85% of the budget.
  Each module in the first two weeks has a lesson PDF and three to six working resource links.
- **F3.** Semantic search finds an imported PDF. Agent writes show author and reason. A new
  program can skip a topic already learned.
- **F4.** Each change has before and after text, a reason, and a master profile fact.
  Accepted changes are grounded in the profile. The PDF preserves page count and selectable text.
- **F5.** A previously applied-to posting triggers an alert with the date. A week without a
  reply produces a follow-up draft.
- **F6.** Switching Strong from Anthropic to GLM changes the next session's model in
  `llm_calls`. A key test reports an invalid key.
- **F7.** Google accounts see only their own data.
- **F8.** A posting produces a match score and gap table. Adding a gap to the schedule
  creates a replanning proposal.
- **F9.** A quiz score of 80% moves the skill to `validated`. A missed flashcard returns
  the following day.
- **F10.** A 15-minute interview asks posting-related questions and yields a scored debrief.
- **F11.** An approved project produces four drafts and moves the skill to `proven`.
- **F12.** The report counts read and blocked postings and ranks skills by frequency.
- **F13.** After a half-completed week, the review proposes a plan within the budget and
  shows before and after.
- **F14.** Guided study records time, checks off tasks, and creates flashcards from mistakes.
- **F15.** The map reflects a level change within a minute. Clicking a skill shows its evidence.
- **F16.** The kit produces seven editable items and a downloadable archive.
- **F17.** Today's brief is available on open with the study block, reviews, follow-ups, and
  postings.
- **F18.** A captured URL becomes a summarized memory entry. The app immediately flags
  unreadable URLs.
- **F19.** The panel gives four votes with reasons and three priority changes. Running it
  again after edits shows the difference.

**Criteria across features**

- One model key in `.env` and `docker compose up` are enough to start locally.
- Source files stay within 300 lines.
- A running session survives `docker compose restart backend`.
- Every LLM call is logged with its estimated cost.
- Text written on January's behalf draws facts from the master profile or memory.

## 19. Sources

The original design recorded these technical references on November 11, 2026.
Check the docs at implementation time.

**Pages consulted**

- Free allowance and paid plans. [Vectorize pricing][vectorize-pricing]
- Python Workers and support for FastAPI and LangChain. [Cloudflare Python Workers][python-workers]
- LangGraph interrupts, checkpointing, and resume. [LangGraph interrupts][langgraph-interrupts]
- SearXNG with LangChain and JSON output. [LangChain SearXNG docs][langchain-searxng]
- Changes to the Brave Search API free tier. [Implicator][brave-api-report]
- Mermaid conversion to Excalidraw. [Excalidraw conversion API][excalidraw-conversion]
- Applicant tracking system behavior. [Huntr survey][huntr-ats]

**Findings from search results**

- Apache 2.0 license and built-in dashboard. [Qdrant]
- Chromium routes for HTML-to-PDF conversion. [Gotenberg]
- Z.ai's OpenAI-compatible API URL.
- `bge-m3` uses 1,024 dimensions and supports over 100 languages on Ollama and Workers AI.

[python-workers]: https://developers.cloudflare.com/workers/languages/python/
[langchain-searxng]: https://docs.langchain.com/oss/python/integrations/providers/searx
[brave-api-report]:
  https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/
[excalidraw-conversion]: https://plus.excalidraw.com/docs/mermaid-to-excalidraw/api
[huntr-ats]: https://huntr.co/blog/how-applicant-tracking-systems-work
