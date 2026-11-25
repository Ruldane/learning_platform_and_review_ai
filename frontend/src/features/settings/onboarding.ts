import type { AvailabilityDraft } from "./availabilitySettings";
import { readTiers } from "./tierChoices";
import type { SettingsOut, UserSettings } from "./types";
import { buildUserSettings } from "./userSettings";

/** The three durations the last step asks for (text while typing). */
export type OnboardingAvailability = Pick<
  AvailabilityDraft,
  "weekday" | "weekendMin" | "weekendMax"
>;

/** The five first-run steps (SPEC 15.5, P20). */
export const STEP_COUNT = 5;

/** The first-run address: the gate does not redirect to it; the page is outside navigation. */
export const WELCOME_PATH = "/welcome";
export const LEGACY_WELCOME_PATH = "/bienvenue";

/**
 * Body of the `PUT /settings` that finishes the first run: all the settings read are kept as-is
 * (never `...current`, see `buildUserSettings`), `onboarding_done` becomes true, and the
 * availability is the one given; without it, the one that was read stays.
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
