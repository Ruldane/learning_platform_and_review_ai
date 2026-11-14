import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { deletePosting } from "../api";
import { gapKeys } from "../queryKeys";

/** Supprime l'offre ; 409 `review_in_progress` (une revue de CV tourne) a son texte. */
export function useDeletePosting(postingId: string, onDeleted: () => void) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => deletePosting(postingId),
    onSuccess: () => {
      client.removeQueries({ queryKey: gapKeys.posting(postingId) });
      client.removeQueries({ queryKey: gapKeys.gap(postingId) });
      void client.invalidateQueries({ queryKey: gapKeys.postings });
      onDeleted();
    },
  });
  const failure = mutation.error;
  const error = !mutation.isError
    ? null
    : failure instanceof ApiError && failure.code === "review_in_progress"
      ? t("gap.errors.review_in_progress")
      : errorMessage(failure);
  return {
    remove: () => mutation.mutate(),
    pending: mutation.isPending,
    error,
    reset: mutation.reset,
  };
}
