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
 * Statut affiché = celui du serveur. Deux sources : les événements du flux et les lectures REST
 * (ouverture du flux, réponse d'une action). Chacune porte une version (`seq`, puis `updated_at`
 * pour départager deux lectures du même `seq`) ; la plus récente gagne, l'autre est ignorée.
 * Pause et annulation ne publient aucun événement (D46 §7) : un événement publié juste avant elles
 * peut arriver après ; il ne lève donc jamais `paused` ni `cancelled` (seul `run.*`, final, le peut).
 */
const STICKY: ReadonlySet<SessionStatus> = new Set(["paused", "cancelled"]);

interface StatusChange {
  status: SessionStatus;
  pendingInterrupt: InterruptPayload | null;
  /** `run.completed` / `run.failed` : toujours vrais (l'issue n'est écrite que depuis `running`). */
  final?: boolean;
}

/** Statut posé par un événement de `seq` donné, si rien de plus récent n'est connu. */
export function statusFromEvent(
  state: SessionViewState,
  seq: number,
  change: StatusChange,
): SessionViewState {
  if (seq <= state.statusVersion.seq) return state; // une lecture REST plus récente fait foi
  if (STICKY.has(state.status) && !change.final) return state;
  // Rien ne change (`agent.started` d'une session déjà en cours) : l'événement ne prétend pas
  // mieux connaître le statut qu'une lecture REST faite juste avant lui.
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

/** Microsecondes d'un horodatage ISO du serveur (`Date.parse` s'arrête à la milliseconde). */
export function serverInstant(iso: string): number {
  const seconds = Date.parse(iso.replace(/\.\d+/, ""));
  if (Number.isNaN(seconds)) return 0;
  const fraction = /\.(\d+)/.exec(iso)?.[1] ?? "";
  return seconds * 1000 + Number(fraction.padEnd(6, "0").slice(0, 6));
}

export const snapshotOf = (view: SessionView): StatusSnapshot => ({
  status: view.status,
  lastSeq: view.last_seq,
  updatedAt: view.updated_at,
  pendingInterrupt: view.pending_interrupt,
});

/** La question en attente selon le serveur a sa carte (active), même si son événement manque. */
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
 * Applique une lecture REST, vraie au moins à `lastSeq` (le serveur lit le dernier `seq` avant le
 * statut, D56) : ignorée si les événements ou une lecture plus récente en savent plus.
 */
export function applySnapshot(state: SessionViewState, snap: StatusSnapshot): SessionViewState {
  const at = serverInstant(snap.updatedAt);
  const { seq, at: knownAt } = state.statusVersion;
  if (snap.lastSeq < seq || (snap.lastSeq === seq && at < knownAt)) return state;
  if (snap.lastSeq === seq && at === knownAt && snap.status === state.status) return state;
  const running = snap.status === "running";
  const feed = running ? state.feed : stopStreaming(state.feed); // plus rien n'écrit
  return {
    ...state,
    status: snap.status,
    pendingInterrupt: snap.pendingInterrupt,
    statusVersion: { seq: snap.lastSeq, at },
    currentAgent: running ? state.currentAgent : null,
    feed: withPendingCard(feed, snap.pendingInterrupt, snap.lastSeq),
  };
}
