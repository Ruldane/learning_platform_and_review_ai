import { useEffect, useRef, type ReactNode } from "react";
import { Navigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

export type GateStatus = "loading" | "signedOut" | "error" | "ready";

/** The main area of the layout (target of the skip link). */
const CONTENT_ID = "contenu";

interface AuthGateProps {
  status: GateStatus;
  /** The error message, when `status` is `error`. */
  message?: string;
  onRetry: () => void;
  children: ReactNode;
}

/**
 * The login gate, presentational: when open (`ready`), it shows the layout;
 * without a session it leads to `/login` (a replace, never a push); in error or
 * loading it shows a state alone, without the layout. The container stays the same element:
 * « Réessayer » keeps focus on it; if the re-read succeeds, focus moves to the layout
 * content (`#contenu`, target of the skip link): the container is unmounted with the button.
 */
export function AuthGate({ status, message, onRetry, children }: AuthGateProps) {
  const holder = useRef<HTMLElement>(null);
  const retried = useRef(false);
  useEffect(() => {
    if (status !== "ready" || !retried.current) return;
    retried.current = false;
    document.getElementById(CONTENT_ID)?.focus();
  }, [status]);
  if (status === "ready") return children;
  if (status === "signedOut") return <Navigate to="/login" replace />;
  const retry = () => {
    retried.current = true;
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
