import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPreferences, putPreferences } from "../api";
import { ideKeys } from "../queryKeys";
import type { Preferences } from "../types";

/** Teacher mode, timer and caps (`GET /ide/preferences`). */
export function usePreferences() {
  return useQuery({
    queryKey: ideKeys.preferences,
    queryFn: ({ signal }) => fetchPreferences(signal),
  });
}

/**
 * Saves one setting: the contract replaces everything, so we re-read the server preferences just
 * before and only change what was touched (a second tab left on an old value must not
 * switch anything back on). The page follows the server's answer, not its own idea of the value.
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
