import { useMutation, useQueryClient } from "@tanstack/react-query";
import { patchApplication, postEvent } from "../api";
import { applicationsErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { ApplicationDetail, ApplicationPatch, EventIn } from "../types";

function settle(write: Promise<unknown>, resetOther: () => void): Promise<boolean> {
  resetOther();
  return write.then(
    () => true,
    () => false,
  );
}

/** Les écritures d'une fiche ouverte ; chacune rend la fiche relue, qui remplace celle du cache. */
export function useUpdateApplication(applicationId: string) {
  const client = useQueryClient();
  const onSuccess = (detail: ApplicationDetail) => {
    client.setQueryData(applicationsKeys.one(applicationId), detail);
    // Le tableau, les indicateurs et les relances dues ont pu changer (statut, dates, contacts).
    void client.invalidateQueries({ queryKey: applicationsKeys.list });
    void client.invalidateQueries({ queryKey: applicationsKeys.stats });
    void client.invalidateQueries({ queryKey: applicationsKeys.reminders });
  };
  const patch = useMutation({
    mutationFn: (body: ApplicationPatch) => patchApplication(applicationId, body),
    onSuccess,
  });
  const event = useMutation({
    mutationFn: (body: EventIn) => postEvent(applicationId, body),
    onSuccess,
  });
  const failure = patch.error ?? event.error;
  return {
    /** Résolvent à `true` quand le serveur a pris l'écriture, `false` sur un refus (lisible dans `error`). */
    save: (body: ApplicationPatch) => settle(patch.mutateAsync(body), event.reset),
    record: (body: EventIn) => settle(event.mutateAsync(body), patch.reset),
    pending: patch.isPending || event.isPending,
    error: failure ? applicationsErrorMessage(failure) : null,
  };
}
