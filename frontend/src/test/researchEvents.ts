import type { SessionEvent } from "@/shared/realtime/types";

const SOURCE_DEFAULTS = {
  title: "Titre",
  url: "https://exemple.fr/a",
  author: null,
  date: null,
  lang: "fr",
  score: null,
  source_id: null,
  status: "ok",
  verdict: null,
  reason: null,
  kind: "page",
  role: null,
};

/**
 * Fabrique d'événements de la recherche web pour les tests. Chaque appel de `researchEvents()`
 * repart d'un compteur `seq` à 1 : un test = une session.
 */
export function researchEvents(sessionId = "s1") {
  let seq = 0;
  const base = (agent: string | null = "scout") => {
    seq += 1;
    return { id: `e${seq}`, session_id: sessionId, seq, ts: "2026-11-12T10:00:00Z", agent };
  };
  return {
    toolCalled: (callId: string, tool: string, args: Record<string, unknown>): SessionEvent => ({
      ...base(),
      type: "tool.called",
      payload: { call_id: callId, tool, args },
    }),
    toolResult: (
      callId: string,
      ok: boolean,
      summary: string,
      tool = "web_search",
    ): SessionEvent => ({
      ...base(),
      type: "tool.result",
      payload: { call_id: callId, tool, ok, summary },
    }),
    sourceFound: (over: Record<string, unknown> = {}): SessionEvent =>
      ({
        ...base(),
        type: "source.found",
        payload: { ...SOURCE_DEFAULTS, ...over },
      }) as SessionEvent,
    completed: (): SessionEvent => ({
      ...base(null),
      type: "run.completed",
      payload: { summary: "ok" },
    }),
    failed: (message: string): SessionEvent => ({
      ...base(null),
      type: "run.failed",
      payload: { code: "search_unavailable", message },
    }),
  };
}
