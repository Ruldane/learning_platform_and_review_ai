import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { postClaim, readMe } from "../api";
import { authKeys } from "../queryKeys";
import type { ClaimChoice } from "../types";

const ALREADY_CLAIMED = "local_already_claimed";

/**
 * Envoie le choix de la reprise ; la session est ouverte, `me` est connu sans le relire. Un choix
 * rejoué (double envoi, deuxième onglet) répond `local_already_claimed` à la personne qui vient de
 * reprendre l'espace : si sa session est ouverte, `me` est relu et elle entre ; sinon le refus
 * reste ce qu'il est.
 */
export function useClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (choice: ClaimChoice) => {
      try {
        return await postClaim(choice);
      } catch (error) {
        if (error instanceof ApiError && error.code === ALREADY_CLAIMED) {
          const me = await readMe().catch(() => null);
          if (me) return me;
        }
        throw error;
      }
    },
    onSuccess: (me) => {
      queryClient.setQueryData(authKeys.me, me);
    },
  });
}
