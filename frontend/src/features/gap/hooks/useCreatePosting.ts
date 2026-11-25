import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLaunchSource } from "@/shared/session-ui";
import { createPosting } from "../api";
import type { PostingSourceView } from "../components/viewTypes";
import { postingFormError } from "../postingError";
import { gapKeys } from "../queryKeys";
import type { PostingCreatedOut } from "../types";

/**
 * Adds a posting (link or text). The response says whether the posting is new (`created`) or it is
 * a posting already added (same link or same text). The list is re-read after submission.
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
