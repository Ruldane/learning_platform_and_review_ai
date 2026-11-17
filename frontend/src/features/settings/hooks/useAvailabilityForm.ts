import { useState } from "react";
import type { FormEvent } from "react";
import {
  availabilityErrors,
  CONTRACT_FIELDS,
  hasAvailabilityErrors,
  sameAvailabilityDraft,
  toAvailabilityDraft,
  withAvailabilitySettings,
  type AvailabilityDraft,
  type AvailabilityField,
} from "../availabilitySettings";
import { isRefused, refusedFields } from "../refusedFields";
import type { SettingsOut } from "../types";
import { useSaveSettings } from "./useSaveSettings";

/**
 * L'état du formulaire de disponibilité : le brouillon n'existe que pendant l'édition (`null` : on
 * montre les réglages du serveur) ; un champ hors des bornes bloque l'envoi ; un champ que le
 * serveur refuse (422) est signalé sans citer sa valeur ; en cas d'échec le brouillon reste.
 */
export function useAvailabilityForm(settings: SettingsOut) {
  const stored = toAvailabilityDraft(settings);
  const [draft, setDraft] = useState<AvailabilityDraft | null>(null);
  const saver = useSaveSettings();
  const errors = availabilityErrors(draft ?? stored);
  const dirty = draft !== null && !sameAvailabilityDraft(draft, stored);
  const invalid = hasAvailabilityErrors(errors);
  const blocked = !dirty || invalid || saver.pending;
  const refusals = refusedFields(saver.error);

  return {
    saver,
    value: draft ?? stored,
    errors,
    dirty,
    invalid,
    blocked,
    refused: (field: AvailabilityField) => isRefused(refusals, CONTRACT_FIELDS[field]),
    edit: (next: AvailabilityDraft) => {
      saver.reset();
      setDraft(next);
    },
    submit: (event: FormEvent) => {
      event.preventDefault();
      if (blocked || draft === null) return;
      // Une frappe faite pendant l'envoi reste : le brouillon n'est rendu au serveur que s'il n'a
      // pas changé.
      saver.save(withAvailabilitySettings(settings, draft)).then(
        () => setDraft((current) => (current === draft ? null : current)),
        () => undefined, // l'erreur est affichée depuis la mutation ; la saisie est gardée
      );
    },
  };
}
