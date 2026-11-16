import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { submitProject } from "../api";
import { errorCode, openReviewSession, submitFailure } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProjectOut, SubmissionView } from "../types";

/** Le rendu parti : sa session, ou (409 `review_in_progress`) celle de l'évaluation qui tourne déjà. */
export interface Submitted {
  sessionId: string | null;
  resumed: boolean;
}

async function send(projectId: string, submission: SubmissionView): Promise<Submitted> {
  try {
    const started = await submitProject(projectId, submission);
    return { sessionId: started.session_id, resumed: false };
  } catch (error) {
    const open = openReviewSession(error);
    if (open !== undefined) return { sessionId: open, resumed: true };
    throw error;
  }
}

/**
 * « Rendre le projet » : un rendu tient du clic jusqu'à la relecture du projet (statut `reviewing`) :
 * un second clic (double clic, Entrée répétée) n'envoie rien, ni pendant l'envoi, ni dans l'instant
 * où le formulaire est encore là alors que le projet lu n'attend plus de rendu. Un 409 `review_in_progress` n'est pas
 * une panne (on suit l'évaluation ouverte, `resumed`) ; un 422 se range par champ dans `refusal`,
 * tout autre refus (409 `project_not_ready` ou `project_validated`, 413, 503) dans `message`.
 */
export function useSubmitProject(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: (submission: SubmissionView) => send(projectId, submission),
    // Attendu : le formulaire reste verrouillé jusqu'à ce que le statut `reviewing` soit lu.
    onSuccess: () => client.invalidateQueries({ queryKey: projectKeys.one(projectId) }),
    onError: (error) => {
      // Le projet a changé sous nos yeux (validé, énoncé encore absent) : la page se relit.
      const code = errorCode(error);
      if (code === "project_validated" || code === "project_not_ready") {
        void client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
      }
    },
  });
  const { mutateAsync, error, isError } = mutation;
  const failure = useMemo(() => (isError ? submitFailure(error) : null), [isError, error]);
  const submit = (submission: SubmissionView) => {
    const status = client.getQueryData<ProjectOut>(projectKeys.one(projectId))?.status;
    const open = status === undefined || status === "todo" || status === "to_redo";
    if (sending.current || !open) return Promise.resolve(null);
    sending.current = true;
    return mutateAsync(submission)
      .catch(() => null)
      .finally(() => {
        sending.current = false;
      });
  };
  return {
    submit,
    pending: mutation.isPending,
    /** Ce que le serveur refuse, par champ ; stable tant que l'erreur ne change pas. */
    refusal: failure?.refusal ?? null,
    message: failure?.general ?? null,
    resumed: mutation.data?.resumed ?? false,
  };
}
