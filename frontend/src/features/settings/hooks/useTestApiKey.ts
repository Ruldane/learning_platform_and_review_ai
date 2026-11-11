import { useMutation, useQueryClient } from "@tanstack/react-query";
import { testApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/** Teste la clé en vigueur et renvoie le `KeyTestResult` ; le back mémorise le dernier test. */
export function useTestApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => testApiKey(provider),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
  });
}
