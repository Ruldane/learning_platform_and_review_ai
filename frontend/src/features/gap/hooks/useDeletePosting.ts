import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { deletePosting } from "../api";
import { gapKeys } from "../queryKeys";

/**
 * Deletes the posting. The 409s `review_in_progress` (a CV review is running or waiting),
 * `analysis_in_progress` (an analysis is open) and `posting_has_running_work` (a committee or an
 * interview in progress cites the posting) have their own text; `code` lets the page
 * offer the link to the review.
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
