import { t } from "@/shared/i18n/t";
import type {
  AnnotationView,
  ExerciseView,
  FreeSessionView,
  NoteView,
  UsageView,
} from "./components/viewTypes";
import type { Exercise, Note, RunProgress, SessionSummary, Usage } from "./types";

/** The lines `start` to `end` (from 1) of a text; `null` if they do not exist. */
export function excerpt(text: string | undefined, start: number, end: number): string | null {
  if (text === undefined) return null;
  const lines = text.split("\n");
  if (start < 1 || end < start || end > lines.length) return null;
  return lines.slice(start - 1, end).join("\n");
}

/** The name the note shows under: Claude (via the MCP) is always named « Claude ». */
function authorLabel(note: Note): string {
  if (note.origin !== "mcp") return note.author_label ?? t(`ide.authors.${note.author}`);
  const label = note.author_label;
  if (!label) return t("ide.authors.claude");
  return label.toLowerCase().includes("claude") ? label : t("ide.authors.claudeVia", { label });
}

function beforeText(note: Note, files: Record<string, string>): string | null {
  if (note.kind !== "proposal" || !note.file_path || note.line_start === null) return null;
  return excerpt(files[note.file_path], note.line_start, note.line_end ?? note.line_start);
}

/**
 * The notes in the order they were written. A hint carries the actual level given by the
 * backend (`level`); otherwise (old note), its rank among the session's hints.
 */
export function toNoteViews(notes: Note[], files: Record<string, string>): NoteView[] {
  const ordered = [...notes].sort((a, b) => a.created_at.localeCompare(b.created_at));
  let hints = 0;
  return ordered.map((note) => {
    if (note.kind === "hint") hints += 1;
    return {
      id: note.id,
      kind: note.kind,
      author: note.author,
      authorLabel: authorLabel(note),
      origin: note.origin,
      status: note.status,
      filePath: note.file_path,
      lineStart: note.line_start,
      lineEnd: note.line_end,
      content: note.content,
      replacement: note.replacement,
      before: beforeText(note, files),
      hintLevel: note.kind === "hint" ? (note.level ?? hints) : null,
    };
  });
}

/** The annotations to place in the open file's margin (a stale note is no longer there). */
export function toAnnotations(notes: NoteView[], filePath: string): AnnotationView[] {
  return notes
    .filter((n) => n.kind === "annotation" && n.status !== "stale" && n.filePath === filePath)
    .filter((n) => n.lineStart !== null)
    .map((n) => ({ id: n.id, line: n.lineStart ?? 1, text: n.content }));
}

export function toUsageView(usage: Usage): UsageView {
  return {
    sessionTokens: usage.session_tokens,
    dayTokens: usage.day_tokens,
    sessionCap: usage.session_cap,
    dayCap: usage.day_cap,
    onDemand: usage.mode_on_demand,
  };
}

/** Each exercise with its state: passed if a session is passed, in progress if a session exists. */
export function toExerciseViews(exercises: Exercise[], sessions: SessionSummary[]): ExerciseView[] {
  return exercises.map((exercise) => {
    const mine = sessions.filter((session) => session.exercise_id === exercise.id);
    const state = mine.some((s) => s.passed) ? "passed" : mine.length > 0 ? "doing" : "todo";
    return {
      id: exercise.id,
      title: exercise.title,
      statement: exercise.statement,
      origin: exercise.origin,
      topic: exercise.topic,
      state,
      sessionId: mine[0]?.id ?? null,
    };
  });
}

export function toFreeSessions(sessions: SessionSummary[]): FreeSessionView[] {
  return sessions
    .filter((session) => session.exercise_id === null)
    .map((session) => ({ id: session.id, title: session.title, passed: session.passed }));
}

/** A run is a failure if it did not finish with exit code 0. */
export function isFailedRun(progress: Pick<RunProgress, "status" | "exit_code">): boolean {
  if (progress.status === "running") return false;
  return progress.status !== "done" || (progress.exit_code ?? 0) !== 0;
}
