import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { generateCv } from "../api";
import { cvErrorMessage } from "../errors";
import { cvKeys } from "../queryKeys";

/**
 * « Générer le PDF »: `POST /cv/reviews/{id}/generate`. A double click sends only one request
 * (the lock holds until the response), and the review is reloaded before control returns: the
 * exit question no longer waits, the buttons are disabled during rendering. A 409 (generation
 * already running, review finished…) comes back as `error`, in French.
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
