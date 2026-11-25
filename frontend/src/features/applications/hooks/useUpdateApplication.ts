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

/** Writes to an open record; each returns the re-read record, which replaces the cached one. */
export function useUpdateApplication(applicationId: string) {
  const client = useQueryClient();
  const onSuccess = (detail: ApplicationDetail) => {
    client.setQueryData(applicationsKeys.one(applicationId), detail);
    // The board, the indicators and the reminders due may have changed (status, dates, contacts).
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
    /** Resolve to `true` when the server accepted the write, `false` on a refusal (readable in
     * `error`). */
    save: (body: ApplicationPatch) => settle(patch.mutateAsync(body), event.reset),
    record: (body: EventIn) => settle(event.mutateAsync(body), patch.reset),
    pending: patch.isPending || event.isPending,
    error: failure ? applicationsErrorMessage(failure) : null,
  };
}
