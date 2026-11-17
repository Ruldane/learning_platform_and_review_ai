import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPreferences, putPreferences } from "../api";
import { ideKeys } from "../queryKeys";
import type { Preferences } from "../types";

/** Mode du professeur, minuterie et plafonds (`GET /ide/preferences`). */
export function usePreferences() {
  return useQuery({
    queryKey: ideKeys.preferences,
    queryFn: ({ signal }) => fetchPreferences(signal),
  });
}

/**
 * Enregistre les préférences : le contrat remplace tout, on renvoie donc les plafonds lus avec le
 * réglage changé. La page suit la réponse du serveur, pas son idée de la valeur.
 */
export function useSavePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Preferences) => putPreferences(body),
    onSuccess: (saved) => {
      queryClient.setQueryData(ideKeys.preferences, saved);
      return queryClient.invalidateQueries({ queryKey: ["ide", "usage"] });
    },
  });
}
