import { useState } from "react";
import type { Criterion, Progress } from "../../api";

export type Changes = Pick<Progress, "observed" | "note">;

export function useCriterionDraft(criterion: Criterion) {
  const [draft, setDraft] = useState<Changes | null>(null);
  const { observed, note: storedNote } = draft ?? criterion;
  const note = storedNote ?? "";
  const changed = observed !== criterion.observed || note.trim() !== (criterion.note ?? "");
  const clearSavedDraft = () => setDraft((current) => (current === draft ? null : current));
  return { observed, note, changed, setDraft, clearSavedDraft };
}
