import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { RunSourceAvailability } from "@/shared/lib/runSource";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useApiKeys } from "./hooks/useApiKeys";
import { useSettings } from "./hooks/useSettings";
import { LEGACY_WELCOME_PATH, WELCOME_PATH } from "./onboarding";

/** La zone principale de la mise en page (cible du lien d'évitement). */
const CONTENT_ID = "contenu";

/**
 * La porte du premier lancement de la coquille (`shell.gate`) : tant que `onboarding_done` est
 * faux, toute page autre que `/welcome` mène à `/welcome` (un remplacement, pas un empilement).
 * Les réglages sont lus avant la mise en page : en chargement ou en erreur, un état seul. Une
 * relecture ratée alors que les réglages sont déjà là ne ferme jamais l'application.
 *
 * « Réessayer » garde le focus sur le conteneur (le bouton disparaît avec l'erreur) ; si la lecture
 * réussit, le focus passe au contenu de la mise en page (`#contenu`). Quand la lecture mène à
 * `/welcome`, c'est le titre de l'étape qui le prend : la porte ne le lui retire pas.
 */
export function OnboardingGate({ children }: { children: ReactNode }) {
  const settings = useSettings();
  const { data: keys } = useApiKeys(false);
  const keyed = useMemo(
    () => keys && new Set(keys.filter((key) => key.last4 != null).map((key) => key.provider)),
    [keys],
  );
  const { pathname } = useLocation();
  const isWelcome = pathname === WELCOME_PATH || pathname === LEGACY_WELCOME_PATH;
  const holder = useRef<HTMLElement>(null);
  const retried = useRef(false);
  const ready = Boolean(settings.data) && (settings.data?.onboarding_done || isWelcome);
  useEffect(() => {
    if (!ready || !retried.current) return;
    retried.current = false;
    if (!isWelcome) document.getElementById(CONTENT_ID)?.focus();
  }, [ready, isWelcome]);

  if (settings.data) {
    return ready ? (
      <RunSourceAvailability.Provider value={keyed}>{children}</RunSourceAvailability.Provider>
    ) : (
      <Navigate to={WELCOME_PATH} replace />
    );
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
