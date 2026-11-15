import { t } from "@/shared/i18n/t";
import type { VoteValueView } from "../viewTypes";

const MARKS: Record<VoteValueView, string> = { oui: "✓", non: "✗", peut_etre: "?" };

/** Un vote écrit en toutes lettres (« Oui », « Non », « Peut-être ») ; le signe est décoratif, jamais la couleur seule. */
export function VoteLabel({ vote }: { vote: VoteValueView }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-sm font-medium">
      <span aria-hidden="true">{MARKS[vote]}</span>
      {t(`applications.committeeVote.${vote}`)}
    </span>
  );
}
