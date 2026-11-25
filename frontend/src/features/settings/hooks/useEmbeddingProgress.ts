import { useQuery } from "@tanstack/react-query";
import { fetchEmbeddingProgress } from "../api";
import { settingsKeys } from "../queryKeys";

export const EMBEDDING_PROGRESS_MS = 3_000;

/**
 * The embeddings model's progress, reread every 3 s while it is not present; once
 * present, no more reads. A failed read breaks nothing: the next one retries.
 */
export function useEmbeddingProgress() {
  return useQuery({
    queryKey: settingsKeys.onboardingEmbedding,
    queryFn: ({ signal }) => fetchEmbeddingProgress(signal),
    refetchInterval: (query) => (query.state.data?.present ? false : EMBEDDING_PROGRESS_MS),
    retry: false,
  });
}
