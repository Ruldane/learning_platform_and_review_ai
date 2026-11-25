export type NoteKind = "hint" | "explanation" | "annotation" | "proposal" | "reference" | "question";
export type NoteStatus = "open" | "accepted" | "rejected" | "stale";
export type NoteAuthor = "professor" | "claude" | "user";
export type RunKind = "run" | "check";
export type RunStatus = "running" | "done" | "timeout" | "killed" | "error";
export type ExerciseState = "todo" | "doing" | "passed";
export type ExerciseOrigin = "user" | "generated" | "claude";
export type Level = "beginner" | "intermediate" | "advanced";
export type TeachSkip = "cap_reached" | "on_demand" | "busy";
export type Origin = "app" | "mcp";

/** A teacher (or Claude) note, ready to display. */
export interface NoteView {
  id: string;
  kind: NoteKind;
  author: NoteAuthor;
  authorLabel: string;
  /** `mcp`: written by Claude (the page says so in full). */
  origin: Origin;
  status: NoteStatus;
  filePath: string | null;
  lineStart: number | null;
  lineEnd: number | null;
  content: string;
  /** The text the backend would apply (proposal): never applied by the front. */
  replacement: string | null;
  /** The targeted lines as they are in the file; `null` if they are no longer there. */
  before: string | null;
  /** Hint level (given by the teacher, otherwise its rank); `null` for other notes. */
  hintLevel: number | null;
}

/** A dot in the editor margin (Monaco decoration). */
export interface AnnotationView {
  id: string;
  line: number;
  text: string;
}

export interface UsageView {
  sessionTokens: number;
  dayTokens: number;
  sessionCap: number;
  dayCap: number;
  onDemand: boolean;
}

/** A run's output, as the page shows it. */
export interface OutputView {
  runId: string | null;
  kind: RunKind | null;
  /** `mcp`: started by Claude (« lancée par Claude »; it does not take focus). */
  origin: Origin;
  status: RunStatus | "idle";
  output: string;
  exitCode: number | null;
  durationMs: number | null;
  truncated: boolean;
  error: string | null;
}

export interface ExerciseView {
  id: string;
  title: string;
  statement: string;
  origin: ExerciseOrigin;
  topic: string | null;
  state: ExerciseState;
  /** The most recent session on the exercise, if any. */
  sessionId: string | null;
}

export interface FreeSessionView {
  id: string;
  title: string;
  passed: boolean;
}

export interface ExerciseDraft {
  title: string;
  statement: string;
  starter: string;
  tests: string;
}

export interface GenerateDraft {
  topic: string;
  level: Level;
}

export interface PreferencesView {
  auto: boolean;
  idle: boolean;
  /** `guide` steers with hints; `pair` thinks with you and may propose the fix. */
  style: "guide" | "pair";
  /** Claude (MCP) may write to your files; off by default, set here only. */
  claudeWrites: boolean;
}
