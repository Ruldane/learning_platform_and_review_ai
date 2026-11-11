import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fetchSession as fetchSessionRest } from "./sessionApi";
import { browserSocket, type SocketFactory } from "./socket";
import { selectEvents, selectSession, useSessionStore } from "./sessionStore";
import { snapshotOf } from "./statusGate";
import {
  SessionStreamConnection,
  type ConnectionState,
  type StreamConnectionDeps,
  type StreamFailure,
} from "./streamConnection";
import type { InterruptPayload, SessionEvent, SessionStatus, SessionViewState } from "./types";

export type { ConnectionState, StreamFailure } from "./streamConnection";

export interface SessionStreamOptions {
  /** Fabrique de socket (un faux en test). Lue à chaque (re)connexion ; la changer ne rouvre rien. */
  createSocket?: SocketFactory;
  /** Lecture REST de la session (statut, dernier `seq`). */
  fetchSession?: StreamConnectionDeps["fetchSession"];
}

export interface SessionStream {
  events: SessionEvent[];
  view: SessionViewState;
  status: SessionStatus;
  pendingInterrupt: InterruptPayload | null;
  connection: ConnectionState;
  /** Message français quand le flux a abandonné (`connection === "failed"`). */
  error: string | null;
  /** Raison de l'abandon : une session introuvable ne se « réessaie » pas. */
  failure: StreamFailure | null;
  /** Relance le flux après un abandon (bouton « Réessayer »). */
  retry: () => void;
}

interface Link {
  sessionId: string | null;
  state: ConnectionState;
  failure: StreamFailure | null;
}

type StreamIo = Pick<StreamConnectionDeps, "createSocket" | "fetchSession">;

/** Branche une connexion de flux sur le store de l'application et la démarre. */
function openStream(
  sessionId: string,
  io: { current: StreamIo },
  onState: StreamConnectionDeps["onState"],
): SessionStreamConnection {
  const store = useSessionStore.getState;
  const view = () => selectSession(sessionId)(store());
  const connection: SessionStreamConnection = new SessionStreamConnection({
    sessionId,
    createSocket: (url) => io.current.createSocket(url),
    fetchSession: (id, signal) => io.current.fetchSession(id, signal),
    lastSeq: () => view().lastSeq,
    onEvent: (event) => {
      store().ingest(sessionId, [event]);
      const { status, statusVersion } = view();
      if (status === "paused" && event.seq > statusVersion.seq) connection.refresh();
    },
    onSnapshot: (session) =>
      store().local(sessionId, { type: "snapshot", snapshot: snapshotOf(session) }),
    onState,
  });
  connection.start();
  return connection;
}

/**
 * Suit une session en direct : ouvre le WebSocket après le dernier `seq` du store, ingère chaque
 * événement (le réducteur ignore les doublons d'un rejeu), relit le statut en REST à chaque
 * ouverture, reconnecte sur fermeture anormale. Pendant une pause, un événement plus récent que
 * le statut connu (publié avant la pause, ou session reprise ailleurs) fait relire la session.
 * Démontage : socket fermé, minuteries coupées, aucune reconnexion (StrictMode compris).
 */
export function useSessionStream(
  sessionId: string | null,
  options?: SessionStreamOptions,
): SessionStream {
  const createSocket = options?.createSocket ?? browserSocket;
  const fetchSession = options?.fetchSession ?? fetchSessionRest;
  const [attempt, setAttempt] = useState(0);
  const [link, setLink] = useState<Link>({ sessionId: null, state: "closed", failure: null });
  // Options lues par référence : une fonction recréée à chaque rendu ne relance pas le flux.
  const io = useRef<StreamIo>({ createSocket, fetchSession });
  useEffect(() => {
    io.current = { createSocket, fetchSession };
  });

  useEffect(() => {
    if (!sessionId) return undefined;
    const connection = openStream(sessionId, io, (state, failure) =>
      setLink({ sessionId, state, failure }),
    );
    return () => connection.dispose();
  }, [sessionId, attempt]);

  const id = sessionId ?? "";
  const view = useSessionStore(useMemo(() => selectSession(id), [id]));
  const events = useSessionStore(useMemo(() => selectEvents(id), [id]));
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  // Tant que le flux de cette session n'a rien signalé, il est en cours d'ouverture.
  const current = link.sessionId === sessionId ? link : null;
  const connection: ConnectionState = !sessionId ? "closed" : (current?.state ?? "connecting");
  const failure = current?.state === "failed" ? current.failure : null;

  return {
    events,
    view,
    status: view.status,
    pendingInterrupt: view.pendingInterrupt,
    connection,
    error: failure ? t(`sessions.stream.${failure}`) : null,
    failure,
    retry,
  };
}
