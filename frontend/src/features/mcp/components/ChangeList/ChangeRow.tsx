import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { Button } from "@/shared/ui/button";
import type { ChangeView } from "../viewTypes";

interface ChangeRowProps {
  change: ChangeView;
  busy: boolean;
  onUndo: () => void;
}

/** A call that changed rows: « Annuler » until it has been undone. */
export function ChangeRow({ change, busy, onUndo }: ChangeRowProps) {
  const actionId = useId();
  const rows = t(change.rows === 1 ? "mcp.history.changeRows.one" : "mcp.history.changeRows.many", {
    count: change.rows,
  });
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card p-3">
      <div className="flex flex-col gap-0.5">
        <p id={actionId} className="font-mono text-sm">
          {change.action}
        </p>
        <p className="text-sm text-muted-foreground">
          {rows} {t("mcp.history.changeTables", { tables: change.tables.join(", ") })} ·{" "}
          <time dateTime={change.at}>{fullDateTime(change.at)}</time>
        </p>
      </div>
      {change.undoneAt ? (
        <p className="text-sm text-muted-foreground">
          {t("mcp.history.undone", { date: fullDateTime(change.undoneAt) })}
        </p>
      ) : (
        <Button variant="outline" disabled={busy} aria-describedby={actionId} onClick={onUndo}>
          {t("mcp.history.undo")}
        </Button>
      )}
    </li>
  );
}
