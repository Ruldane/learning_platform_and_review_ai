import { useState } from "react";
import type { SubmissionRefusalView } from "../viewTypes";

export type RefusedField = keyof SubmissionRefusalView;

/**
 * The server's refusal, field by field: a message holds until its field is edited
 * (`clear`); a new refusal (another object) starts from scratch. `refusal` must stay the same
 * object while the error does not change.
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
      setCleared((current) => {
        const added = fields.filter((field) => !current.fields.includes(field));
        // Nothing new: the same state, so no new array or re-render on each keystroke.
        return added.length === 0 ? current : { ...current, fields: [...current.fields, ...added] };
      }),
  };
}
