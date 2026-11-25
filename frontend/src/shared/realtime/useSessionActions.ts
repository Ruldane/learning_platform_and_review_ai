import { useMutation } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { en } from "@/shared/i18n/en";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import {
  postCancel,
  postCommand,
  postMessage,
  postPause,
  postResume,
  startSession,
  type SessionView,
} from "./sessionApi";
import { selectSession, useSessionStore } from "./sessionStore";
import { snapshotOf } from "./statusGate";
import type { UserCommand } from "./types";

type SessionErrorCode = keyof typeof en.session.errors;

const isSessionErrorCode = (code: string): code is SessionErrorCode =>
  Object.hasOwn(en.session.errors, code);

/** French message for an action failure: known codes (409, 503) translated here, else the API's. */
export function sessionActionError(error: unknown): string {
  if (error instanceof ApiError && isSessionErrorCode(error.code)) {
    return t(`session.errors.${error.code}`);
  }
  return errorMessage(error);
}

export interface SessionActions {
  /** Answers question `interruptId` (or resumes a pause with `null`). `true` if accepted. */
  resume(interruptId: string | null, value: unknown): Promise<boolean>;
  sendMessage(text: string): Promise<boolean>;
  /** Debate command (REST, never the WebSocket); `true` if accepted. */
  sendCommand(command: NonNullable<UserCommand>): Promise<boolean>;
  pause(): Promise<boolean>;
  cancel(): Promise<boolean>;
  pending: boolean;
  /** French message of the last failure, cleared by the next action. */
  error: string | null;
}

type Action = () => Promise<void>;

/**
 * Session actions over REST (the WebSocket only goes down). A failed action does not throw:
 * it returns `false` and the error is exposed in `error` (never a blocking dialog).
 */
export function useSessionActions(sessionId: string): SessionActions {
  const { mutateAsync, isPending, error } = useMutation({
    mutationFn: (action: Action) => action(),
  });
  const run = useCallback(
    (action: Action) =>
      mutateAsync(action).then(
        () => true,
        () => false,
      ),
    [mutateAsync],
  );

  return useMemo(() => {
    const store = useSessionStore.getState;
    const view = () => selectSession(sessionId)(store());
    // The REST response is a status read: applied only if nothing more recent
    // came in over the stream (next question, end), D56.
    const applyView = (updated: SessionView) =>
      store().local(sessionId, { type: "snapshot", snapshot: snapshotOf(updated) });
    return {
      resume: (interruptId, value) =>
        run(async () => {
          const updated = await postResume(sessionId, interruptId, value);
          // Guard: the stream may have delivered the next question before this REST response.
          if (interruptId !== null && view().pendingInterrupt?.interrupt_id === interruptId) {
            store().local(sessionId, { type: "interrupt.answered", interruptId });
          }
          applyView(updated);
        }),
      // The returned `user.message` event is not ingested: it will arrive over the stream, in
      // order; ingesting it before smaller `seq` still in transit would make them be ignored.
      sendMessage: (text) => run(() => postMessage(sessionId, text)),
      sendCommand: (command) => run(() => postCommand(sessionId, command)),
      pause: () => run(async () => applyView(await postPause(sessionId))),
      cancel: () => run(async () => applyView(await postCancel(sessionId))),
      pending: isPending,
      error: error ? sessionActionError(error) : null,
    };
  }, [sessionId, run, isPending, error]);
}

/** Starts a session and returns its id; throws an `ApiError` on failure. */
export function useStartSession(): (
  graph: string,
  input: Record<string, unknown>,
  source?: RunSource,
) => Promise<string> {
  const { mutateAsync } = useMutation({
    mutationFn: ({
      graph,
      input,
      source,
    }: {
      graph: string;
      input: Record<string, unknown>;
      source?: RunSource;
    }) => startSession(graph, input, source),
  });
  return useCallback(
    (graph, input, source) => mutateAsync({ graph, input, source }),
    [mutateAsync],
  );
}
