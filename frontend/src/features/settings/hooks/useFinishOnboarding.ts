import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { withOnboardingDone, type OnboardingAvailability } from "../onboarding";
import type { SettingsOut } from "../types";
import { useUpdateSettings } from "./useUpdateSettings";

/**
 * Termine le premier lancement : un `PUT /settings` complet (`onboarding_done: true`, avec la
 * disponibilité donnée, ou celle qui était lue), puis l'accueil. Un seul envoi à la fois ; un
 * échec reste affiché (`error`, et `failure` pour lire les champs refusés) et la page reste.
 */
export function useFinishOnboarding() {
  const update = useUpdateSettings();
  const navigate = useNavigate();
  return {
    pending: update.isPending,
    error: update.isError ? errorMessage(update.error) : null,
    failure: update.error,
    finish: async (settings: SettingsOut, availability?: OnboardingAvailability) => {
      if (update.isPending) return;
      try {
        await update.mutateAsync(withOnboardingDone(settings, availability));
      } catch {
        return; // l'erreur est affichée depuis la mutation
      }
      void navigate("/", { replace: true });
    },
    reset: () => {
      if (!update.isPending) update.reset();
    },
  };
}
