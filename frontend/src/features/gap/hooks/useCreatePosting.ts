import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLaunchSource } from "@/shared/session-ui";
import { createPosting } from "../api";
import type { PostingSourceView } from "../components/viewTypes";
import { postingFormError } from "../postingError";
import { gapKeys } from "../queryKeys";
import type { PostingCreatedOut } from "../types";

/**
 * Ajoute une offre (lien ou texte). La réponse dit si l'offre est nouvelle (`created`) ou si c'est
 * une offre déjà ajoutée (même lien ou même texte). La liste est relue après l'envoi.
 */
export function useCreatePosting(onDone: (result: PostingCreatedOut) => void) {
  const client = useQueryClient();
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: (source: PostingSourceView) => createPosting(source, provider.source),
    onSuccess: (result) => {
      void client.invalidateQueries({ queryKey: gapKeys.postings });
      onDone(result);
    },
  });
  const { mutate, reset } = mutation;
  return {
    providerMenu: provider.menu,
    create: (source: PostingSourceView) => {
      reset();
      mutate(source);
    },
    pending: mutation.isPending,
    error: mutation.isError ? postingFormError(mutation.error) : null,
  };
}
