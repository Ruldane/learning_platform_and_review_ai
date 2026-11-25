import { t } from "@/shared/i18n/t";
import type { VoteValueView } from "../viewTypes";

const MARKS: Record<VoteValueView, string> = { yes: "✓", no: "✗", maybe: "?" };

/** A vote written in words (« Oui », « Non », « Peut-être »); the sign is decorative, never colour
 * alone. */
export function VoteLabel({ vote }: { vote: VoteValueView }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-sm font-medium">
      <span aria-hidden="true">{MARKS[vote]}</span>
      {t(`applications.committeeVote.${vote}`)}
    </span>
  );
}
