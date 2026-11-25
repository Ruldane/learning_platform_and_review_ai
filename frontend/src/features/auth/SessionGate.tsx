import { useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { onAuthRequired } from "@/shared/api/authEvents";
import { errorMessage } from "@/shared/api/errors";
import { forgetAccount } from "@/shared/lib/forgetAccount";
import { readMe } from "./api";
import { AuthGate, type GateStatus } from "./components/AuthGate";
import { useMe } from "./hooks/useMe";
import { authKeys } from "./queryKeys";
import type { Me } from "./types";

/**
 * The shell's login gate (`shell.gate`): wires `me` to `AuthGate`. A 401
 * `auth_required` received from any call sets `me` to « pas de session » without re-reading it:
 * re-reading `me` from here would fail again, so it is emitted again. `AuthGate` then leads
 * to `/login` once, and the login page never sends back to the gate.
 *
 * The session cookie is shared by all tabs: when the tab becomes visible again, `me`
 * is re-read without cache. If the account changed (or the session closed) in another tab,
 * everything the old account read is forgotten; the tab then shows the current account.
 */
export function SessionGate({ children }: { children: ReactNode }) {
  const me = useMe();
  const queryClient = useQueryClient();
  useEffect(
    () =>
      onAuthRequired(() => {
        queryClient.setQueryData(authKeys.me, null);
        forgetAccount(queryClient);
      }),
    [queryClient],
  );
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      const shown = queryClient.getQueryData<Me | null>(authKeys.me);
      if (!shown) return;
      queryClient
        .fetchQuery({
          queryKey: authKeys.me,
          queryFn: ({ signal }) => readMe(signal),
          staleTime: 0,
        })
        .then(
          (fresh) => {
            if (fresh?.id !== shown.id) forgetAccount(queryClient);
          },
          () => undefined, // a failed re-read changes nothing: what is shown is kept
        );
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [queryClient]);
  let status: GateStatus = "loading";
  if (me.data === null) status = "signedOut";
  else if (me.data) status = "ready";
  else if (me.isError && !me.isFetching) status = "error";
  return (
    <AuthGate status={status} message={errorMessage(me.error)} onRetry={() => void me.refetch()}>
      {children}
    </AuthGate>
  );
}
