import { useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { onAuthRequired } from "@/shared/api/authEvents";
import { errorMessage } from "@/shared/api/errors";
import { AuthGate, type GateStatus } from "./components/AuthGate";
import { useMe } from "./hooks/useMe";
import { authKeys } from "./queryKeys";

/**
 * La porte de connexion de la coquille (`shell.gate`) : branche `me` sur `AuthGate`. Un 401
 * `auth_required` reçu par n'importe quel appel passe `me` à « pas de session » sans le relire :
 * relire `me` d'ici le ferait échouer de nouveau, donc émettre de nouveau. `AuthGate` mène alors
 * à `/connexion`, une seule fois, et la page de connexion ne renvoie jamais vers la porte.
 */
export function SessionGate({ children }: { children: ReactNode }) {
  const me = useMe();
  const queryClient = useQueryClient();
  useEffect(() => onAuthRequired(() => queryClient.setQueryData(authKeys.me, null)), [queryClient]);
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
