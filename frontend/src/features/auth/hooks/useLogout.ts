import { useMutation, useQueryClient } from "@tanstack/react-query";
import { forgetAccount } from "@/shared/lib/forgetAccount";
import { postLogout } from "../api";
import { authKeys } from "../queryKeys";

/**
 * Sign out: `me` becomes « pas de session » (the gate then leads to `/login`), and nothing
 * the previous account read stays in memory (queries, drafts, timers).
 */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postLogout,
    onSuccess: () => {
      queryClient.setQueryData(authKeys.me, null);
      forgetAccount(queryClient);
    },
  });
}
