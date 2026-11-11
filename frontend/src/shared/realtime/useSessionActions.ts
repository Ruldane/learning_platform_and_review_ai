import { useMutation } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { fr } from "@/shared/i18n/fr";
import { t } from "@/shared/i18n/t";
import {
  postCancel,
  postMessage,
  postPause,
  postResume,
  startSession,
  type SessionView,
} from "./sessionApi";
import { selectSession, useSessionStore } from "./sessionStore";
import { snapshotOf } from "./statusGate";

type SessionErrorCode = keyof typeof fr.sessions.errors;

const isSessionErrorCode = (code: string): code is SessionErrorCode =>
  Object.hasOwn(fr.sessions.errors, code);

/** Message français d'un échec d'action : codes connus (409, 503) traduits ici, sinon celui de l'API. */
export function sessionActionError(error: unknown): string {
  if (error instanceof ApiError && isSessionErrorCode(error.code)) {
    return t(`sessions.errors.${error.code}`);
  }
  return errorMessage(error);
}

export interface SessionActions {
  /** Répond à la question `interruptId` (ou reprend une pause avec `null`). `true` si accepté. */
  resume(interruptId: string | null, value: unknown): Promise<boolean>;
  sendMessage(text: string): Promise<boolean>;
  pause(): Promise<boolean>;
  cancel(): Promise<boolean>;
  pending: boolean;
  /** Message français du dernier échec, effacé par l'action suivante. */
  error: string | null;
}

type Action = () => Promise<void>;

/**
 * Actions de session par REST (le WebSocket ne fait que descendre). Une action en échec ne lève
 * pas : elle renvoie `false` et l'erreur est exposée dans `error` (jamais de dialogue bloquant).
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
    // La réponse REST est une lecture du statut : appliquée seulement si rien de plus récent
    // n'est arrivé par le flux (question suivante, fin), D56.
    const applyView = (updated: SessionView) =>
      store().local(sessionId, { type: "snapshot", snapshot: snapshotOf(updated) });
    return {
      resume: (interruptId, value) =>
        run(async () => {
          const updated = await postResume(sessionId, interruptId, value);
          // Garde : le direct a pu livrer la question suivante avant cette réponse REST.
          if (interruptId !== null && view().pendingInterrupt?.interrupt_id === interruptId) {
            store().local(sessionId, { type: "interrupt.answered", interruptId });
          }
          applyView(updated);
        }),
      // L'événement `user.message` renvoyé n'est pas ingéré : il arrivera par le flux, dans
      // l'ordre ; l'ingérer avant des `seq` plus petits encore en route les ferait ignorer.
      sendMessage: (text) => run(() => postMessage(sessionId, text)),
      pause: () => run(async () => applyView(await postPause(sessionId))),
      cancel: () => run(async () => applyView(await postCancel(sessionId))),
      pending: isPending,
      error: error ? sessionActionError(error) : null,
    };
  }, [sessionId, run, isPending, error]);
}

/** Lance une session et renvoie son identifiant ; lève une `ApiError` en cas d'échec. */
export function useStartSession(): (
  graph: string,
  input: Record<string, unknown>,
) => Promise<string> {
  const { mutateAsync } = useMutation({
    mutationFn: ({ graph, input }: { graph: string; input: Record<string, unknown> }) =>
      startSession(graph, input),
  });
  return useCallback((graph, input) => mutateAsync({ graph, input }), [mutateAsync]);
}
