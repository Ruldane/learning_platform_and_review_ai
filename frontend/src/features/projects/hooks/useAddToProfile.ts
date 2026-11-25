import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { addToProfile } from "../api";
import { addFailure, errorCode } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProfileEntryView, ProjectOut } from "../types";

/**
 * « Ajouter au profil maître » (`POST /projects/{id}/profile-entry`): January's entry, with its
 * text possibly edited, becomes a new validated version of the profile; the server returns the
 * project with its `profile_version`. One send at a time (a double click does not add twice);
 * a 409 refusal is written in plain text, with the profile link if that is the next step.
 */
export function useAddToProfile(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: (entry: ProfileEntryView) => addToProfile(projectId, entry),
    onSuccess: (project) => {
      client.setQueryData(projectKeys.one(projectId), project);
      void client.invalidateQueries({ queryKey: projectKeys.list });
    },
    onError: (error) => {
      // Already added elsewhere, or no longer validated: the page re-reads the real state.
      const code = errorCode(error);
      if (code === "entry_already_added" || code === "project_not_validated") {
        void client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
      }
    },
  });
  const { mutateAsync, error, isError } = mutation;
  const failure = useMemo(() => (isError ? addFailure(error) : null), [isError, error]);
  return {
    add: (entry: ProfileEntryView) => {
      const added = client.getQueryData<ProjectOut>(projectKeys.one(projectId))?.profile_version;
      if (sending.current || (added !== undefined && added !== null)) return;
      sending.current = true;
      void mutateAsync(entry)
        .catch(() => null)
        .finally(() => {
          sending.current = false;
        });
    },
    pending: mutation.isPending,
    failure,
  };
}
