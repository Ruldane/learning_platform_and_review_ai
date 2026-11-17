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
 * La porte de connexion de la coquille (`shell.gate`) : branche `me` sur `AuthGate`. Un 401
 * `auth_required` reçu par n'importe quel appel passe `me` à « pas de session » sans le relire :
 * relire `me` d'ici le ferait échouer de nouveau, donc émettre de nouveau. `AuthGate` mène alors
 * à `/connexion`, une seule fois, et la page de connexion ne renvoie jamais vers la porte.
 *
 * Le cookie de session est partagé par tous les onglets : quand l'onglet redevient visible, `me`
 * est relu sans cache. Si le compte a changé (ou la session s'est close) dans un autre onglet,
 * tout ce que l'ancien compte avait lu est oublié ; l'onglet montre alors le compte actuel.
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
          () => undefined, // une relecture ratée ne change rien : on garde ce qui est affiché
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
