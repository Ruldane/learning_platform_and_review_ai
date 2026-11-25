import { useMutation, useQueryClient } from "@tanstack/react-query";
import { decideBulk, decideModification, type Decision } from "../api";
import { cvErrorMessage, errorCode } from "../errors";
import { cvKeys } from "../queryKeys";
import type { CvReviewOut, ModificationOut } from "../types";

const replaceMod = (review: CvReviewOut | undefined, updated: ModificationOut) =>
  review && {
    ...review,
    modifications: review.modifications.map((mod) => (mod.id === updated.id ? updated : mod)),
  };

/**
 * Decides a change (`PATCH /cv/modifications/{id}`). The response replaces the change
 * in the review: it may come back « à confirmer » (text revalidated). An error stays readable in
 * `error`; `code` names it for refusals that have a follow-up (`profile_draft_pending`).
 */
export function useDecide(reviewId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: Decision }) =>
      decideModification(id, decision),
    onSuccess: (updated) =>
      client.setQueryData<CvReviewOut>(cvKeys.review(reviewId), (review) =>
        replaceMod(review, updated),
      ),
  });
  const { mutateAsync, reset } = mutation;
  return {
    /** Resolves to `true` when the decision is taken, `false` on a refusal (see `error`). */
    decide: async (id: string, decision: Decision): Promise<boolean> => {
      reset();
      try {
        await mutateAsync({ id, decision });
        return true;
      } catch {
        return false;
      }
    },
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
    /** The change whose last decision was refused: the error shows on its card. */
    errorId: mutation.isError ? (mutation.variables?.id ?? null) : null,
    code: mutation.isError ? errorCode(mutation.error) : null,
  };
}

/**
 * Grouped decision (`PATCH /cv/reviews/{id}/modifications`) on `proposed` changes: a
 * « à confirmer » change is never part of it. The review is reloaded before control returns.
 */
export function useBulkDecide(reviewId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: Decision["status"] }) =>
      decideBulk(reviewId, ids, status),
    onSuccess: () => client.invalidateQueries({ queryKey: cvKeys.review(reviewId) }),
  });
  const { mutate, reset } = mutation;
  return {
    decide: (ids: string[], status: Decision["status"]) => {
      reset();
      mutate({ ids, status });
    },
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
    skipped: mutation.data?.skipped.length ?? 0,
  };
}
