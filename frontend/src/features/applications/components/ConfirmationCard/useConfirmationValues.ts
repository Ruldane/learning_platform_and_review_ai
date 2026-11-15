import { useState } from "react";
import type { ConfirmationView } from "../viewTypes";

/**
 * Ce que January a laissé dans chaque champ (départ : ce que l'Assistant a lu), si les obligatoires
 * sont remplis et si un rôle de contact est donné sans nom (le serveur le jetterait sans rien dire).
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
