import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startKit } from "../api";
import { applicationsErrorMessage, errorCode, openKitSessionId } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { KitOut } from "../types";

/** Un lancement accepté (202), ou la session que le serveur dit déjà ouverte (409 `kit_in_progress`). */
async function launch(applicationId: string): Promise<{ sessionId: string; resumed: boolean }> {
  try {
    return { sessionId: (await startKit(applicationId)).session_id, resumed: false };
  } catch (error) {
    const open = openKitSessionId(error);
    if (open) return { sessionId: open, resumed: true };
    throw error;
  }
}

/**
 * « Générer le kit » : `sessionId` est la session à suivre ; un 409 `kit_in_progress` n'est pas une
 * panne (on suit la session ouverte, `resumed`). Le kit en cache passe tout de suite à « en cours ».
 */
export function useStartKit(applicationId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => launch(applicationId),
    onSuccess: ({ sessionId }) => {
      client.setQueryData<KitOut>(applicationsKeys.kit(applicationId), (kit) =>
        kit ? { ...kit, running: true, session_id: sessionId } : kit,
      );
      void client.invalidateQueries({ queryKey: applicationsKeys.kit(applicationId) });
    },
  });
  const { mutateAsync } = mutation;
  return {
    /** Résout à `true` quand une session tourne pour ce kit. */
    start: () =>
      mutateAsync().then(
        () => true,
        () => false,
      ),
    sessionId: mutation.data?.sessionId ?? null,
    resumed: mutation.data?.resumed ?? false,
    pending: mutation.isPending,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
    /** Le profil validé manque : January doit le faire avant de relancer. */
    profileMissing: mutation.isError && errorCode(mutation.error) === "profile_required",
  };
}
