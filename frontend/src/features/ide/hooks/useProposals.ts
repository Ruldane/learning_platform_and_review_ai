import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useAcceptNote, useRejectNote } from "./useNotes";

interface Draft {
  save: () => Promise<boolean>;
  discard: () => void;
}

/**
 * Accepter ou refuser une proposition. Avant d'accepter, le code est enregistré : le serveur
 * compare l'empreinte du fichier à celle de la proposition et la refuse (409) si le code a changé.
 * Accepté, le fichier est celui que le serveur rend ; les retouches locales sont jetées.
 * `onDone` rend le focus à la liste du professeur (la carte disparaît de la file d'attente).
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
