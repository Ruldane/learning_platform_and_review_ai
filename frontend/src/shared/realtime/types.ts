import type { components } from "@/shared/api/schema";

/** Tous les types sont dérivés du contrat généré (`pnpm gen:api`). */
export type SessionEvent = components["schemas"]["SessionEvent"];
export type SessionEventType = SessionEvent["type"];
export type SessionStatus = components["schemas"]["SessionView"]["status"];
export type InterruptPayload = components["schemas"]["InterruptRequestedPayload"];
export type CostPayload = components["schemas"]["CostUpdatedPayload"];

/** Variante de `SessionEvent` pour un `type` donné (ex. `EventOf<"agent.token">`). */
export type EventOf<T extends SessionEventType> = Extract<SessionEvent, { type: T }>;

export interface ToolCallView {
  callId: string;
  tool: string;
  args: Record<string, unknown>;
  ok?: boolean;
  summary?: string;
}

export interface AgentTurn {
  kind: "turn";
  messageId: string;
  agent: string;
  intent?: string;
  text: string;
  streaming: boolean;
  tools: ToolCallView[];
  citations: unknown[];
}

export type FeedItem =
  | AgentTurn
  | { kind: "user"; seq: number; text: string }
  | { kind: "interrupt"; seq: number; interrupt: InterruptPayload; answered: boolean }
  | { kind: "event"; event: SessionEvent }; // autres types : registre de rendu

export interface SessionViewState {
  lastSeq: number;
  status: SessionStatus;
  feed: FeedItem[];
  pendingInterrupt: InterruptPayload | null;
  cost: CostPayload | null;
  error: { code: string; message: string } | null;
  currentAgent: string | null;
}

export type LocalAction =
  | { type: "interrupt.answered"; interruptId: string }
  | { type: "status.set"; status: SessionStatus };
