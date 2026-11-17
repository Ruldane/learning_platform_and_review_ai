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
 * Enregistre un réglage : le contrat remplace tout, donc on relit les préférences du serveur juste
 * avant et on n'y change que ce qui a été touché (un second onglet resté sur une ancienne valeur ne
 * rallume rien ailleurs). La page suit la réponse du serveur, pas son idée de la valeur.
 */
export function useSavePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<Preferences>) =>
      putPreferences({ ...(await fetchPreferences()), ...patch }),
    onSuccess: (saved) => {
      queryClient.setQueryData(ideKeys.preferences, saved);
      return queryClient.invalidateQueries({ queryKey: ["ide", "usage"] });
    },
  });
}
