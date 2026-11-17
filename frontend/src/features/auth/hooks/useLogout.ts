import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postLogout } from "../api";
import { authKeys } from "../queryKeys";

/**
 * Se déconnecter : `me` passe à « pas de session » (la porte mène alors à `/connexion`), et rien
 * de ce que le compte précédent a lu ne reste en mémoire.
 */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postLogout,
    onSuccess: () => {
      queryClient.setQueryData(authKeys.me, null);
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== authKeys.me[0],
      });
    },
  });
}
