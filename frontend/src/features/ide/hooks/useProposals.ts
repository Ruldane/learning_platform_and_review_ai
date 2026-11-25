import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useAcceptNote, useRejectNote } from "./useNotes";

interface Draft {
  save: () => Promise<boolean>;
  discard: () => void;
}

/**
 * Accept or refuse a proposal. Before accepting, the code is saved: the server
 * compares the file fingerprint with the proposal's and refuses it (409) if the code changed.
 * Once accepted, the file is the one the server returns; local edits are dropped.
 * `onDone` returns focus to the teacher's list (the card leaves the waiting queue).
 */
export function useProposals(sessionId: string, draft: Draft, onDone: () => void) {
  const accept = useAcceptNote(sessionId);
  const reject = useRejectNote(sessionId);
  const [error, setError] = useState<string | null>(null);

  async function decide(noteId: string, decision: "accept" | "reject") {
    setError(null);
    try {
      if (decision === "reject") {
        await reject.mutateAsync(noteId);
      } else {
        if (!(await draft.save())) return setError(t("ide.proposal.saveFirst"));
        await accept.mutateAsync(noteId);
        draft.discard();
      }
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      onDone();
    }
  }
  return { decide, busy: accept.isPending || reject.isPending, error };
}
