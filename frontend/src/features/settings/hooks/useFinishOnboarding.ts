import { useRef } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { withOnboardingDone, type OnboardingAvailability } from "../onboarding";
import type { SettingsOut, TierChoices } from "../types";
import { buildUserSettings } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

/**
 * Termine le premier lancement : un `PUT /settings` complet (`onboarding_done: true`, avec la
 * disponibilité donnée, ou celle qui était lue), puis l'accueil. Un seul envoi à la fois, même si
 * deux activations arrivent dans le même instant (« Terminer » et « Passer l'accueil » : une ref,
 * pas l'état de rendu). Un échec reste affiché (`error`, et `failure` pour lire les champs
 * refusés) et la page reste.
 */
export function useFinishOnboarding() {
  const update = useUpdateSettings();
  const navigate = useNavigate();
  const running = useRef(false);
  const guarded = async (send: () => Promise<unknown>): Promise<boolean> => {
    if (running.current) return false;
    running.current = true;
    try {
      await send();
      return true;
    } catch {
      return false; // l'erreur est affichée depuis la mutation
    } finally {
      running.current = false;
    }
  };
  return {
    pending: update.isPending,
    error: update.isError ? errorMessage(update.error) : null,
    failure: update.error,
    finish: async (settings: SettingsOut, availability?: OnboardingAvailability) => {
      const saved = await guarded(() =>
        update.mutateAsync(withOnboardingDone(settings, availability)),
      );
      if (saved) void navigate("/", { replace: true });
    },
    /**
     * Règle les niveaux de modèles sur le fournisseur de la clé donnée (le reste des réglages est
     * repris tel quel) ; `false` si l'envoi a échoué (l'erreur est affichée, l'étape reste).
     */
    saveTiers: (settings: SettingsOut, tiers: TierChoices) =>
      guarded(() => update.mutateAsync(buildUserSettings(settings, tiers))),
    reset: () => {
      if (!running.current) update.reset();
    },
  };
}
