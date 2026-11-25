import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { startRun } from "../api";
import type { RadarRunRequestView } from "../components/viewTypes";
import { launchErrors, openRunId } from "../errors";
import { radarKeys } from "../queryKeys";

/** The sweep to follow: the one just launched, or (409) the one already running. */
export interface StartedRun {
  runId: string;
  /** The 202 session; `null` for a sweep already running (the server does not return it). */
  sessionId: string | null;
  resumed: boolean;
}

async function launch(request: RadarRunRequestView, source?: RunSource): Promise<StartedRun> {
  try {
    const started = await startRun({ role: request.role, zone: request.zone }, source);
    return { runId: started.run_id, sessionId: started.session_id, resumed: false };
  } catch (error) {
    const open = openRunId(error);
    if (open) return { runId: open, sessionId: null, resumed: true };
    throw error;
  }
}

/**
 * « Lancer un relevé »: `start` resolves to the sweep to follow. A 409 `radar_in_progress` is not
 * an error (the running sweep is followed, `resumed`); a 409 `radar_role_required` or a 422 are
 * sorted by field into `errors`.
 */
export function useStartRadar() {
  const client = useQueryClient();
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: ({ request, source }: { request: RadarRunRequestView; source?: RunSource }) =>
      launch(request, source),
    // Without `await`: the page navigates to the sweep before the latest sweep is re-read.
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: radarKeys.all });
    },
  });
  const { mutateAsync } = mutation;
  return {
    launchMenu: provider.menu,
    start: (request: RadarRunRequestView) =>
      mutateAsync({ request, source: provider.source }).then(
        (started) => started,
        () => null,
      ),
    /** The sweep the last launch gave to follow (the page navigates there at once). */
    started: mutation.data ?? null,
    pending: mutation.isPending,
    errors: mutation.isError ? launchErrors(mutation.error) : null,
  };
}
