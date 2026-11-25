import { useQuery } from "@tanstack/react-query";
import { fetchSettings } from "../api";
import { settingsKeys } from "../queryKeys";

/** The user's settings (`GET /settings`). */
export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.settings,
    queryFn: ({ signal }) => fetchSettings(signal),
  });
}
