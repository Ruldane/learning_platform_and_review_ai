import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startKit } from "../api";
import { applicationsErrorMessage, errorCode, openKitSessionId } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { KitOut } from "../types";

/** An accepted start (202), or the open session the server reports (409 `kit_in_progress`). */
async function launch(
  applicationId: string,
  source?: RunSource,
): Promise<{ sessionId: string; resumed: boolean }> {
  try {
    return { sessionId: (await startKit(applicationId, source)).session_id, resumed: false };
  } catch (error) {
    const open = openKitSessionId(error);
    if (open) return { sessionId: open, resumed: true };
    throw error;
  }
}

/**
 * « Générer le kit »: `sessionId` is the session to follow; a 409 `kit_in_progress` is not a
 * failure (the open session is followed, `resumed`). The cached kit goes to « en cours » at once.
 */
export function useStartKit(applicationId: string) {
  const provider = useLaunchSource();
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => launch(applicationId, provider.source),
    onSuccess: ({ sessionId }) => {
      client.setQueryData<KitOut>(applicationsKeys.kit(applicationId), (kit) =>
        kit ? { ...kit, running: true, session_id: sessionId } : kit,
      );
      void client.invalidateQueries({ queryKey: applicationsKeys.kit(applicationId) });
    },
  });
  const { mutateAsync } = mutation;
  return {
    launchMenu: provider.menu,
    /** Resolves to `true` when a session is running for this kit. */
    start: () =>
      mutateAsync().then(
        () => true,
        () => false,
      ),
    sessionId: mutation.data?.sessionId ?? null,
    resumed: mutation.data?.resumed ?? false,
    pending: mutation.isPending,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
    /** The validated profile is missing: January must do it before relaunching. */
    profileMissing: mutation.isError && errorCode(mutation.error) === "profile_required",
  };
}
