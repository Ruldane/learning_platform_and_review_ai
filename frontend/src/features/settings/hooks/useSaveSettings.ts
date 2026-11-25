import type { UserSettings } from "../types";
import { useUpdateSettings } from "./useUpdateSettings";

/**
 * Saves a `PUT /settings` body already built from the settings read: the send state for
 * the screen that shows it (sending, error, done), and `save`, which rejects if the back end
 * refuse.
 */
export function useSaveSettings() {
  const update = useUpdateSettings();
  return {
    pending: update.isPending,
    error: update.error,
    saved: update.isSuccess,
    // During the send, a keystroke must not make it look finished (and allow a second
    // envoi).
    reset: () => {
      if (!update.isPending) update.reset();
    },
    save: (body: UserSettings) => update.mutateAsync(body),
  };
}
