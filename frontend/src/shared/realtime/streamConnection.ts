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
  /**
   * Session lue en REST (ouverture du flux, fin, `refresh`) : statut et question en attente du
   * serveur ; une pause ou une annulation ne publient aucun événement (D46 §7, D56).
   */
  onSnapshot: (view: SessionView) => void;
  onState: (state: ConnectionState, failure: StreamFailure | null) => void;
}

const TERMINAL: ReadonlySet<SessionStatus> = new Set(["completed", "failed", "cancelled"]);
export const isTerminalStatus = (status: SessionStatus): boolean => TERMINAL.has(status);

/**
 * Un flux de session : ouvre le WebSocket après le dernier `seq` et relit la session en REST à
 * chaque ouverture, reconnecte sur fermeture anormale (attente croissante, nombre d'essais
 * plafonné), s'arrête sur 1000 / 4404 / 1008 ou quand le serveur dit la session terminée et déjà
 * toute reçue. `dispose()` coupe tout, sans rappel.
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

  /** Relit la session en REST, sauf si une lecture est déjà en cours (sa réponse suffira). */
  refresh(): void {
    if (this.done || this.check !== null) return;
    this.readView((view) => this.deps.onSnapshot(view));
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
    socket.onopen = () => this.opened();
    socket.onmessage = (e) => this.receive(e.data);
    socket.onclose = (e) => this.closed(e.code);
  }

  /**
   * Le serveur a accepté : les essais repartent de zéro (un navigateur ne signale jamais `open`
   * pour un refus avant `accept`, et 4404 est traité à part), puis le statut est relu en REST.
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
    this.readView(
      (view) => {
        // Terminée mais des événements manquent encore : la reconnexion les rejouera, puis 1000.
        if (!isTerminalStatus(view.status) || view.last_seq > this.deps.lastSeq()) return;
        this.deps.onSnapshot(view);
        this.end("closed", null);
      },
      (error) => {
        if (error instanceof ApiError && error.status === 404) this.end("failed", "not_found");
        // Autre échec (réseau, serveur arrêté) : la reconnexion prévue suit son cours.
      },
    );
  }

  /** Après une fin normale : statut final (une session annulée n'a pas d'événement de fin). */
  private refreshStatus(): void {
    // Un échec laisse le statut tel quel : le flux est déjà complet.
    this.readView((view) => this.deps.onSnapshot(view));
  }

  /**
   * Une lecture REST à la fois : la précédente est abandonnée. Rappels muets une fois la lecture
   * abandonnée (nouvelle lecture, `dispose`, abandon du flux) ; une lecture lancée après `end`
   * (statut final après 1000) répond encore.
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
      },
      (error: unknown) => {
        settle();
        if (!abort.signal.aborted) onError?.(error);
      },
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
