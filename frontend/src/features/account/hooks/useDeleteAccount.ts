import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef } from "react";
import { useNavigate } from "react-router";
import { resetLocalState } from "@/shared/lib/localReset";
import { fetchMe, postDeleteAccount } from "../api";
import { accountKeys, AUTH_SCOPE } from "../queryKeys";
import { GOOGLE_MODE } from "../types";

/** Où mène « Tout supprimer » en mode local : le premier lancement (réglages vides). */
const WELCOME_PATH = "/bienvenue";

/**
 * « Tout supprimer ». Le mode est lu **avant** l'appel (en mode Google la session est close
 * ensuite : relire `me` donnerait 401). Une fois la suppression faite, rien de ce que l'espace
 * contenait ne reste en mémoire (requêtes, mais aussi ce que les features gardent hors du cache :
 * `resetLocalState`) ; puis :
 * - mode Google : `me` passe à « pas de session », la porte de la coquille mène à `/connexion`
 *   (comme un 401 `auth_required`) ;
 * - mode local : l'identité reste (même utilisateur), retour au premier lancement, qui sait que
 *   les données viennent d'être supprimées (`state.deleted`).
 *
 * `submit` ne lance qu'une suppression à la fois, même si deux validations arrivent dans le même
 * instant (une ref, pas l'état de rendu). `started()` dit si la suppression est partie vers le
 * serveur : faux quand le mode n'a pas pu être lu, donc que rien n'a été envoyé.
 */
export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const running = useRef(false);
  const sent = useRef(false);
  const mutation = useMutation({
    mutationFn: async (confirm: string) => {
      sent.current = false;
      try {
        const me = await queryClient.ensureQueryData({
          queryKey: accountKeys.me,
          queryFn: ({ signal }) => fetchMe(signal),
        });
        sent.current = true;
        await postDeleteAccount(confirm);
        return me?.auth_mode === GOOGLE_MODE;
      } finally {
        running.current = false;
      }
    },
    onSuccess: (closedSession) => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== AUTH_SCOPE });
      resetLocalState();
      if (closedSession) {
        queryClient.setQueryData(accountKeys.me, null);
      } else {
        void navigate(WELCOME_PATH, { replace: true, state: { deleted: true } });
      }
    },
  });
  const { mutate, reset, isPending, error } = mutation;
  // Stable : `DataPage` en fait la dépendance de l'objet d'échec (un neuf prendrait le focus).
  const started = useCallback(() => sent.current, []);
  return {
    isPending,
    error,
    started,
    submit: (confirm: string) => {
      if (running.current) return;
      running.current = true;
      mutate(confirm);
    },
    /** Efface l'échec affiché ; sans effet pendant l'envoi. */
    reset: () => {
      if (!running.current) reset();
    },
  };
}
