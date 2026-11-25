import { useMutation, useQueryClient } from "@tanstack/react-query";
import { putProfile } from "../api";
import type { MasterProfileView, ProfileSaveErrorView } from "../components/viewTypes";
import { errorCode, profileSaveError } from "../errors";
import { cvKeys } from "../queryKeys";
import { fromProfileView } from "../profileView";

/**
 * Validates the profile: `PUT /profile` with `base_version`, the last reloaded version. A 409
 * `profile_conflict` or a 422 comes back as `error` (message, and text per field); the draft
 * entered is not lost.
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
