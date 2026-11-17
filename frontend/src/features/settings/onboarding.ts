import type { AvailabilityDraft } from "./availabilitySettings";
import { readTiers } from "./tierChoices";
import type { SettingsOut, UserSettings } from "./types";
import { buildUserSettings } from "./userSettings";

/** Les trois durées que demande la dernière étape (du texte pendant la saisie). */
export type OnboardingAvailability = Pick<
  AvailabilityDraft,
  "weekday" | "weekendMin" | "weekendMax"
>;

/** Les cinq étapes du premier lancement (SPEC 15.5, P20). */
export const STEP_COUNT = 5;

/** L'adresse du premier lancement : la porte n'y renvoie pas, la page est hors de la navigation. */
export const WELCOME_PATH = "/bienvenue";

/**
 * Corps du `PUT /settings` qui termine le premier lancement : tous les réglages lus sont repris
 * tels quels (jamais `...current`, voir `buildUserSettings`), `onboarding_done` passe à vrai, et la
 * disponibilité est celle qu'on donne ; sans elle, celle qui était lue reste.
 */
export function withOnboardingDone(
  current: SettingsOut,
  availability?: OnboardingAvailability,
): UserSettings {
  const body = { ...buildUserSettings(current, readTiers(current.tiers)), onboarding_done: true };
  if (!availability) return body;
  return {
    ...body,
    availability: {
      weekday_minutes: Number(availability.weekday),
      weekend_block_min_minutes: Number(availability.weekendMin),
      weekend_block_max_minutes: Number(availability.weekendMax),
    },
  };
}
