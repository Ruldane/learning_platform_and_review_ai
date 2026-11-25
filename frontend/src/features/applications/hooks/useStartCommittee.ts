import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startCommittee } from "../api";
import { applicationsErrorMessage, errorCode, openCommitteeRunId } from "../errors";
import { applicationsKeys } from "../queryKeys";

interface Started {
  runId: string;
  /** A committee was already open for the posting: it is followed. */
  resumed: boolean;
}

async function launch(cvVersionId: string, source?: RunSource): Promise<Started> {
  try {
    return { runId: (await startCommittee(cvVersionId, source)).run_id, resumed: false };
  } catch (error) {
    const open = openCommitteeRunId(error);
    if (open) return { runId: open, resumed: true };
    throw error;
  }
}

/**
 * « Lancer le comité »: `start` resolves to the identifier of the run to follow. A 409
 * `committee_in_progress` is not a failure: the open run is followed (`resumed`).
 */
export function useStartCommittee(postingId: string | null) {
  const provider = useLaunchSource();
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (cvVersionId: string) => launch(cvVersionId, provider.source),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: applicationsKeys.committees(postingId ?? "") }),
  });
  const { mutateAsync } = mutation;
  return {
    launchMenu: provider.menu,
    start: (cvVersionId: string) =>
      mutateAsync(cvVersionId).then(
        (started) => started,
        () => null,
      ),
    pending: mutation.isPending,
    resumed: mutation.data?.resumed ?? false,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
    /** The validated profile is missing: January must do it before starting the committee. */
    profileMissing: mutation.isError && errorCode(mutation.error) === "profile_required",
  };
}
