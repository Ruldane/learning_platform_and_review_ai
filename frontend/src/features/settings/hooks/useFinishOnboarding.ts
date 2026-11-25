import { useRef } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { withOnboardingDone, type OnboardingAvailability } from "../onboarding";
import type { SettingsOut, TierChoices } from "../types";
import { buildUserSettings } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

/**
 * Finishes the first run: one full `PUT /settings` (`onboarding_done: true`, with the
 * availability given, or the one read), then the home page. Only one send at a time, even if
 * two activations arrive at the same moment (« Terminer » and « Passer l'accueil »: a ref,
 * not the render state). A failure stays shown (`error`, and `failure` to read the fields
 * refused) and the page stays.
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
      return false; // the error is shown from the mutation
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
     * Sets the model levels to the given key's provider (the rest of the settings is
     * kept as-is); `false` if the send failed (the error is shown, the step stays).
     */
    saveTiers: (settings: SettingsOut, tiers: TierChoices) =>
      guarded(() => update.mutateAsync(buildUserSettings(settings, tiers))),
    reset: () => {
      if (!running.current) update.reset();
    },
  };
}
