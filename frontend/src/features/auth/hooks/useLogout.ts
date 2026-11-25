import { useMutation, useQueryClient } from "@tanstack/react-query";
import { forgetAccount } from "@/shared/lib/forgetAccount";
import { postLogout } from "../api";
import { authKeys } from "../queryKeys";

/**
 * Se déconnecter : `me` passe à « pas de session » (la porte mène alors à `/login`), et rien
 * de ce que le compte précédent a lu ne reste en mémoire (requêtes, brouillons, minuteurs).
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
