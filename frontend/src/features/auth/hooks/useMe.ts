import { useQuery } from "@tanstack/react-query";
import { readMe } from "../api";
import { authKeys } from "../queryKeys";
import type { Me } from "../types";

/**
 * L'utilisateur connecté. Un 401 `auth_required` n'est pas une panne : il vaut `null` (« pas de
 * session »), ce qui évite qu'une relecture échoue en boucle ; toute autre erreur reste une erreur.
 * Pas de nouvelle tentative : la porte propose « Réessayer ».
 */
export function useMe() {
  return useQuery<Me | null>({
    queryKey: authKeys.me,
    queryFn: ({ signal }) => readMe(signal),
    retry: false,
  });
}
