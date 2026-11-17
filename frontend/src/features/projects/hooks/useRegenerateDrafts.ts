import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { regenerateDrafts } from "../api";
import { errorCode, openReviewSession, readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";

/** La session qui écrit les brouillons, ou (409 `review_in_progress`) celle qui tournait déjà. */
interface Regenerating {
  sessionId: string | null;
}

async function send(projectId: string): Promise<Regenerating> {
  try {
    return { sessionId: (await regenerateDrafts(projectId)).session_id };
  } catch (error) {
    const open = openReviewSession(error);
    if (open !== undefined) return { sessionId: open };
    throw error;
  }
}

/**
 * « Régénérer les brouillons » (`POST /projects/{id}/drafts`, 202) pour un projet validé qui n'en a
 * pas : un clic tient jusqu'à la réponse (un double clic n'envoie rien de plus). 409
 * `drafts_present` ou `project_not_validated` : le projet a changé sous nos yeux, la page se relit.
 * `sessionId` est la session à suivre, tant que la page n'en a pas reçu d'autre.
 */
export function useRegenerateDrafts(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const reread = () => client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
  const mutation = useMutation({
    mutationFn: () => send(projectId),
    onSuccess: reread,
    onError: (error) => {
      const code = errorCode(error);
      if (code === "drafts_present" || code === "project_not_validated") void reread();
    },
  });
  const { mutateAsync } = mutation;
  return {
    regenerate: () => {
      if (sending.current) return;
      sending.current = true;
      void mutateAsync()
        .catch(() => null)
        .finally(() => {
          sending.current = false;
        });
    },
    pending: mutation.isPending,
    sessionId: mutation.data?.sessionId ?? null,
    error: mutation.isError ? readableMessage(mutation.error) : null,
  };
}

export type DraftsRegeneration = ReturnType<typeof useRegenerateDrafts>;
