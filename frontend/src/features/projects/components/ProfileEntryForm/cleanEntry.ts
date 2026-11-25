import { t } from "@/shared/i18n/t";
import type { ProfileEntryView } from "../viewTypes";

/** The server limits (`ProfileEntryIn`): an empty line is a 422 there, so it is dropped here. */
const NAME_MAX = 120;
const DESCRIPTION_MAX = 600;
const ACHIEVEMENTS_MAX = 4;
const ACHIEVEMENT_MAX = 200;

export interface EntryErrors {
  name?: string;
  description?: string;
  achievements?: string;
}

/** The achievements typed one per line: trimmed, without empty or blank-space lines. */
export function achievementLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/** The cleaned entry (name and description trimmed, empty lines removed) and the fields to fix. */
export function cleanEntry(
  name: string,
  description: string,
  achievementsText: string,
): { entry: ProfileEntryView; errors: EntryErrors } {
  const entry: ProfileEntryView = {
    name: name.trim(),
    description: description.trim(),
    achievements: achievementLines(achievementsText),
  };
  const errors: EntryErrors = {};
  if (entry.name === "" || entry.name.length > NAME_MAX) {
    errors.name = t("projects.entry.errors.name");
  }
  if (entry.description.length > DESCRIPTION_MAX) {
    errors.description = t("projects.entry.errors.description");
  }
  if (entry.achievements.length > ACHIEVEMENTS_MAX) {
    errors.achievements = t("projects.entry.errors.tooMany");
  } else if (entry.achievements.some((line) => line.length > ACHIEVEMENT_MAX)) {
    errors.achievements = t("projects.entry.errors.tooLong");
  }
  return { entry, errors };
}
