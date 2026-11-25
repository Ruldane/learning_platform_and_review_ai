/** Repères des parcours hôtes. L’interface du fantôme est branchée par le registre. */
export interface LiveQuizPractice {
  elapsedMs: number;
  answered: number;
  total: number;
}

export interface QuizGhostProps {
  quizId: string;
  live?: LiveQuizPractice;
  currentAttemptId?: string;
}

export interface IdeGhostProps {
  sessionId: string;
  current: {
    id: string;
    status: "running" | "done" | "timeout" | "killed" | "error";
    elapsedMs: number | null;
    exitCode: number | null;
  } | null;
}

export function ideGhostPath(sessionId: string, runId: string): string {
  return `/code/${encodeURIComponent(sessionId)}?ghost=${encodeURIComponent(runId)}`;
}

export function quizGhostPath(quizId: string, attemptId: string): string {
  return `/study/quiz/${encodeURIComponent(quizId)}?ghost=${encodeURIComponent(attemptId)}`;
}
