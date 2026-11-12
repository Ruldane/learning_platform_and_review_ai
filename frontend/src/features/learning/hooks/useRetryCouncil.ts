import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { retryCouncil } from "../api";
import { learningKeys } from "../queryKeys";
import { rereadSession, statusIn } from "./rereadSession";

function conflictNotice(failure: ApiError): string | null {
  if (failure.code === "goal_already_chosen") return t("learning.retry.alreadyChosen");
  if (failure.code !== "council_not_failed") return null;
  const status = statusIn(failure.details);
  return status === null
    ? t("learning.retry.notFailed")
    : t("learning.retry.notFailedStatus", { status: t(`session.status.${status}`) });
}

/**
 * Relance d'un Conseil en échec (`POST /goals/{id}/council`). Le 202 rend l'objectif avec sa
 * nouvelle session : la page la suit (elle se remonte sur `council_session_id`), les propositions
 * repartent de zéro et les tableaux de l'ancien Conseil ne s'affichent plus. Les refus 409
 * (`council_not_failed`, `goal_already_chosen`) se disent dans `notice`, puis l'objectif et la
 * session sont relus ; le reste va dans `error`.
 */
export function useRetryCouncil(goalId: string, sessionId: string) {
  const client = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({ mutationFn: () => retryCouncil(goalId) });
  const { mutateAsync } = mutation;

  const retry = useCallback(async () => {
    setNotice(null);
    setError(null);
    try {
      const started = await mutateAsync();
      // Plus rien de l'ancien lot ni de l'ancien tableau, même un instant.
      await client.resetQueries({ queryKey: learningKeys.proposals(goalId) });
      client.setQueryData(learningKeys.goal(goalId), started.goal);
      void client.invalidateQueries({ queryKey: learningKeys.boards(goalId) });
    } catch (failure) {
      const conflict = failure instanceof ApiError ? conflictNotice(failure) : null;
      if (conflict === null) return setError(errorMessage(failure));
      setNotice(conflict);
      await Promise.all([
        client.invalidateQueries({ queryKey: learningKeys.goal(goalId) }),
        rereadSession(sessionId),
      ]);
    }
  }, [client, goalId, sessionId, mutateAsync]);

  return { retry, pending: mutation.isPending, notice, error };
}
