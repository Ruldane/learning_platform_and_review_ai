import { useState } from "react";
import type { SubmissionRefusalView } from "../viewTypes";

export type RefusedField = keyof SubmissionRefusalView;

/**
 * Le refus du serveur, champ par champ : un message vaut jusqu'à ce que son champ soit modifié
 * (`clear`) ; un nouveau refus (un autre objet) repart de zéro. `refusal` doit rester le même
 * objet tant que l'erreur ne change pas.
 */
export function useRefusal(refusal: SubmissionRefusalView | null) {
  const [cleared, setCleared] = useState<{ source: unknown; fields: RefusedField[] }>({
    source: refusal,
    fields: [],
  });
  if (cleared.source !== refusal) setCleared({ source: refusal, fields: [] });
  return {
    refused: (field: RefusedField): string | undefined =>
      cleared.fields.includes(field) ? undefined : refusal?.[field],
    clear: (...fields: RefusedField[]) =>
      setCleared((current) => ({ ...current, fields: [...current.fields, ...fields] })),
  };
}
