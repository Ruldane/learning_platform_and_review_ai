import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { fetchMe, postDeleteAccount } from "../api";
import { accountKeys, AUTH_SCOPE } from "../queryKeys";
import { GOOGLE_MODE } from "../types";

/** Où mène « Tout supprimer » en mode local : le premier lancement (réglages vides). */
const WELCOME_PATH = "/bienvenue";

/**
 * « Tout supprimer ». Le mode est lu **avant** l'appel (en mode Google la session est close
 * ensuite : relire `me` donnerait 401). Une fois la suppression faite, rien de ce que l'espace
 * contenait ne reste en mémoire ; puis :
 * - mode Google : `me` passe à « pas de session », la porte de la coquille mène à `/connexion`
 *   (comme un 401 `auth_required`) ;
 * - mode local : l'identité reste (même utilisateur), retour au premier lancement.
 */
export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async (confirm: string) => {
      const me = await queryClient.ensureQueryData({
        queryKey: accountKeys.me,
        queryFn: ({ signal }) => fetchMe(signal),
      });
      await postDeleteAccount(confirm);
      return me?.auth_mode === GOOGLE_MODE;
    },
    onSuccess: (closedSession) => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== AUTH_SCOPE });
      if (closedSession) {
        queryClient.setQueryData(accountKeys.me, null);
      } else {
        void navigate(WELCOME_PATH, { replace: true });
      }
    },
  });
}
