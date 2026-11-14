import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { markDistinct } from "../api";
import { gapKeys } from "../queryKeys";

/** « Ce sont deux offres distinctes » : l'autre offre disparaît des doublons, l'offre est relue. */
export function useMarkDistinct(postingId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (otherId: string) => markDistinct(postingId, otherId),
    onSuccess: () => client.invalidateQueries({ queryKey: gapKeys.posting(postingId) }),
  });
  return {
    distinct: (otherId: string) => mutation.mutate(otherId),
    error: mutation.isError ? errorMessage(mutation.error) : null,
  };
}
