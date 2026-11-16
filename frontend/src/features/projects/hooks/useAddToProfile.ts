import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { addToProfile } from "../api";
import { addFailure, errorCode } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProfileEntryView, ProjectOut } from "../types";

/**
 * « Ajouter au profil maître » (`POST /projects/{id}/profile-entry`) : l'entrée de January, avec son
 * texte éventuellement modifié, devient une nouvelle version validée du profil ; le serveur rend le
 * projet avec sa `profile_version`. Un seul envoi à la fois (un double clic n'ajoute pas deux fois) ;
 * un refus 409 est écrit en clair, avec le lien du profil quand c'est là que se trouve la suite.
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
      // Déjà ajouté ailleurs, ou plus validé : la page relit le projet pour dire l'état réel.
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
