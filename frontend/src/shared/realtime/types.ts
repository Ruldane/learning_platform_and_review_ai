import type { components } from "@/shared/api/schema";

/** All types are derived from the generated contract (`pnpm gen:api`). */
export type SessionEvent = components["schemas"]["SessionEvent"];
export type SessionEventType = SessionEvent["type"];
export type SessionStatus = components["schemas"]["SessionView"]["status"];
export type InterruptPayload = components["schemas"]["InterruptRequestedPayload"];
export type CostPayload = components["schemas"]["CostUpdatedPayload"];
export type Citation = components["schemas"]["Citation"];
/** Debate command (D82); `null`: a free message. */
export type UserCommand = components["schemas"]["UserMessagePayload"]["command"];

/** Variant of `SessionEvent` for a given `type` (e.g. `EventOf<"agent.token">`). */
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
  /** Stopped without `agent.message` (pause, restart, end): the restarting agent replaces it. */
  interrupted?: boolean;
  tools: ToolCallView[];
  citations: Citation[];
}

export type FeedItem =
  | AgentTurn
  | { kind: "user"; seq: number; text: string; command: UserCommand }
  | { kind: "interrupt"; seq: number; interrupt: InterruptPayload; answered: boolean }
  | { kind: "event"; event: SessionEvent }; // other types: render registry

/** Status read over REST (`GET /sessions/{id}` or action response), true up to `lastSeq`. */
export interface StatusSnapshot {
  playedBy?: string | null;
  status: SessionStatus;
  lastSeq: number;
  /** The server's `updated_at`: breaks ties between two reads at the same `lastSeq`. */
  updatedAt: string;
  pendingInterrupt: InterruptPayload | null;
}

/** Source of the displayed status: the event's or REST read's `seq`, server instant (µs). */
export interface StatusVersion {
  seq: number;
  at: number;
}

export interface SessionViewState {
  playedBy?: string | null;
  lastSeq: number;
  status: SessionStatus;
  statusVersion: StatusVersion;
  feed: FeedItem[];
  pendingInterrupt: InterruptPayload | null;
  cost: CostPayload | null;
  error: { code: string; message: string } | null;
  currentAgent: string | null;
}

export type LocalAction =
  | { type: "interrupt.answered"; interruptId: string }
  | { type: "snapshot"; snapshot: StatusSnapshot };
