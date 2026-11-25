import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { startIntake } from "../api";
import { applicationsErrorMessage, openIntakeSessionId } from "../errors";

/**
 * `POST /applications/intake`: the one-sentence entry. `sessionId` is the followed session (the one
 * just started, or the one January resumes); a 409 `intake_in_progress` is not a
 * failure: `openSessionId` names the session already open, to resume or cancel.
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
    /** Resume the session already open. */
    resume: (id: string) => {
      reset();
      setSessionId(id);
    },
    /** The followed session is finished or abandoned: another one can be started. */
    leave: () => {
      reset();
      setSessionId(null);
    },
    pending: mutation.isPending,
    error: refused ? applicationsErrorMessage(mutation.error) : null,
  };
}
