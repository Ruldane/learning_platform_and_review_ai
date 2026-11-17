import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchMe } from "../api";
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
    queryFn: async ({ signal }) => {
      try {
        return await fetchMe(signal);
      } catch (error) {
        if (error instanceof ApiError && error.code === "auth_required") return null;
        throw error;
      }
    },
    retry: false,
  });
}
