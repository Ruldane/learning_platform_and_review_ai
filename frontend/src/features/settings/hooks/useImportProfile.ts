import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { useLaunchSource } from "@/shared/session-ui";
import { importProfile, type ProfileImport } from "../api";

/**
 * `POST /profile/import` depuis le premier lancement : la lecture se fait en arrière-plan côté
 * serveur, l'étape n'attend rien d'autre que l'accusé de réception. Un échec garde son message
 * (409 : une lecture est déjà en cours, 413 et 415 : le fichier) ; envoyer de nouveau l'efface.
 */
export function useImportProfile() {
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: (documents: ProfileImport) => importProfile(documents, provider.source),
  });
  const { mutate, reset } = mutation;
  return {
    start: (documents: ProfileImport) => {
      reset();
      mutate(documents);
    },
    launchMenu: provider.menu,
    pending: mutation.isPending,
    imported: mutation.isSuccess,
    error: mutation.isError ? errorMessage(mutation.error) : null,
  };
}
