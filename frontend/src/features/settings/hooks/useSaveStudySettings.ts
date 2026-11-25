import type { SettingsOut } from "../types";
import { withStudySettings, type StudyDraft } from "../studySettings";
import { useUpdateSettings } from "./useUpdateSettings";

/** Saves the study settings: a full `PUT /settings`, the other settings unchanged. */
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
