import { useQuery } from "@tanstack/react-query";
import { fetchSettings } from "../api";
import { settingsKeys } from "../queryKeys";

/** Réglages de l'utilisateur (`GET /settings`). */
export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.settings,
    queryFn: ({ signal }) => fetchSettings(signal),
  });
}
