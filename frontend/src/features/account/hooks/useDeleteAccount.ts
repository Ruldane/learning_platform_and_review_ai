import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { forgetAccount } from "@/shared/lib/forgetAccount";
import { AccountChangedError, fetchMe, postDeleteAccount } from "../api";
import { accountKeys } from "../queryKeys";
import { GOOGLE_MODE, type Me } from "../types";

/** Where « Tout supprimer » leads in local mode: the first launch (empty settings). */
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
 * « Tout supprimer ». The mode is read **before** the call (in Google mode the session is closed
 * afterwards: re-reading `me` would give 401), and without cache: if the account is no longer the
 * one that is
 * displayed (another tab), nothing is sent, memory is cleared and `me` is that of the
 * current account (`AccountChangedError`). Once deletion is done, nothing the space
 * held stays in memory (queries, but also what the features keep outside the cache:
 * `resetLocalState`); then:
 * - Google mode: `me` becomes « pas de session », the shell gate leads to `/login`
 *   (like a 401 `auth_required`);
 * - local mode: the identity stays (same user), back to the first launch, which knows that
 *   the data was just deleted (`state.deleted`).
 *
 * `submit` keeps the displayed identity with the confirmation word. The server checks it too,
 * since another tab can change the cookie after `me` is read.
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
  // Stable: `DataPage` uses it as the dependency of the failure object (a new one would take
  // focus).
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
    /** Clears the displayed failure; no effect while sending. */
    reset: () => {
      if (!running.current) reset();
    },
  };
}
