import { t } from "@/shared/i18n/t";
import type {
  AnnotationView,
  ExerciseView,
  FreeSessionView,
  NoteView,
  UsageView,
} from "./components/viewTypes";
import type { Exercise, Note, RunProgress, SessionSummary, Usage } from "./types";

/** Les lignes `start` à `end` (à partir de 1) d'un texte ; `null` si elles n'existent pas. */
export function excerpt(text: string | undefined, start: number, end: number): string | null {
  if (text === undefined) return null;
  const lines = text.split("\n");
  if (start < 1 || end < start || end > lines.length) return null;
  return lines.slice(start - 1, end).join("\n");
}

/** Le nom sous lequel la note s'affiche : Claude (par le MCP) est toujours nommé « Claude ». */
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
 * Les notes dans l'ordre où elles ont été écrites. Un indice porte le niveau réel donné par le
 * back (`level`) ; à défaut (note ancienne), son rang parmi les indices de la séance.
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

/** Les annotations à poser dans la marge du fichier ouvert (une note périmée n'y est plus). */
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

/** Chaque exercice avec son état : réussi si une séance l'est, en cours si une séance existe. */
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

/** Une exécution est un échec si elle n'est pas finie sur le code 0. */
export function isFailedRun(progress: Pick<RunProgress, "status" | "exit_code">): boolean {
  if (progress.status === "running") return false;
  return progress.status !== "done" || (progress.exit_code ?? 0) !== 0;
}
