export type NoteKind = "hint" | "explanation" | "annotation" | "proposal" | "reference";
export type NoteStatus = "open" | "accepted" | "rejected" | "stale";
export type NoteAuthor = "professor" | "claude" | "user";
export type RunKind = "run" | "check";
export type RunStatus = "running" | "done" | "timeout" | "killed" | "error";
export type ExerciseState = "todo" | "doing" | "passed";
export type ExerciseOrigin = "user" | "generated" | "claude";
export type Level = "beginner" | "intermediate" | "advanced";
export type TeachSkip = "cap_reached" | "on_demand" | "busy";

/** Une note du professeur (ou de Claude) prête à l'affichage. */
export interface NoteView {
  id: string;
  kind: NoteKind;
  author: NoteAuthor;
  authorLabel: string;
  status: NoteStatus;
  filePath: string | null;
  lineStart: number | null;
  lineEnd: number | null;
  content: string;
  /** Le texte que le back appliquerait (proposition) : jamais appliqué par le front. */
  replacement: string | null;
  /** Les lignes visées telles qu'elles sont dans le fichier ; `null` si elles n'y sont plus. */
  before: string | null;
  /** Rang de l'indice parmi les indices de la séance (1, 2, 3…) ; `null` pour une autre note. */
  hintLevel: number | null;
}

/** Une pastille dans la marge de l'éditeur (décoration Monaco). */
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

/** La sortie d'une exécution, telle que la page la montre. */
export interface OutputView {
  runId: string | null;
  kind: RunKind | null;
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
  /** La séance la plus récente de l'exercice, s'il y en a une. */
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
}
