import { useMutation, useQueryClient } from "@tanstack/react-query";
import { testApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/** Tests the key in effect, returns the `KeyTestResult`; the back end remembers the last test. */
export function useTestApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => testApiKey(provider),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
  });
}
