import { useQuery } from "@tanstack/react-query";
import { fetchApiKeys } from "../api";
import { settingsKeys } from "../queryKeys";

/** One entry per provider: origin of the key and last 4 characters, never the key. */
export function useApiKeys(enabled = true) {
  return useQuery({
    queryKey: settingsKeys.apiKeys,
    enabled,
    queryFn: ({ signal }) => fetchApiKeys(signal),
  });
}
