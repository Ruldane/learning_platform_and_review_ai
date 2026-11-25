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
  /** Socket factory (a fake in tests). Read on each (re)connection; changing it reopens nothing. */
  createSocket?: SocketFactory;
  /** REST read of the session (status, last `seq`). */
  fetchSession?: StreamConnectionDeps["fetchSession"];
}

export interface SessionStream {
  events: SessionEvent[];
  view: SessionViewState;
  status: SessionStatus;
  pendingInterrupt: InterruptPayload | null;
  connection: ConnectionState;
  /** French message when the stream gave up (`connection === "failed"`). */
  error: string | null;
  /** Reason for giving up: a missing session cannot be retried. */
  failure: StreamFailure | null;
  /** Restarts the stream after giving up (« Réessayer » button). */
  retry: () => void;
}

interface Link {
  sessionId: string | null;
  state: ConnectionState;
  failure: StreamFailure | null;
}

type StreamIo = Pick<StreamConnectionDeps, "createSocket" | "fetchSession">;

/** Plugs a stream connection into the app store and starts it. */
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
 * Follows a session live: opens the WebSocket after the store's last `seq`, ingests each
 * event (the reducer ignores duplicates from a replay), re-reads the status over REST on each
 * open, reconnects after an abnormal close. During a pause, an event more recent than the
 * known status (published before the pause, or session resumed elsewhere) triggers a re-read.
 * Teardown: socket closed, timers stopped, no reconnection (StrictMode included).
 */
export function useSessionStream(
  sessionId: string | null,
  options?: SessionStreamOptions,
): SessionStream {
  const createSocket = options?.createSocket ?? browserSocket;
  const fetchSession = options?.fetchSession ?? fetchSessionRest;
  const [attempt, setAttempt] = useState(0);
  const [link, setLink] = useState<Link>({ sessionId: null, state: "closed", failure: null });
  // Options read by reference: a function recreated on each render does not restart the stream.
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
  // While this session's stream has reported nothing, it is still opening.
  const current = link.sessionId === sessionId ? link : null;
  const connection: ConnectionState = !sessionId ? "closed" : (current?.state ?? "connecting");
  const failure = current?.state === "failed" ? current.failure : null;

  return {
    events,
    view,
    status: view.status,
    pendingInterrupt: view.pendingInterrupt,
    connection,
    error: failure ? t(`session.stream.${failure}`) : null,
    failure,
    retry,
  };
}
