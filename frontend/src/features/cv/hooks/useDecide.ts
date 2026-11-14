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
 * Décide d'une modification (`PATCH /cv/modifications/{id}`). La réponse remplace la modification
 * dans la revue : elle peut revenir « à confirmer » (texte revalidé). Une erreur reste lisible dans
 * `error` ; `code` la nomme pour les refus qui ont une suite (`profile_draft_pending`).
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
  const { mutate, reset } = mutation;
  return {
    decide: (id: string, decision: Decision) => {
      reset();
      mutate({ id, decision });
    },
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
    code: mutation.isError ? errorCode(mutation.error) : null,
  };
}

/**
 * Décision groupée (`PATCH /cv/reviews/{id}/modifications`) sur les modifications `proposed` : une
 * modification « à confirmer » n'en fait jamais partie. La revue est relue avant de rendre la main.
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
