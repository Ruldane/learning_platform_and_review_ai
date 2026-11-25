import { formatDay } from "./format";
import type { ApplicationView } from "./viewTypes";

/** « Relancer (20/11/2026) », « Relancer » or « 20/11/2026 »; `null` with no action or date. */
export function describeNextAction({ nextAction, nextActionOn }: ApplicationView): string | null {
  if (nextAction && nextActionOn) return `${nextAction} (${formatDay(nextActionOn)})`;
  if (nextAction) return nextAction;
  return nextActionOn ? formatDay(nextActionOn) : null;
}
