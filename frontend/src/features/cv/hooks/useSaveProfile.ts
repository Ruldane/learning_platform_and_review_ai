import { useMutation, useQueryClient } from "@tanstack/react-query";
import { putProfile } from "../api";
import type { MasterProfileView, ProfileSaveErrorView } from "../components/viewTypes";
import { errorCode, profileSaveError } from "../errors";
import { cvKeys } from "../queryKeys";
import { fromProfileView } from "../profileView";

/**
 * Valide le profil : `PUT /profile` avec `base_version`, la dernière version relue. Un 409
 * `profile_conflict` ou un 422 revient en `error` (message, et texte par champ) ; le brouillon
 * saisi n'est pas perdu.
 */
export function useSaveProfile(baseVersion: number | null, onSaved: (version: number) => void) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (profile: MasterProfileView) => putProfile(fromProfileView(profile), baseVersion),
    onSuccess: async (saved) => {
      onSaved(saved.version);
      await Promise.all([
        client.invalidateQueries({ queryKey: cvKeys.profile }),
        client.invalidateQueries({ queryKey: cvKeys.profileVersions }),
      ]);
    },
  });
  const { mutate, reset } = mutation;
  const error: ProfileSaveErrorView | null = mutation.isError
    ? profileSaveError(mutation.error)
    : null;
  return {
    save: (profile: MasterProfileView) => {
      reset();
      mutate(profile);
    },
    saving: mutation.isPending,
    error,
    conflict: mutation.isError && errorCode(mutation.error) === "profile_conflict",
    clear: reset,
  };
}
