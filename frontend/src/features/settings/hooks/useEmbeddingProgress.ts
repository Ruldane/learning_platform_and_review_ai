import { useQuery } from "@tanstack/react-query";
import { fetchEmbeddingProgress } from "../api";
import { settingsKeys } from "../queryKeys";

export const EMBEDDING_PROGRESS_MS = 3_000;

/**
 * La progression du modèle d'embeddings, relue toutes les 3 s tant qu'il n'est pas présent ; une
 * fois présent, plus aucune lecture. Une lecture ratée ne casse rien : la suivante réessaie.
 */
export function useEmbeddingProgress() {
  return useQuery({
    queryKey: settingsKeys.onboardingEmbedding,
    queryFn: ({ signal }) => fetchEmbeddingProgress(signal),
    refetchInterval: (query) => (query.state.data?.present ? false : EMBEDDING_PROGRESS_MS),
    retry: false,
  });
}
