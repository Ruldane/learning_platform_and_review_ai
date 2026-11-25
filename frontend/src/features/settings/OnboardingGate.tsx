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

/** The main area of the layout (target of the skip link). */
const CONTENT_ID = "contenu";

/**
 * The first-launch gate of the shell (`shell.gate`): while `onboarding_done` is false, any page
 * other than `/welcome` leads to `/welcome` (a replacement, not a stack).
 * Settings are read before the layout: while loading or on error, a single state. A
 * failed re-read while settings are already there never closes the app.
 *
 * « Réessayer » keeps focus on the container (the button disappears with the error); if the read
 * succeeds, focus moves to the layout's content (`#contenu`). When the read leads to
 * `/welcome`, the step's title takes it: the gate does not take it away.
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
