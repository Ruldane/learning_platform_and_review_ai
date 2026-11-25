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
 * « Request a revision »: resumes from the validation stop point with
 * `{ action: "revise", note }` (`POST /sessions/{id}/resume`). The Strategist writes a new
 * version; the page follows the session (`useProgramSession`), then re-reads the program.
 */
export function useReviseProgram(programId: string) {
  const client = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { mutateAsync, isPending } = useMutation({
    mutationFn: ({ sessionId, interruptId, note }: Revision) =>
      postResume(sessionId, interruptId, { action: "revise", note }),
  });

  /** `true` if the request was sent. */
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
