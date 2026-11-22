import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLaunchSource } from "@/shared/session-ui";
import { importProfile, type ProfileImport } from "../api";
import { cvErrorMessage } from "../errors";
import { cvKeys } from "../queryKeys";

/** `POST /profile/import` : après l'envoi, le profil est relu (il porte la session de lecture). */
export function useImportProfile() {
  const client = useQueryClient();
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: (documents: ProfileImport) => importProfile(documents, provider.source),
    onSuccess: () => client.invalidateQueries({ queryKey: cvKeys.profile }),
  });
  const { mutate, reset } = mutation;
  return {
    start: (documents: ProfileImport) => {
      reset();
      mutate(documents);
    },
    launchMenu: provider.menu,
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
  };
}
