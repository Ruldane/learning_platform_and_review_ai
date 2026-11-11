import { useMutation, useQueryClient } from "@tanstack/react-query";
import { putSettings } from "../api";
import { settingsKeys } from "../queryKeys";
import type { UserSettings } from "../types";

/** Remplace les réglages (`PUT /settings`, corps complet), puis recharge `["settings"]`. */
export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UserSettings) => putSettings(body),
    onSuccess: (saved) => {
      queryClient.setQueryData(settingsKeys.settings, saved);
      return queryClient.invalidateQueries({ queryKey: settingsKeys.settings });
    },
  });
}
