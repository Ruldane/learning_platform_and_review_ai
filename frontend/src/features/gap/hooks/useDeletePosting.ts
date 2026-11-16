import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { deletePosting } from "../api";
import { gapKeys } from "../queryKeys";

/**
 * Supprime l'offre. Les 409 `review_in_progress` (une revue de CV tourne ou attend),
 * `analysis_in_progress` (une analyse est ouverte) et `posting_has_running_work` (un comité ou un
 * entretien en cours cite l'offre) ont leur texte ; `code` permet à la page de
 * proposer le lien vers la revue.
 */
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
  const code = failure instanceof ApiError ? failure.code : null;
  const error = !mutation.isError ? null : deleteMessage(code, failure);
  return {
    remove: () => mutation.mutate(),
    pending: mutation.isPending,
    error,
    code,
    reset: mutation.reset,
  };
}

const REFUSALS = [
  "review_in_progress",
  "analysis_in_progress",
  "posting_has_running_work",
] as const;

function deleteMessage(code: string | null, failure: unknown): string {
  const known = REFUSALS.find((refused) => refused === code);
  return known ? t(`gap.errors.${known}`) : errorMessage(failure);
}
