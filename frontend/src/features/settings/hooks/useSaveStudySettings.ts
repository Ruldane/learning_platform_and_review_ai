import type { SettingsOut } from "../types";
import { withStudySettings, type StudyDraft } from "../studySettings";
import { useUpdateSettings } from "./useUpdateSettings";

/** Enregistre les réglages d'étude : `PUT /settings` complet, le reste des réglages inchangé. */
export function useSaveStudySettings(settings: SettingsOut) {
  const update = useUpdateSettings();
  return {
    pending: update.isPending,
    error: update.error,
    saved: update.isSuccess,
    reset: update.reset,
    save: (draft: StudyDraft) => update.mutateAsync(withStudySettings(settings, draft)),
  };
}
