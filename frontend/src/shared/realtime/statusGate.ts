import { stopStreaming } from "./feedHelpers";
import type { SessionView } from "./sessionApi";
import type {
  FeedItem,
  InterruptPayload,
  SessionStatus,
  SessionViewState,
  StatusSnapshot,
} from "./types";

/**
 * Displayed status = the server's. Two sources: stream events and REST reads
 * (stream opening, action response). Each carries a version (`seq`, then `updated_at`
 * to break ties between reads at the same `seq`); the most recent wins, the other is ignored.
 * Pause and cancel publish no event (D46 §7): an event published just before them
 * may arrive after; it therefore never raises `paused` or `cancelled` (only `run.*`, final, can).
 */
const STICKY: ReadonlySet<SessionStatus> = new Set(["paused", "cancelled", "expired"]);

interface StatusChange {
  status: SessionStatus;
  pendingInterrupt: InterruptPayload | null;
  /** `run.completed` / `run.failed`: always true (the outcome is only written from `running`). */
  final?: boolean;
}

/** Status set by an event of a given `seq`, if nothing more recent is known. */
export function statusFromEvent(
  state: SessionViewState,
  seq: number,
  change: StatusChange,
): SessionViewState {
  if (seq <= state.statusVersion.seq) return state; // a more recent REST read wins
  if (STICKY.has(state.status) && !change.final) return state;
  // Nothing changes (`agent.started` of a session already running): the event claims no
  // better knowledge of the status than a REST read made just before it.
  const samePending =
    state.pendingInterrupt?.interrupt_id === change.pendingInterrupt?.interrupt_id;
  if (change.status === state.status && samePending) return state;
  return {
    ...state,
    status: change.status,
    pendingInterrupt: change.pendingInterrupt,
    statusVersion: { seq, at: 0 },
  };
}

/** Microseconds of a server ISO timestamp (`Date.parse` stops at the millisecond). */
export function serverInstant(iso: string): number {
  const seconds = Date.parse(iso.replace(/\.\d+/, ""));
  if (Number.isNaN(seconds)) return 0;
  const fraction = /\.(\d+)/.exec(iso)?.[1] ?? "";
  return seconds * 1000 + Number(fraction.padEnd(6, "0").slice(0, 6));
}

export const snapshotOf = (view: SessionView): StatusSnapshot => ({
  status: view.status,
  playedBy: view.played_by,
  lastSeq: view.last_seq,
  updatedAt: view.updated_at,
  pendingInterrupt: view.pending_interrupt,
});

/** The server's pending question has its card (active), even if its event is missing. */
function withPendingCard(feed: FeedItem[], pending: InterruptPayload | null, seq: number) {
  if (!pending) return feed;
  const id = pending.interrupt_id;
  const index = feed.findIndex((i) => i.kind === "interrupt" && i.interrupt.interrupt_id === id);
  if (index >= 0) {
    return feed.map((i, n) =>
      n === index && i.kind === "interrupt" ? { ...i, answered: false } : i,
    );
  }
  return [...feed, { kind: "interrupt" as const, seq, interrupt: pending, answered: false }];
}

/**
 * Applies a REST read, true at least up to `lastSeq` (the server reads the last `seq` before
 * the status, D56): ignored if events or a more recent read know more.
 */
export function applySnapshot(state: SessionViewState, snap: StatusSnapshot): SessionViewState {
  const at = serverInstant(snap.updatedAt);
  const { seq, at: knownAt } = state.statusVersion;
  if (snap.lastSeq < seq || (snap.lastSeq === seq && at < knownAt)) return state;
  if (snap.lastSeq === seq && at === knownAt && snap.status === state.status) return state;
  const running = snap.status === "running";
  const feed = running ? state.feed : stopStreaming(state.feed); // nothing writes any more
  return {
    ...state,
    status: snap.status,
    playedBy: snap.playedBy,
    pendingInterrupt: snap.pendingInterrupt,
    statusVersion: { seq: snap.lastSeq, at },
    currentAgent: running ? state.currentAgent : null,
    feed: withPendingCard(feed, snap.pendingInterrupt, snap.lastSeq),
  };
}
