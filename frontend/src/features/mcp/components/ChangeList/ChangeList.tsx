import { t } from "@/shared/i18n/t";
import type { ChangeView } from "../viewTypes";
import { ChangeRow } from "./ChangeRow";

interface ChangeListProps {
  changes: ChangeView[];
  /** Appels dont l'annulation est en cours. */
  busyIds: readonly string[];
  onUndo: (callId: string) => void;
}

/** Les changements faits par Claude ; seul un changement pas encore annulé a son bouton. */
export function ChangeList({ changes, busyIds, onUndo }: ChangeListProps) {
  if (changes.length === 0) {
    return <p className="text-muted-foreground">{t("mcp.history.changesEmpty")}</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {changes.map((change) => (
        <ChangeRow
          key={change.callId}
          change={change}
          busy={busyIds.includes(change.callId)}
          onUndo={() => onUndo(change.callId)}
        />
      ))}
    </ul>
  );
}
