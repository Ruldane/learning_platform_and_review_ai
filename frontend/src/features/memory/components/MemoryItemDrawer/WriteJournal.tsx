import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { authorLabel } from "../authorLabel";
import { formatDayTime } from "../formatDate";
import type { MemoryWriteView } from "../viewTypes";

/** Journal des écritures : action, auteur, date et raison en une phrase (SPEC 4.5). */
export function WriteJournal({ writes }: { writes: MemoryWriteView[] }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <h3 id={headingId} className="text-sm font-semibold">
        {t("memory.drawer.journal")}
      </h3>
      {writes.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("memory.drawer.journalEmpty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {writes.map((write) => (
            <li key={write.id} className="rounded-lg border border-border px-3 py-2 text-sm">
              <p className="flex flex-wrap gap-x-3">
                <span className="font-medium">{t(`memory.action.${write.action}`)}</span>
                <span>{authorLabel(write.author)}</span>
                <span className="text-muted-foreground">{formatDayTime(write.created_at)}</span>
              </p>
              <p className="text-muted-foreground">{write.reason ?? t("memory.drawer.noReason")}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
