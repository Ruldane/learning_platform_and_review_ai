import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { chooseProposal } from "../api";
import { learningKeys } from "../queryKeys";
import { rereadSession, statusIn } from "./rereadSession";

function conflictNotice(failure: ApiError): string | null {
  if (failure.code === "proposal_outdated") return t("learning.choose.outdated");
  if (failure.code !== "council_not_waiting") return null;
  const status = statusIn(failure.details);
  return status === null
    ? t("learning.choose.notWaiting")
    : t("learning.choose.notWaitingStatus", { status: t(`session.status.${status}`) });
}

/**
 * Le choix du parcours (`POST /proposals/{id}/choose`, D87). Les conflits ne sont pas des erreurs
 * bloquantes : `proposal_outdated` (un nouveau lot est arrivé) et `council_not_waiting` (le Conseil
 * n'attend plus ce choix) relisent les propositions et le statut et se disent dans `notice` ;
 * `already_chosen` (double clic) dit que la date de début n'a pas changé. Le même choix après
 * l'échec du Stratège le relance (`already_chosen` faux) : l'objectif relu donne la nouvelle
 * session du programme, suivie aussitôt. Le reste va dans `error`.
 */
export function useChooseProposal(goalId: string, sessionId: string) {
  const client = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: ({ proposalId, mixWith }: { proposalId: string; mixWith: string | null }) =>
      chooseProposal(proposalId, mixWith),
  });
  const { mutateAsync } = mutation;

  const refresh = useCallback(
    () =>
      Promise.all([
        client.invalidateQueries({ queryKey: learningKeys.proposals(goalId) }),
        client.invalidateQueries({ queryKey: learningKeys.goal(goalId) }),
        rereadSession(sessionId),
      ]),
    [client, goalId, sessionId],
  );

  const choose = useCallback(
    async (proposalId: string, mixWith: string | null = null) => {
      setNotice(null);
      setError(null);
      try {
        const done = await mutateAsync({ proposalId, mixWith });
        if (done.already_chosen) setNotice(t("learning.choose.alreadyChosen"));
      } catch (failure) {
        const conflict = failure instanceof ApiError ? conflictNotice(failure) : null;
        if (conflict === null) return setError(errorMessage(failure));
        setNotice(conflict);
      }
      await refresh();
    },
    [mutateAsync, refresh],
  );
  return { choose, pending: mutation.isPending, notice, error };
}
