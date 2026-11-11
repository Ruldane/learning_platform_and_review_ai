import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { authorLabel } from "../authorLabel";
import type { MemoryItemRow } from "../viewTypes";

interface PendingDecisionsProps {
  items: MemoryItemRow[];
  /** Décision dont la confirmation ou le refus est en cours : ses boutons sont verrouillés. */
  busyId: string | null;
  onConfirm: (id: string) => void;
  onReject: (id: string) => void;
}

/** Boîte « À confirmer » : les décisions proposées par les agents, jamais écrites sans accord (SPEC 4.5). */
export function PendingDecisions({ items, busyId, onConfirm, onReject }: PendingDecisionsProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border border-border bg-card px-4 py-3"
    >
      <h2 id={headingId} className="text-base font-semibold">
        {t("memory.pending.title")}
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("memory.pending.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex flex-col gap-2 border-t border-border pt-3 first:border-0 first:pt-0"
            >
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="text-xs text-muted-foreground">
                  {t("memory.pending.proposedBy", { author: authorLabel(item.created_by) })}
                </p>
                <p className="text-sm">{item.reason ?? t("memory.pending.noReason")}</p>
              </div>
              <div className="flex gap-2">
                <Button disabled={busyId === item.id} onClick={() => onConfirm(item.id)}>
                  {t("memory.button.confirm")}
                </Button>
                <Button
                  variant="outline"
                  disabled={busyId === item.id}
                  onClick={() => onReject(item.id)}
                >
                  {t("memory.button.reject")}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
