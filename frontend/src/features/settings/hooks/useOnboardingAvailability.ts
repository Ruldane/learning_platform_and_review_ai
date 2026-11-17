import { useState } from "react";
import type { AvailabilityKey } from "../components/viewTypes";
import {
  availabilityErrors,
  CONTRACT_FIELDS,
  toAvailabilityDraft,
  weeklyBudget,
} from "../availabilitySettings";
import type { OnboardingAvailability } from "../onboarding";
import { isRefused, refusedFields } from "../refusedFields";
import type { SettingsOut } from "../types";

/**
 * Les trois durées de la dernière étape : du texte pendant la saisie, d'abord celles que les
 * réglages portent (ou les défauts du back). `invalid` bloque « Terminer » ; `refused` marque les
 * champs qu'une 422 de l'enregistrement a nommés (jamais leur valeur).
 */
export function useOnboardingAvailability(settings: SettingsOut, failure: unknown) {
  const stored = toAvailabilityDraft(settings);
  const [values, setValues] = useState<OnboardingAvailability>({
    weekday: stored.weekday,
    weekendMin: stored.weekendMin,
    weekendMax: stored.weekendMax,
  });
  const draft = { ...stored, ...values };
  const flags = availabilityErrors(draft);
  const refusals = refusedFields(failure);
  const refused = (key: AvailabilityKey) => isRefused(refusals, CONTRACT_FIELDS[key]);
  return {
    values,
    flags,
    invalid: flags.weekday || flags.weekendMin || flags.weekendMax || flags.weekendOrder,
    refused: {
      weekday: refused("weekday"),
      weekendMin: refused("weekendMin"),
      weekendMax: refused("weekendMax"),
    },
    budget: weeklyBudget(draft),
    edit: (key: AvailabilityKey, value: string) =>
      setValues((current) => ({ ...current, [key]: value })),
  };
}
