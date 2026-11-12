import type { SessionEvent } from "@/shared/realtime/types";

type Interrupt = Extract<SessionEvent, { type: "interrupt.requested" }>["payload"];

type Base = (agent?: string | null) => {
  id: string;
  session_id: string;
  seq: number;
  ts: string;
  agent: string | null;
};

function debateEvents(base: Base) {
  return {
    started: (agent: string, intent = "je prépare"): SessionEvent => ({
      ...base(agent),
      type: "agent.started",
      payload: { intent, step: "draft" },
    }),
    message: (messageId: string, text: string, agent = "moderator"): SessionEvent => ({
      ...base(agent),
      type: "agent.message",
      payload: { message_id: messageId, text, citations: [] },
    }),
    userMessage: (text: string): SessionEvent => ({
      ...base(),
      type: "user.message",
      payload: { text, command: null },
    }),
    interrupt: (
      kind: string,
      interruptId: string,
      over: Partial<Interrupt> = {},
    ): SessionEvent => ({
      ...base("moderator"),
      type: "interrupt.requested",
      payload: { interrupt_id: interruptId, kind, question: "Question ?", options: [], ...over },
    }),
  };
}

function researchOf(base: Base) {
  return {
    toolCalled: (
      callId: string,
      tool: string,
      args: Record<string, unknown> = {},
    ): SessionEvent => ({
      ...base("scout"),
      type: "tool.called",
      payload: { call_id: callId, tool, args },
    }),
    sourceFound: (over: Record<string, unknown> = {}): SessionEvent =>
      ({
        ...base("scout"),
        type: "source.found",
        payload: {
          title: "Titre",
          url: "https://exemple.fr/a",
          author: null,
          date: null,
          lang: "fr",
          score: 80,
          source_id: null,
          status: "ok",
          verdict: "kept",
          reason: null,
          kind: "page",
          role: null,
          ...over,
        },
      }) as SessionEvent,
  };
}

function outcomeEvents(base: Base) {
  return {
    boardUpdate: (
      boardId: string | null,
      step: number,
      over: { kind?: string | null; title?: string | null; mermaid?: string } = {},
    ): SessionEvent =>
      ({
        ...base("scribe"),
        type: "board.update",
        payload: {
          board_id: boardId,
          step,
          kind: "domain_map",
          title: "Carte du domaine",
          mermaid: "flowchart TD\n  A --> B",
          ...over,
        },
      }) as SessionEvent,
    proposalReady: (proposalId: string, title: string): SessionEvent => ({
      ...base("strategist"),
      type: "proposal.ready",
      payload: { proposal_id: proposalId, title },
    }),
    artifactReady: (kind: string, artifactId: string, url: string | null): SessionEvent => ({
      ...base("strategist"),
      type: "artifact.ready",
      payload: { artifact_id: artifactId, kind, title: "Programme", url },
    }),
    cost: (): SessionEvent => ({
      ...base(),
      type: "cost.updated",
      payload: { tokens_in: 1200, tokens_out: 300, cost_usd: 0.02, cap_tokens: 300000 },
    }),
    completed: (): SessionEvent => ({
      ...base(),
      type: "run.completed",
      payload: { summary: "ok" },
    }),
    failed: (message = "Le modèle n'a pas répondu."): SessionEvent => ({
      ...base(),
      type: "run.failed",
      payload: { code: "internal_error", message },
    }),
  };
}

/**
 * Fabrique d'événements du Conseil pour les tests. Chaque appel de `councilEvents(sessionId)`
 * repart d'un compteur `seq` à 1 : un test = une session.
 */
export function councilEvents(sessionId = "c1") {
  let seq = 0;
  const base: Base = (agent = null) => {
    seq += 1;
    return { id: `e${seq}`, session_id: sessionId, seq, ts: "2026-11-12T10:00:00Z", agent };
  };
  return { ...debateEvents(base), ...researchOf(base), ...outcomeEvents(base) };
}
