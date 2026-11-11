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
/** Raison d'un abandon (`failed`) : session introuvable, connexion refusée, serveur injoignable. */
export type StreamFailure = "not_found" | "refused" | "unreachable";

export interface StreamConnectionDeps {
  sessionId: string;
  createSocket: SocketFactory;
  fetchSession: (sessionId: string, signal?: AbortSignal) => Promise<SessionView>;
  /** Dernier `seq` appliqué, relu à chaque (re)connexion. */
  lastSeq: () => number;
  onEvent: (event: SessionEvent) => void;
  /** Statut lu en REST : une annulation, par exemple, ne publie aucun événement. */
  onStatus: (status: SessionStatus) => void;
  onState: (state: ConnectionState, failure: StreamFailure | null) => void;
}

const TERMINAL: ReadonlySet<SessionStatus> = new Set(["completed", "failed", "cancelled"]);
export const isTerminalStatus = (status: SessionStatus): boolean => TERMINAL.has(status);

/**
 * Un flux de session : ouvre le WebSocket après le dernier `seq`, reconnecte sur fermeture anormale
 * (attente croissante, nombre d'essais plafonné), s'arrête sur 1000 / 4404 / 1008 ou quand le
 * serveur dit la session terminée et déjà toute reçue. `dispose()` coupe tout, sans rappel.
 */
export class SessionStreamConnection {
  private readonly deps: StreamConnectionDeps;
  private socket: SocketLike | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private check: AbortController | null = null;
  private attempts = 0;
  private done = false;

  constructor(deps: StreamConnectionDeps) {
    this.deps = deps;
  }

  start(): void {
    this.connect("connecting");
  }

  /** Démontage : socket fermé, minuteries et requêtes annulées, plus aucun rappel. */
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
    socket.onopen = () => this.deps.onState("open", null);
    socket.onmessage = (e) => this.receive(e.data);
    socket.onclose = (e) => this.closed(e.code);
  }

  private receive(data: string): void {
    const event = parseEventFrame(data);
    if (!event) return;
    this.attempts = 0; // connexion utile : les essais repartent de zéro
    this.deps.onEvent(event);
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

  /** 1006 & co. : le navigateur ne voit pas la raison d'un refus, d'où le plafond d'essais. */
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

  /** Pendant l'attente, demande au serveur si la session existe encore et si elle est finie. */
  private checkSession(): void {
    const abort = this.newCheck();
    this.deps.fetchSession(this.deps.sessionId, abort.signal).then(
      (view) => {
        if (abort.signal.aborted || this.done) return;
        // Terminée mais des événements manquent encore : la reconnexion les rejouera, puis 1000.
        if (!isTerminalStatus(view.status) || view.last_seq > this.deps.lastSeq()) return;
        this.deps.onStatus(view.status);
        this.end("closed", null);
      },
      (error: unknown) => {
        if (abort.signal.aborted || this.done) return;
        if (error instanceof ApiError && error.status === 404) this.end("failed", "not_found");
        // Autre échec (réseau, serveur arrêté) : la reconnexion prévue suit son cours.
      },
    );
  }

  /** Après une fin normale : statut final (une session annulée n'a pas d'événement de fin). */
  private refreshStatus(): void {
    const abort = this.newCheck();
    this.deps.fetchSession(this.deps.sessionId, abort.signal).then(
      (view) => {
        if (!abort.signal.aborted) this.deps.onStatus(view.status);
      },
      () => undefined, // le flux est déjà complet ; seul le statut affiché pourrait être en retard
    );
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
    this.check?.abort();
    this.check = null;
  }

  /** Débranche le socket courant (plus aucun rappel) et le rend à l'appelant. */
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
