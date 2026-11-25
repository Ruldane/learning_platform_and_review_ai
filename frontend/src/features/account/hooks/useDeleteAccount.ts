import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { forgetAccount } from "@/shared/lib/forgetAccount";
import { AccountChangedError, fetchMe, postDeleteAccount } from "../api";
import { accountKeys } from "../queryKeys";
import { GOOGLE_MODE, type Me } from "../types";

/** Où mène « Tout supprimer » en mode local : le premier lancement (réglages vides). */
const WELCOME_PATH = "/welcome";

function readCurrentMe(queryClient: QueryClient): Promise<Me | null> {
  return queryClient.fetchQuery({
    queryKey: accountKeys.me,
    queryFn: ({ signal }) => fetchMe(signal),
    staleTime: 0,
  });
}

interface Consent {
  confirm: string;
  account: Me;
}

async function deleteWithConsent(
  queryClient: QueryClient,
  { confirm, account }: Consent,
  onSend: () => void,
) {
  const me = await readCurrentMe(queryClient);
  if (me?.id !== account.id) {
    forgetAccount(queryClient);
    throw new AccountChangedError();
  }
  onSend();
  try {
    await postDeleteAccount(confirm, account.id);
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== "account_changed") throw error;
    forgetAccount(queryClient);
    await readCurrentMe(queryClient).catch(() => undefined);
    throw new AccountChangedError();
  }
  return account;
}

/**
 * « Tout supprimer ». Le mode est lu **avant** l'appel (en mode Google la session est close
 * ensuite : relire `me` donnerait 401), et sans cache : si le compte n'est plus celui qui est
 * affiché (autre onglet), rien n'est envoyé, la mémoire est vidée et `me` est celui du compte
 * actuel (`AccountChangedError`). Une fois la suppression faite, rien de ce que l'espace
 * contenait ne reste en mémoire (requêtes, mais aussi ce que les features gardent hors du cache :
 * `resetLocalState`) ; puis :
 * - mode Google : `me` passe à « pas de session », la porte de la coquille mène à `/login`
 *   (comme un 401 `auth_required`) ;
 * - mode local : l'identité reste (même utilisateur), retour au premier lancement, qui sait que
 *   les données viennent d'être supprimées (`state.deleted`).
 *
 * `submit` garde l'identité affichée avec le mot de confirmation. Le serveur la contrôle aussi,
 * car un autre onglet peut changer le cookie après la lecture de `me`.
 */
export function useDeleteAccount(account: Me | null | undefined) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const running = useRef(false);
  const sent = useRef(false);
  const [consentRevision, setConsentRevision] = useState(0);
  const { mutate, reset, isPending, error, variables } = useMutation({
    mutationFn: async (consent: Consent) => {
      sent.current = false;
      try {
        return await deleteWithConsent(queryClient, consent, () => {
          sent.current = true;
        });
      } catch (error) {
        if (error instanceof AccountChangedError) setConsentRevision((value) => value + 1);
        throw error;
      } finally {
        running.current = false;
      }
    },
    onSuccess: (deleted) => {
      if (queryClient.getQueryData<Me | null>(accountKeys.me)?.id !== deleted.id) return;
      forgetAccount(queryClient);
      if (deleted.auth_mode === GOOGLE_MODE) {
        queryClient.setQueryData(accountKeys.me, null);
      } else {
        void navigate(WELCOME_PATH, { replace: true, state: { deleted: true } });
      }
    },
  });
  // Stable : `DataPage` en fait la dépendance de l'objet d'échec (un neuf prendrait le focus).
  const started = useCallback(() => sent.current, []);
  return {
    isPending,
    error:
      error instanceof AccountChangedError || variables?.account.id === account?.id ? error : null,
    consentRevision,
    started,
    submit: (confirm: string) => {
      if (running.current || !account) return;
      running.current = true;
      mutate({ confirm, account });
    },
    /** Efface l'échec affiché ; sans effet pendant l'envoi. */
    reset: () => {
      if (!running.current) reset();
    },
  };
}
