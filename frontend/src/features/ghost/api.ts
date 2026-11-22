import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

export async function fetchQuizGhost(
  quizId: string,
  attemptId: string | null,
  signal?: AbortSignal,
) {
  return unwrap(
    await api.GET("/quizzes/{quiz_id}/ghost", {
      params: { path: { quiz_id: quizId }, query: { attempt_id: attemptId ?? undefined } },
      signal,
    }),
  );
}

export async function fetchIdeGhost(sessionId: string, runId: string | null, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/ide/sessions/{session_id}/ghost", {
      params: { path: { session_id: sessionId }, query: { run_id: runId ?? undefined } },
      signal,
    }),
  );
}
