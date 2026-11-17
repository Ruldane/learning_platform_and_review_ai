import { useRef, type ReactNode } from "react";
import { Navigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

export type GateStatus = "loading" | "signedOut" | "error" | "ready";

interface AuthGateProps {
  status: GateStatus;
  /** Le message de l'erreur, quand `status` vaut `error`. */
  message?: string;
  onRetry: () => void;
  children: ReactNode;
}

/**
 * La porte de connexion, présentationnelle : ouverte (`ready`), elle montre la mise en page ;
 * sans session elle mène à `/connexion` (un remplacement, jamais un empilement) ; en erreur ou en
 * chargement elle montre un état seul, sans la mise en page. Le conteneur reste le même élément :
 * « Réessayer » lui garde le focus, que l'état change ou non.
 */
export function AuthGate({ status, message, onRetry, children }: AuthGateProps) {
  const holder = useRef<HTMLElement>(null);
  if (status === "ready") return children;
  if (status === "signedOut") return <Navigate to="/connexion" replace />;
  const retry = () => {
    holder.current?.focus();
    onRetry();
  };
  return (
    <main ref={holder} tabIndex={-1} className="mx-auto max-w-xl px-6 py-16 focus:outline-none">
      {status === "loading" ? (
        <LoadingState label={t("auth.gate.checking")} />
      ) : (
        <ErrorState message={message ?? t("auth.gate.failed")} onRetry={retry} />
      )}
    </main>
  );
}
