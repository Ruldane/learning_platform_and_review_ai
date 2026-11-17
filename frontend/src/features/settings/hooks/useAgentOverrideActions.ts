import type { ModelChoice, SettingsOut } from "../types";
import { withAgentOverride } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

const ignore = () => undefined;

/** Choisir le modèle d'un agent, ou le rendre à son niveau (`null`) : un `PUT /settings` complet. */
export function useAgentOverrideActions(settings: SettingsOut) {
  const update = useUpdateSettings();
  return {
    pending: update.isPending,
    error: update.error,
    setOverride: (agent: string, choice: ModelChoice | null) => {
      if (update.isPending) return; // un PUT complet à la fois : pas de course entre deux surcharges
      update.mutateAsync(withAgentOverride(settings, agent, choice)).catch(ignore);
    },
  };
}
