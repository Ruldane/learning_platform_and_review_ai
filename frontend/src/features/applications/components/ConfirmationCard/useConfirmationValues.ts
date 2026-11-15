import { useState } from "react";
import type { ConfirmationView } from "../viewTypes";

/** Ce que January a laissé dans chaque champ (départ : ce que l'Assistant a lu) et si les obligatoires sont remplis. */
export function useConfirmationValues(confirmation: ConfirmationView) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(confirmation.fields.map((field) => [field.id, field.value])),
  );
  const complete = confirmation.fields.every(
    (field) => !field.required || (values[field.id] ?? "").trim() !== "",
  );
  return {
    values,
    complete,
    setValue: (id: string, value: string) => setValues({ ...values, [id]: value }),
  };
}
