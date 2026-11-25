import { useState } from "react";

export type CopyState = "idle" | "copied" | "failed";

/** The copy state belongs to a reminder: another reminder starts from zero. */
interface CopyOf {
  reminderId: string;
  state: CopyState;
}

/** Copies a reminder's draft (the app sends nothing) and keeps the copy result. */
export function useCopyState(
  reminderId: string,
  draft: string,
  onCopy: (draft: string) => void | Promise<void>,
) {
  const [last, setLast] = useState<CopyOf | null>(null);
  const state: CopyState = last?.reminderId === reminderId ? last.state : "idle";

  async function copy() {
    try {
      await onCopy(draft);
      setLast({ reminderId, state: "copied" });
    } catch {
      setLast({ reminderId, state: "failed" });
    }
  }

  return { state, copy };
}
