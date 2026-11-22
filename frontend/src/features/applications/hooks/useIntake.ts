import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { startIntake } from "../api";
import { applicationsErrorMessage, openIntakeSessionId } from "../errors";

/**
 * `POST /applications/intake` : la saisie en une phrase. `sessionId` est la session suivie (celle
 * qui vient de démarrer, ou celle que January reprend) ; un 409 `intake_in_progress` n'est pas une
 * panne : `openSessionId` nomme la session déjà ouverte, à reprendre ou à annuler.
 */
export function useIntake() {
  const launch = useLaunchSource();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (text: string) => startIntake(text, launch.source),
    onSuccess: (started) => setSessionId(started.session_id),
  });
  const { mutate, reset } = mutation;
  const openSessionId = mutation.isError ? openIntakeSessionId(mutation.error) : null;
  const refused = mutation.isError && openSessionId === null;
  return {
    launchMenu: launch.menu,
    start: (text: string) => mutate(text),
    sessionId,
    openSessionId,
    /** Reprendre la session déjà ouverte. */
    resume: (id: string) => {
      reset();
      setSessionId(id);
    },
    /** La session suivie est finie ou abandonnée : on peut en commencer une autre. */
    leave: () => {
      reset();
      setSessionId(null);
    },
    pending: mutation.isPending,
    error: refused ? applicationsErrorMessage(mutation.error) : null,
  };
}
