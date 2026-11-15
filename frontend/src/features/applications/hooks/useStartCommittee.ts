import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startCommittee } from "../api";
import { applicationsErrorMessage, errorCode, openCommitteeRunId } from "../errors";
import { applicationsKeys } from "../queryKeys";

interface Started {
  runId: string;
  /** Un comité était déjà ouvert pour l'offre : on le suit. */
  resumed: boolean;
}

async function launch(cvVersionId: string): Promise<Started> {
  try {
    return { runId: (await startCommittee(cvVersionId)).run_id, resumed: false };
  } catch (error) {
    const open = openCommitteeRunId(error);
    if (open) return { runId: open, resumed: true };
    throw error;
  }
}

/**
 * « Lancer le comité » : `start` résout à l'identifiant de l'exécution à suivre. Un 409
 * `committee_in_progress` n'est pas une panne : on suit l'exécution ouverte (`resumed`).
 */
export function useStartCommittee(postingId: string | null) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: launch,
    onSuccess: () =>
      client.invalidateQueries({ queryKey: applicationsKeys.committees(postingId ?? "") }),
  });
  const { mutateAsync } = mutation;
  return {
    start: (cvVersionId: string) =>
      mutateAsync(cvVersionId).then(
        (started) => started,
        () => null,
      ),
    pending: mutation.isPending,
    resumed: mutation.data?.resumed ?? false,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
    /** Le profil validé manque : January doit le faire avant de lancer le comité. */
    profileMissing: mutation.isError && errorCode(mutation.error) === "profile_required",
  };
}
