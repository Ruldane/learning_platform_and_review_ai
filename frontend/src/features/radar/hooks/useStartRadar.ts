import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startRun } from "../api";
import type { RadarRunRequestView } from "../components/viewTypes";
import { launchErrors, openRunId } from "../errors";
import { radarKeys } from "../queryKeys";

/** Le relevé à suivre : celui qui vient d'être lancé, ou (409) celui qui tournait déjà. */
export interface StartedRun {
  runId: string;
  /** La session du 202 ; `null` pour un relevé déjà en cours (le serveur ne la redonne pas). */
  sessionId: string | null;
  resumed: boolean;
}

async function launch(request: RadarRunRequestView): Promise<StartedRun> {
  try {
    const started = await startRun({ role: request.role, zone: request.zone });
    return { runId: started.run_id, sessionId: started.session_id, resumed: false };
  } catch (error) {
    const open = openRunId(error);
    if (open) return { runId: open, sessionId: null, resumed: true };
    throw error;
  }
}

/**
 * « Lancer un relevé » : `start` résout au relevé à suivre. Un 409 `radar_in_progress` n'est pas
 * une panne (on suit le relevé en cours, `resumed`) ; un 409 `radar_role_required` ou un 422 se
 * rangent par champ dans `errors`.
 */
export function useStartRadar() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: launch,
    // Sans `await` : la page navigue vers le relevé avant que le dernier relevé soit relu.
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: radarKeys.all });
    },
  });
  const { mutateAsync } = mutation;
  return {
    start: (request: RadarRunRequestView) =>
      mutateAsync(request).then(
        (started) => started,
        () => null,
      ),
    /** Le relevé que le dernier lancement a donné à suivre (la page y navigue tout de suite). */
    started: mutation.data ?? null,
    pending: mutation.isPending,
    errors: mutation.isError ? launchErrors(mutation.error) : null,
  };
}
