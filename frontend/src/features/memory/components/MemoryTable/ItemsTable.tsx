import { t } from "@/shared/i18n/t";
import type { MemoryItemRow } from "../viewTypes";
import { MemoryTableRow } from "./MemoryTableRow";

interface ItemsTableProps {
  items: MemoryItemRow[];
  selected: string[];
  /** Sélection verrouillée (fusion en cours). */
  locked: boolean;
  onToggle: (id: string) => void;
  onOpen: (id: string) => void;
}

const headClass = "px-3 py-2 text-left font-medium text-muted-foreground";
const COLUMNS = ["title", "kind", "author", "level", "date"] as const;

/** Tableau des éléments : une ligne par élément, une case de sélection en tête. */
export function ItemsTable({ items, selected, locked, onToggle, onOpen }: ItemsTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full text-sm">
        <caption className="sr-only">{t("memory.table.caption")}</caption>
        <thead>
          <tr>
            <th scope="col" className={headClass}>
              <span className="sr-only">{t("memory.table.selection")}</span>
            </th>
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className={headClass}>
                {t(`memory.table.${column}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <MemoryTableRow
              key={item.id}
              item={item}
              checked={selected.includes(item.id)}
              locked={locked}
              onToggle={onToggle}
              onOpen={onOpen}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
