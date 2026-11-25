import { useState } from "react";
import type { ConfirmationView } from "../viewTypes";

/**
 * What January left in each field (start: what the Assistant read), whether the mandatory ones
 * are filled in and whether a contact role is given without a name (the server would silently drop
 * it).
 */
export function useConfirmationValues(confirmation: ConfirmationView) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(confirmation.fields.map((field) => [field.id, field.value])),
  );
  const filled = (id: string) => (values[id] ?? "").trim() !== "";
  const roleWithoutName = filled("contact_role") && !filled("contact_name");
  const complete =
    !roleWithoutName && confirmation.fields.every((field) => !field.required || filled(field.id));
  return {
    values,
    complete,
    roleWithoutName,
    setValue: (id: string, value: string) => setValues({ ...values, [id]: value }),
  };
}
