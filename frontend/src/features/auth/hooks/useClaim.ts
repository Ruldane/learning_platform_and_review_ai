import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postClaim } from "../api";
import { authKeys } from "../queryKeys";
import type { ClaimChoice } from "../types";

/** Envoie le choix de la reprise ; la session est ouverte, `me` est connu sans le relire. */
export function useClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (choice: ClaimChoice) => postClaim(choice),
    onSuccess: (me) => {
      queryClient.setQueryData(authKeys.me, me);
    },
  });
}
