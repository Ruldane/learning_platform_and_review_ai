import type { SearchSettingsView, SettingsOut } from "../types";
import { withSearchSettings } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

/** Saves the search settings: a full `PUT /settings`, the other settings unchanged. */
export function useSaveSearchSettings(settings: SettingsOut) {
  const update = useUpdateSettings();
  return {
    pending: update.isPending,
    error: update.error,
    saved: update.isSuccess,
    reset: update.reset,
    save: (search: SearchSettingsView) => update.mutateAsync(withSearchSettings(settings, search)),
  };
}
