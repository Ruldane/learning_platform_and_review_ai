import type { UserSettings } from "../types";
import { useUpdateSettings } from "./useUpdateSettings";

/**
 * Enregistre un corps de `PUT /settings` déjà construit à partir des réglages lus : l'état de
 * l'envoi pour l'écran qui le montre (en cours, erreur, réussi), et `save` qui rejette si le back refuse.
 */
export function useSaveSettings() {
  const update = useUpdateSettings();
  return {
    pending: update.isPending,
    error: update.error,
    saved: update.isSuccess,
    reset: update.reset,
    save: (body: UserSettings) => update.mutateAsync(body),
  };
}
