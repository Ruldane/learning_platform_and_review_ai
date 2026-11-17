import { useRef, useState } from "react";
import type { ModelChoice, SettingsOut } from "../types";
import { withAgentOverrides } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

/** Les choix demandés et pas encore écrits : `null` retire la surcharge de l'agent. */
type Wanted = Record<string, ModelChoice | null>;

/**
 * Choisir le modèle d'un agent, ou le rendre à son niveau (`null`) : un `PUT /settings` complet,
 * un seul à la fois. Un choix fait pendant un envoi (une flèche de plus dans une liste, un autre
 * agent) n'est jamais jeté : il attend, le dernier choix de chaque agent est rejoué à la fin de
 * l'envoi, à partir des réglages que le serveur vient de renvoyer. Les listes montrent le choix
 * demandé sans retour arrière (`overrides`) ; si un envoi échoue, elles retombent sur ce que le
 * serveur a enregistré et les choix en attente sont abandonnés.
 */
export function useAgentOverrideActions(settings: SettingsOut) {
  const update = useUpdateSettings();
  const [wanted, setWanted] = useState<Wanted>({});
  const [saved, setSaved] = useState(false);
  const queue = useRef<Wanted>({});
  const running = useRef(false);

  async function flush(start: SettingsOut) {
    running.current = true;
    update.reset();
    try {
      let current = start;
      while (Object.keys(queue.current).length > 0) {
        const batch = queue.current;
        queue.current = {};
        current = await update.mutateAsync(withAgentOverrides(current, batch));
      }
      setSaved(true);
    } catch {
      queue.current = {}; // l'erreur est affichée depuis la mutation
    } finally {
      running.current = false;
      setWanted({});
    }
  }

  return {
    pending: update.isPending,
    error: update.error,
    /** Un enregistrement vient de finir (les choix demandés sont écrits). */
    saved,
    /** Les surcharges telles que le serveur les a, avec les choix demandés qu'il n'a pas encore. */
    overrides: (): Record<string, ModelChoice | undefined> => {
      const shown: Record<string, ModelChoice | undefined> = { ...settings.agent_overrides };
      for (const [agent, choice] of Object.entries(wanted)) {
        if (choice) shown[agent] = choice;
        else delete shown[agent];
      }
      return shown;
    },
    setOverride: (agent: string, choice: ModelChoice | null) => {
      queue.current[agent] = choice;
      setWanted((current) => ({ ...current, [agent]: choice }));
      setSaved(false);
      if (!running.current) void flush(settings);
    },
  };
}
