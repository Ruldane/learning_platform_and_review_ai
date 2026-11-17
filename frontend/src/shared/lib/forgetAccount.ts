import type { QueryClient } from "@tanstack/react-query";
import { resetLocalState } from "./localReset";

/** Les requêtes de la session (`me`) : elles survivent à l'oubli d'un compte. */
const SESSION_SCOPE = "auth";

/**
 * Oublie tout ce que le compte précédent avait lu : les requêtes (sauf celles de la session) et ce
 * que les features gardent hors du cache (`resetLocalState`). Utilisée à la déconnexion, au 401,
 * après « Tout supprimer » et quand le compte change dans un autre onglet.
 */
export function forgetAccount(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== SESSION_SCOPE });
  resetLocalState();
}
