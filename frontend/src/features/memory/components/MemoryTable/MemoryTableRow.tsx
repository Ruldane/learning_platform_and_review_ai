import { t } from "@/shared/i18n/t";
import { authorLabel } from "../authorLabel";
import { formatDay } from "../formatDate";
import { KindBadge } from "../KindBadge";
import type { MemoryItemRow } from "../viewTypes";

interface MemoryTableRowProps {
  item: MemoryItemRow;
  checked: boolean;
  onToggle: (id: string) => void;
  onOpen: (id: string) => void;
}

const cellClass = "px-3 py-2 align-top";

/** Une ligne de la liste : case, titre (ouvre le détail), type, auteur, niveau et date. */
export function MemoryTableRow({ item, checked, onToggle, onOpen }: MemoryTableRowProps) {
  return (
    <tr className="border-t border-border">
      <td className={cellClass}>
        <input
          type="checkbox"
          checked={checked}
          aria-label={t("memory.table.select", { title: item.title })}
          onChange={() => onToggle(item.id)}
        />
      </td>
      <td className={cellClass}>
        <button
          type="button"
          onClick={() => onOpen(item.id)}
          className="text-left font-medium underline-offset-4 hover:underline focus-visible:underline"
        >
          {item.title}
        </button>
        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-muted-foreground">
          {item.status === "pending" ? <span>{t("memory.pendingBadge")}</span> : null}
          {item.indexed ? null : <span>{t("memory.notIndexed")}</span>}
          {item.tags.map((tag) => (
            <span key={tag}>#{tag}</span>
          ))}
        </div>
      </td>
      <td className={cellClass}>
        <KindBadge kind={item.kind} />
      </td>
      <td className={cellClass}>{authorLabel(item.created_by)}</td>
      <td className={cellClass}>
        {item.level ? t(`memory.level.${item.level}`) : t("memory.noValue")}
      </td>
      <td className={cellClass}>{formatDay(item.created_at)}</td>
    </tr>
  );
}
