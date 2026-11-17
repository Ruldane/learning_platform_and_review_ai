import { useEffect, useRef, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "./hooks/useSettings";
import { WELCOME_PATH } from "./onboarding";

/** La zone principale de la mise en page (cible du lien d'évitement). */
const CONTENT_ID = "contenu";

/**
 * La porte du premier lancement de la coquille (`shell.gate`) : tant que `onboarding_done` est
 * faux, toute page autre que `/bienvenue` mène à `/bienvenue` (un remplacement, pas un empilement).
 * Les réglages sont lus avant la mise en page : en chargement ou en erreur, un état seul. Une
 * relecture ratée alors que les réglages sont déjà là ne ferme jamais l'application.
 *
 * « Réessayer » garde le focus sur le conteneur (le bouton disparaît avec l'erreur) ; si la lecture
 * réussit, le focus passe au contenu de la mise en page (`#contenu`). Quand la lecture mène à
 * `/bienvenue`, c'est le titre de l'étape qui le prend : la porte ne le lui retire pas.
 */
export function OnboardingGate({ children }: { children: ReactNode }) {
  const settings = useSettings();
  const { pathname } = useLocation();
  const holder = useRef<HTMLElement>(null);
  const retried = useRef(false);
  const ready =
    Boolean(settings.data) && (settings.data?.onboarding_done || pathname === WELCOME_PATH);
  useEffect(() => {
    if (!ready || !retried.current) return;
    retried.current = false;
    if (pathname !== WELCOME_PATH) document.getElementById(CONTENT_ID)?.focus();
  }, [ready, pathname]);

  if (settings.data) {
    return ready ? children : <Navigate to={WELCOME_PATH} replace />;
  }
  const retry = () => {
    retried.current = true;
    holder.current?.focus();
    void settings.refetch();
  };
  return (
    <main ref={holder} tabIndex={-1} className="mx-auto max-w-xl px-6 py-16 focus:outline-none">
      {settings.isError ? (
        <ErrorState message={errorMessage(settings.error)} onRetry={retry} />
      ) : (
        <LoadingState label={t("onboarding.gate.checking")} />
      )}
    </main>
  );
}
