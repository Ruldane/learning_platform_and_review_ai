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
 * Availability form state: the draft exists only while editing (`null`: the
 * server's settings are shown); a field out of bounds blocks sending; a field that the
 * server refuses (422) is flagged without quoting its value; on failure the draft stays.
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
      // A keystroke made during the send stays: the draft is sent to the server only if it
      // has not changed.
      saver.save(withAvailabilitySettings(settings, draft)).then(
        () => setDraft((current) => (current === draft ? null : current)),
        () => undefined, // the error is shown from the mutation; the input is kept
      );
    },
  };
}
