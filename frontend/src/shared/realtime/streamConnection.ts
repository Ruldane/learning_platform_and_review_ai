import { ApiError } from "@/shared/api/errors";
import type { SessionView } from "./sessionApi";
import {
  CLOSE_FINISHED,
  CLOSE_NOT_FOUND,
  CLOSE_POLICY,
  MAX_RECONNECT_ATTEMPTS,
  parseEventFrame,
  reconnectDelay,
  sessionStreamUrl,
  type SocketFactory,
  type SocketLike,
} from "./socket";
import type { SessionEvent, SessionStatus } from "./types";

export type ConnectionState = "connecting" | "open" | "reconnecting" | "closed" | "failed";
/** Reason for an abort (`failed`): session not found, connection refused, server unreachable. */
export type StreamFailure = "not_found" | "refused" | "unreachable";

export interface StreamConnectionDeps {
  sessionId: string;
  createSocket: SocketFactory;
  fetchSession: (sessionId: string, signal?: AbortSignal) => Promise<SessionView>;
  /** Last applied `seq`, read again on each (re)connection. */
  lastSeq: () => number;
  onEvent: (event: SessionEvent) => void;
  /**
   * Session read over REST (stream opening, end, `refresh`): status and pending question from the
   * server; a pause or a cancellation publishes no event (D46 §7, D56).
   */
  onSnapshot: (view: SessionView) => void;
  onState: (state: ConnectionState, failure: StreamFailure | null) => void;
}

const TERMINAL: ReadonlySet<SessionStatus> = new Set(["completed", "failed", "cancelled", "expired"]);
export const isTerminalStatus = (status: SessionStatus): boolean => TERMINAL.has(status);

/**
 * A session stream: opens the WebSocket after the last `seq` and re-reads the session over REST
 * on each open, reconnects after an abnormal close (growing wait, capped retry count),
 * stops on 1000 / 4404 / 1008, or when the server says the session is over and all events
 * have been received. `dispose()` closes everything, with no callbacks.
 */
export class SessionStreamConnection {
  private readonly deps: StreamConnectionDeps;
  private socket: SocketLike | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private check: AbortController | null = null;
  private attempts = 0;
  private done = false;
  /** A re-read was requested during a read in progress: it starts as soon as that one ends. */
  private refreshQueued = false;

  constructor(deps: StreamConnectionDeps) {
    this.deps = deps;
  }

  start(): void {
    this.connect("connecting");
  }

  /**
   * Re-reads the session over REST. If a read is already running, the re-read is queued
   * (only one, however many requests) and started when it ends: its response
   * may predate the request (reconnection check, previous opening).
   */
  refresh(): void {
    if (this.done) return;
    if (this.check !== null) {
      this.refreshQueued = true;
      return;
    }
    this.readView((view) => this.deps.onSnapshot(view));
  }

  /** Teardown: socket closed, timers and requests cancelled, no more callbacks. */
  dispose(): void {
    this.done = true;
    this.clearPending();
    const socket = this.detach();
    socket?.close();
  }

  private connect(state: "connecting" | "reconnecting"): void {
    if (this.done) return;
    this.deps.onState(state, null);
    const url = sessionStreamUrl(this.deps.sessionId, this.deps.lastSeq());
    const socket = this.deps.createSocket(url);
    this.socket = socket;
    socket.onopen = () => this.opened();
    socket.onmessage = (e) => this.receive(e.data);
    socket.onclose = (e) => this.closed(e.code);
  }

  /**
   * The server accepted: retries start again from zero (a browser never reports `open`
   * for refusals before `accept`; 4404 is handled apart), then the status is re-read over REST.
   */
  private opened(): void {
    this.attempts = 0;
    this.deps.onState("open", null);
    this.refresh();
  }

  private receive(data: string): void {
    const event = parseEventFrame(data);
    if (event) this.deps.onEvent(event);
  }

  private closed(code: number): void {
    this.detach();
    if (this.done) return;
    if (code === CLOSE_FINISHED) {
      this.end("closed", null);
      this.refreshStatus();
    } else if (code === CLOSE_NOT_FOUND) {
      this.end("failed", "not_found");
    } else if (code === CLOSE_POLICY) {
      this.end("failed", "refused");
    } else {
      this.scheduleReconnect();
    }
  }

  /** 1006 and co.: the browser does not see the reason for a refusal, hence the retry cap. */
  private scheduleReconnect(): void {
    this.attempts += 1;
    if (this.attempts > MAX_RECONNECT_ATTEMPTS) {
      this.end("failed", "unreachable");
      return;
    }
    this.deps.onState("reconnecting", null);
    this.timer = setTimeout(() => {
      this.timer = null;
      this.connect("reconnecting");
    }, reconnectDelay(this.attempts));
    this.checkSession();
  }

  /** While waiting, asks the server whether the session still exists and whether it is over. */
  private checkSession(): void {
    this.readView(
      (view) => {
        // Over but events are still missing: reconnecting will replay them, then 1000.
        if (!isTerminalStatus(view.status) || view.last_seq > this.deps.lastSeq()) return;
        this.deps.onSnapshot(view);
        this.end("closed", null);
      },
      (error) => {
        if (error instanceof ApiError && error.status === 404) this.end("failed", "not_found");
        // Other failure (network, server stopped): the planned reconnection goes ahead.
      },
    );
  }

  /** After a normal end: final status (a cancelled session has no end event). */
  private refreshStatus(): void {
    // A failure leaves the status as it is: the stream is already complete.
    this.readView((view) => this.deps.onSnapshot(view));
  }

  /**
   * One REST read at a time: the previous one is abandoned. Callbacks are silent once the read
   * is abandoned (new read, `dispose`, stream abort); a read started after `end`
   * (final status after 1000) still answers. A queued re-read starts after the callbacks
   * of the ending read, unless the stream has ended in the meantime.
   */
  private readView(onView: (view: SessionView) => void, onError?: (error: unknown) => void) {
    const abort = this.newCheck();
    const settle = () => {
      if (this.check === abort) this.check = null;
    };
    this.deps.fetchSession(this.deps.sessionId, abort.signal).then(
      (view) => {
        settle();
        if (!abort.signal.aborted) onView(view);
        this.runQueuedRefresh(abort);
      },
      (error: unknown) => {
        settle();
        if (!abort.signal.aborted) onError?.(error);
        this.runQueuedRefresh(abort);
      },
    );
  }

  /** Starts the queued re-read once the read `finished` ends (and is not replaced). */
  private runQueuedRefresh(finished: AbortController): void {
    if (!this.refreshQueued || this.check !== null || finished.signal.aborted) return;
    this.refreshQueued = false;
    this.refresh();
  }

  private end(state: "closed" | "failed", failure: StreamFailure | null): void {
    this.done = true;
    this.clearPending();
    this.detach()?.close();
    this.deps.onState(state, failure);
  }

  private newCheck(): AbortController {
    this.check?.abort();
    this.check = new AbortController();
    return this.check;
  }

  private clearPending(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.refreshQueued = false;
    this.check?.abort();
    this.check = null;
  }

  /** Unplugs the current socket (no more callbacks) and hands it back to the caller. */
  private detach(): SocketLike | null {
    const socket = this.socket;
    this.socket = null;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
    }
    return socket;
  }
}
