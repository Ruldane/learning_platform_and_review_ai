import { useQuery } from "@tanstack/react-query";
import { fetchModels } from "../api";
import { settingsKeys } from "../queryKeys";

/** Providers (with or without a key), offered models and presets. */
export function useModels() {
  return useQuery({
    queryKey: settingsKeys.models,
    queryFn: ({ signal }) => fetchModels(signal),
  });
}
