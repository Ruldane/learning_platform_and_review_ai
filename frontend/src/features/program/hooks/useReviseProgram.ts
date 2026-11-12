import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { ApiError } from "@/shared/api/errors";
import { postResume } from "@/shared/realtime/sessionApi";
import { sessionActionError } from "@/shared/realtime/useSessionActions";
import { programKeys } from "../queryKeys";
import { conflictNotice } from "./conflictNotice";

interface Revision {
  sessionId: string;
  interruptId: string;
  note: string;
}

/**
 * « Demander une révision » : reprise du point d'arrêt de validation avec
 * `{ action: "revise", note }` (`POST /sessions/{id}/resume`). Le Stratège écrit une nouvelle
 * version ; la page suit la session (`useProgramSession`) puis relit le programme.
 */
export function useReviseProgram(programId: string) {
  const client = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { mutateAsync, isPending } = useMutation({
    mutationFn: ({ sessionId, interruptId, note }: Revision) =>
      postResume(sessionId, interruptId, { action: "revise", note }),
  });

  /** `true` si la demande est partie. */
  const revise = useCallback(
    async (revision: Revision): Promise<boolean> => {
      setNotice(null);
      setError(null);
      let sent = true;
      try {
        await mutateAsync(revision);
      } catch (failure) {
        sent = false;
        const conflict = failure instanceof ApiError ? conflictNotice(failure) : null;
        if (conflict === null) setError(sessionActionError(failure));
        else setNotice(conflict);
      }
      await Promise.all([
        client.invalidateQueries({ queryKey: programKeys.detail(programId) }),
        client.invalidateQueries({ queryKey: programKeys.sessions }),
      ]);
      return sent;
    },
    [mutateAsync, client, programId],
  );
  return { revise, pending: isPending, notice, error };
}
