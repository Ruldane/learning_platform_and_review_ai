import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { generateCv } from "../api";
import { cvErrorMessage } from "../errors";
import { cvKeys } from "../queryKeys";

/**
 * « Générer le PDF » : `POST /cv/reviews/{id}/generate`. Un double clic n'envoie qu'une requête
 * (le verrou tient jusqu'à la réponse), et la revue est relue avant de rendre la main : la
 * question de sortie n'attend plus, les boutons se désactivent pendant le rendu. Un 409 (génération
 * déjà en cours, revue terminée…) revient en `error`, en français.
 */
export function useGenerate(reviewId: string) {
  const client = useQueryClient();
  const locked = useRef(false);
  const mutation = useMutation({
    mutationFn: (allowExtraPages: boolean) => generateCv(reviewId, allowExtraPages),
    onSettled: async () => {
      await client.invalidateQueries({ queryKey: cvKeys.review(reviewId) });
      locked.current = false;
    },
  });
  const { mutate, reset } = mutation;
  return {
    generate: (allowExtraPages = false) => {
      if (locked.current) return;
      locked.current = true;
      reset();
      mutate(allowExtraPages);
    },
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
  };
}
