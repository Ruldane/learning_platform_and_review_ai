import type { InterruptPayload } from "@/shared/realtime/types";

export type InterruptField = NonNullable<InterruptPayload["fields"]>[number];

/** Réponses saisies : un texte rogné par champ, les champs vides omis. */
export function fieldAnswers(
  fields: InterruptField[],
  draft: Record<string, string>,
): Record<string, string> {
  const answers: Record<string, string> = {};
  for (const field of fields) {
    const text = (draft[field.id] ?? "").trim();
    if (text !== "") answers[field.id] = text;
  }
  return answers;
}
