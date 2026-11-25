import type { SalaryScenarioView } from "./salaryScenarioView";

/**
 * View types for the application components: independent of the API contract (D34). The pages
 * (7.13) convert the server's responses (`ApplicationOut`, `ReminderOut`, `EventOut`,
 * `ApplicationStatsOut`, `AlertOut`) into these shapes.
 */

/** The eight statuses, in tracking board column order (`STATUS_ORDER` on the backend). */
export const STATUS_ORDER = [
  "to_apply",
  "applied",
  "followed_up",
  "interview",
  "offer",
  "rejected",
  "no_answer",
  "withdrawn",
] as const;

export type StatusView = (typeof STATUS_ORDER)[number];

/** The six application channels, in dropdown order. */
export const CHANNEL_ORDER = [
  "company_site",
  "job_board",
  "linkedin",
  "email",
  "referral",
  "other",
] as const;

export type ChannelView = (typeof CHANNEL_ORDER)[number];

/** A day, `AAAA-MM-JJ`. */
export type DayString = string;

/** An application record, as the cards and the table display it. */
export interface ApplicationView {
  id: string;
  company: string;
  title: string;
  status: StatusView;
  channel: ChannelView | null;
  appliedOn: DayString | null;
  interviewOn: DayString | null;
  nextAction: string | null;
  nextActionOn: DayString | null;
  /** Reminders now due and not yet handled. */
  dueReminders: number;
}

/** A record's contact; `id` is empty for a contact added by hand, not yet saved. */
export interface ContactView {
  id: string;
  name: string;
  role: string | null;
  url: string | null;
}

export type EventKindView =
  "created" | "status" | "note" | "reminder" | "kit" | "interview" | "committee" | "version";

/** A line of the chronological thread; `at` is an ISO instant. */
export interface EventView {
  id: string;
  kind: EventKindView;
  at: string;
  statusFrom: StatusView | null;
  statusTo: StatusView | null;
  text: string | null;
}

export type ReminderKindView = "linkedin_7" | "email_14" | "close_21" | "thanks" | "news_7";

/** A reminder to handle: the app sends nothing, January copies the draft. */
export interface ReminderView {
  id: string;
  applicationId: string;
  kind: ReminderKindView;
  dueOn: DayString;
  company: string;
  title: string;
  contact: ContactView | null;
  /** LinkedIn search offered when the record has no contact. */
  linkedinSearchUrl: string | null;
  draft: string;
}

/** The indicators; `responseRate` is a share between 0 and 1. */
export interface StatsView {
  byStatus: Record<StatusView, number>;
  responseRate: number | null;
  meanResponseDays: number | null;
  dueReminders: number;
}

export const MAX_CONTACTS = 10;

/** A pre-filled field of the confirmation of a record read from a sentence. */
export interface ConfirmationFieldView {
  id: string;
  label: string;
  required: boolean;
  maxLength: number;
  value: string;
}

/** An outcome offered by the server (`create`, `distinct`, `open`, `cancel`). */
export interface ConfirmationOptionView {
  value: string;
  label: string;
}

/** The « Je crée cette fiche ? » question from the tracking Assistant, with the record it read. */
export interface ConfirmationView {
  question: string;
  fields: ConfirmationFieldView[];
  options: ConfirmationOptionView[];
  /** Why the question is asked again (the previous answer could not be taken), if applicable. */
  reason?: string | null;
}

/** The seven kit pieces, in the order the server returns them. */
export const KIT_KINDS = [
  "cv",
  "letter",
  "linkedin",
  "followups",
  "form_answers",
  "company_brief",
  "pitch",
] as const;
export type KitKindView = (typeof KIT_KINDS)[number];

/** `pending`: not yet filed; `to_check`: to re-read before use; `failed`: not produced. */
export type KitStatusView = "pending" | "ready" | "to_check" | "failed";

/** A page read for the company file; `rank` is its `[n]` number in the text. */
export interface KitSourceView {
  rank: number;
  url: string;
  title: string | null;
}

/** A kit piece as the page shows it. */
export interface KitPieceView {
  kind: KitKindView;
  status: KitStatusView;
  content: string;
  /** The terms the profile does not state (« à vérifier » piece). */
  flags: string[];
  /** The salary answers left to January. */
  salaryFields: number;
  words: number | null;
  sources: KitSourceView[];
  /** January edited it: a new kit run keeps it as it is. */
  edited: boolean;
  /** The readable reason for a failed piece. */
  error: string | null;
  updatedAt: string | null;
}

/** What saving a change returns to the piece: the new status, or the refusal. */
export type KitSaveResult = { ok: true; status: KitStatusView } | { ok: false; message: string };

/** The four interview formats. */
export const INTERVIEW_MODES = ["behavioral", "technical", "case", "mixed", "salary"] as const;
export type InterviewModeView = (typeof INTERVIEW_MODES)[number];

/** The three durations: 4, 7 or 10 main questions. */
export const INTERVIEW_DURATIONS = [15, 30, 45] as const;
export type InterviewDurationView = (typeof INTERVIEW_DURATIONS)[number];

export const INTERVIEW_LANGUAGES = ["fr", "en"] as const;
export type InterviewLanguageView = (typeof INTERVIEW_LANGUAGES)[number];

/**
 * `running`: in progress; `done`: written debrief; `stopped`: stopped before any answer;
 * `debrief_failed`: answers kept, debrief not written; `failed`: session ended with no result.
 */
export type InterviewStatusView = "running" | "done" | "stopped" | "debrief_failed" | "failed";

/** The four debrief scores, in display order. */
export const SCORE_KEYS = ["clarity", "structure", "technical_depth", "role_fit"] as const;
export type ScoreKeyView = (typeof SCORE_KEYS)[number];

/** An interview question, January's answer, the possible follow-up and the score (1 to 5). */
export interface ExchangeView {
  index: number;
  question: string;
  answer: string;
  followUp: string | null;
  followUpAnswer: string | null;
  note: number;
  /** The model could not score this answer: the score is not to be read. */
  unrated: boolean;
}

/** The points a good answer to question `index` would have earned. */
export interface ExpectedView {
  index: number;
  points: string[];
}

export interface DebriefDataView {
  /** `null`: the model did not return this score (it is not a 0). */
  scores: { key: ScoreKeyView; value: number | null }[];
  strengths: string[];
  fixes: string[];
  weakestIndex: number;
  improvedAnswer: string;
  /** The questions scored 2 at most, those for which a review card was made. */
  missed: number[];
  expected: ExpectedView[];
  /** The questions the model could not score. */
  unrated: number[];
}

/** A mock interview as the pages show it. */
export interface InterviewView {
  salary?: SalaryScenarioView;
  id: string;
  applicationId: string | null;
  postingId: string | null;
  role: string | null;
  mode: InterviewModeView;
  durationMin: InterviewDurationView;
  /** The number of main questions (4, 7 or 10 depending on the duration). */
  questionCount: number;
  language: InterviewLanguageView;
  sessionId: string;
  status: InterviewStatusView;
  exchanges: ExchangeView[];
  debrief: DebriefDataView | null;
  /** The terms the profile does not state in the improved answer. */
  flags: string[];
  cardsCreated: number;
  createdAt: string;
}

/** The four committee personas, in the order the committee names them. */
export const PERSONA_ORDER = ["ats_reader", "recruiter", "manager", "colleague"] as const;

export type PersonaView = (typeof PERSONA_ORDER)[number];

export type VoteValueView = "yes" | "no" | "maybe";

export type CommitteeStatusView = "running" | "done" | "failed" | "stopped";

/** A persona's reasoned vote, with its main objection. */
export interface VoteView {
  persona: PersonaView;
  vote: VoteValueView;
  objection: string;
  reason: string;
}

/** A committee objection, ranked (the first is the most important); `personas`: who raises it. */
export interface ObjectionView {
  text: string;
  personas: PersonaView[];
}

/** A proposed change; `needsSkill`: it requires a skill the profile does not state. */
export interface ChangeView {
  text: string;
  persona: PersonaView;
  needsSkill: boolean;
  terms: string[];
}

/** A persona's vote at the previous run and at this one. */
export interface VoteChangeView {
  persona: PersonaView;
  before: VoteValueView;
  after: VoteValueView;
}

/** Before and after: what the previous run said, what has changed since. */
export interface CommitteeDiffView {
  votes: VoteChangeView[];
  resolved: string[];
  added: string[];
}

/** A committee run as the page shows it. */
export interface CommitteeView {
  id: string;
  cvVersionId: string;
  postingId: string;
  sessionId: string;
  status: CommitteeStatusView;
  verdict: VoteValueView | null;
  votes: VoteView[];
  objections: ObjectionView[];
  changes: ChangeView[];
  /** `null`: first run of the posting (or not finished). */
  diff: CommitteeDiffView | null;
}
